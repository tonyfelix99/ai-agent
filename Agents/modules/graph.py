from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict
from Agents.modules.memory import memory
from Agents.modules.tools import TerraformTool, DiskModifierTool
from Agents.modules.persistent_memory import PersistentMemory
import yaml
import re

# ----------------------------
# Define state structure
# ----------------------------
class GraphState(TypedDict):
    input: str
    reasoning: str
    plan: str
    validation: str
    result: str

# ----------------------------
# Load instructions
# ----------------------------
with open("./Agents/modules/configs/instructions.yaml", "r") as f:
    INSTRUCTIONS = yaml.safe_load(f)

# ----------------------------
# Initialize LLM & Memory
# ----------------------------
llm = ChatOllama(model="llama3")
persistent_memory = PersistentMemory()

# ----------------------------
# ----------------------------
# Helper: Summarize Context
# ----------------------------
def summarize_context(context_text: str) -> str:
    """Summarize lengthy infrastructure context into concise points."""
    if not context_text.strip():
        return "No relevant infra context found."

    summarizer_prompt = f"""
    Summarize the following infrastructure context into 5 concise bullet points:
    {context_text}
    """
    summarizer_chain = llm | StrOutputParser()
    return summarizer_chain.invoke(summarizer_prompt).strip()


# ----------------------------
# Planner Node
# ----------------------------
def planner_node(state: GraphState):
    query = state["input"].strip().lower()

    # ✅ Handle recall/history queries
    recall_phrases = ["recall", "history", "what did i ask", "previous question", "last query"]
    if any(phrase in query for phrase in recall_phrases):
        last_interaction = persistent_memory.get_last_interaction()
        if last_interaction:
            reasoning = f"Recalling your last query:\nQ: {last_interaction['query']}\nA: {last_interaction['response']}"
            return {"reasoning": reasoning, "plan": "No new execution plan generated (history recall only)."}
        else:
            return {"reasoning": "No previous query found in memory.", "plan": "None"}

    # ✅ Retrieve infra context (Terraform + Excel + PDF)
    history = persistent_memory.get_history()
    docs = memory.get_relevant_documents(query)

    # Label each source clearly
    labeled_docs = [
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    ]
    raw_context = "\n\n".join(labeled_docs)

    # Summarize context if too large
    if len(raw_context) > 1500:
        print("[Memory] Context too long. Summarizing...")
        context = summarize_context(raw_context)
    else:
        context = raw_context or "No relevant infra context found."

    # ✅ Detect informational vs actionable queries
    info_keywords = ["which", "list", "show", "find", "display", "describe", "details"]
    is_info_query = any(kw in query for kw in info_keywords) and not any(x in query for x in ["resize", "apply", "init", "plan"])

    # Build instructions dynamically
    instructions = INSTRUCTIONS.get("base", "")
    if not is_info_query:
        if "disk" in query:
            instructions += "\n" + INSTRUCTIONS.get("disk_resize", "")
        instructions += "\n" + INSTRUCTIONS.get("terraform_ops", "")

    # Generate reasoning & plan from LLM
    prompt = PromptTemplate(
        input_variables=["query", "context", "history", "instructions"],
        template=INSTRUCTIONS["planner_prompt"]
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "query": query,
        "context": context,
        "history": history,
        "instructions": instructions
    }).strip()

    # Split reasoning & plan
    if "Plan:" in response:
        reasoning, plan = response.split("Plan:", 1)
    else:
        reasoning, plan = response, "No plan generated."

    # ✅ For informational queries: directly return context
    if is_info_query:
        answer = f"Based on infra context, here are the matches:\n\n{context}"
        persistent_memory.add_interaction(query, answer)
        return {"reasoning": answer, "plan": "Informational query – no actions to execute."}

    # ✅ Clean actionable plan lines
    clean_plan = "\n".join(
        re.sub(r'[*`]+', '', line).strip()
        for line in plan.splitlines()
        if ":" in line
    )

    # Save reasoning & plan to persistent memory
    persistent_memory.add_interaction(query, reasoning.strip() + "\n" + plan.strip())
    return {"reasoning": reasoning.strip(), "plan": clean_plan}



# ----------------------------
# Validation Node
# ----------------------------
def validation_node(state: GraphState):
    print(f"\n[Reasoning]\n{state['reasoning']}")
    print(f"\n[Proposed Plan]\n{state['plan']}")
    confirm = input("Approve this plan? (yes/no): ").strip().lower()
    return {"validation": "approved" if confirm == "yes" else "rejected"}

# ----------------------------
# Executor Node
# ----------------------------
def executor_node(state: GraphState):
    if state["validation"] != "approved":
        return {"result": "Execution cancelled by user."}

    tools = {
        "TerraformTool": TerraformTool(working_dir="./Agents/modules/terraform"),
        "DiskModifierTool": DiskModifierTool(tf_file="./Agents/modules/terraform/main.tf")
    }
    aliases = {"Terraform": "TerraformTool", "DiskModifier": "DiskModifierTool"}

    output = []
    for line in state["plan"].splitlines():
        if ":" in line:
            tool_name, command = line.split(":", 1)
            tool_name, command = tool_name.strip(), command.strip()
            tool_name = aliases.get(tool_name, tool_name)

            confirm = input(f"Approve execution of [{tool_name}: {command}]? (yes/no): ").strip().lower()
            if confirm != "yes":
                output.append(f"Skipped: {tool_name}: {command}")
                continue

            if tool_name in tools:
                if tool_name == "TerraformTool":
                    if command == "init":
                        output.append(tools[tool_name].init())
                    elif command == "plan":
                        output.append(tools[tool_name].plan())
                    elif command == "apply":
                        final_confirm = input("This will APPLY changes. Confirm again (yes/no): ").strip().lower()
                        if final_confirm == "yes":
                            output.append(tools[tool_name].apply())
                        else:
                            output.append("Skipped Terraform apply.")
                elif tool_name == "DiskModifierTool":
                    parts = command.split()
                    if parts[0] == "resize-disk" and len(parts) == 3:
                        vm_name, size = parts[1], parts[2]
                        output.append(tools[tool_name].modify_disk_size(vm_name, size))

    return {"result": "\n".join(output)}

# ----------------------------
# Build LangGraph
# ----------------------------
def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("planner", planner_node)
    graph.add_node("validate", validation_node)
    graph.add_node("execute", executor_node)
    graph.add_edge("planner", "validate")
    graph.add_edge("validate", "execute")
    graph.add_edge("execute", END)
    graph.set_entry_point("planner")
    return graph.compile()
