from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict
from Agents.modules.memory import memory
from Agents.modules.tools import TerraformTool, DiskModifierTool
from Agents.modules.persistent_memory import PersistentMemory
from Agents.modules.tools.file_query_tool import FileQueryTool
from Agents.modules.tools.recall_history_tool import RecallHistoryTool  # ✅ New tool

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
# Summarizer (still used if context too big)
# ----------------------------
def summarize_context(context_text: str) -> str:
    if not context_text.strip():
        return "No relevant infra context found."

    summarizer_prompt = f"""
    Summarize the following infrastructure context into 5 concise bullet points:
    {context_text}
    """
    summarizer_chain = llm | StrOutputParser()
    return summarizer_chain.invoke(summarizer_prompt).strip()

# ----------------------------
# Planner Node (LLM decides reasoning + tool usage)
# ----------------------------
def planner_node(state: GraphState):
    query = state["input"].strip().lower()

    # Retrieve infra context (Terraform + Excel + PDF)
    history = persistent_memory.get_history()
    docs = memory.get_relevant_documents(query)

    labeled_docs = [
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    ]
    raw_context = "\n\n".join(labeled_docs)
    context = summarize_context(raw_context) if len(raw_context) > 1500 else (raw_context or "No relevant infra context found.")

    # ✅ Detect query type
    recall_keywords = ["recall", "history", "previous", "what did i ask", "last query"]
    disk_keywords = ["disk", "resize", "expand", "increase size"]
    info_keywords = ["which", "list", "show", "find", "display", "describe", "details", "os of", "cpu of"]

    if any(k in query for k in recall_keywords):
        active_instructions = INSTRUCTIONS["base"] + "\n" + INSTRUCTIONS["recall"]
    elif any(k in query for k in disk_keywords):
        active_instructions = INSTRUCTIONS["base"] + "\n" + INSTRUCTIONS["disk_resize"]
    elif any(k in query for k in info_keywords):
        active_instructions = INSTRUCTIONS["base"] + "\n" + INSTRUCTIONS["informational"] + "\n" + INSTRUCTIONS["file_query"]
    else:
        active_instructions = INSTRUCTIONS["base"] + "\n" + INSTRUCTIONS["terraform_ops"]

    # ✅ Build prompt for LLM
    prompt = PromptTemplate(
        input_variables=["query", "context", "history", "instructions"],
        template=INSTRUCTIONS["planner_prompt"]
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "query": query,
        "context": context,
        "history": history,
        "instructions": active_instructions
    }).strip()

    # ✅ Parse reasoning & plan
    if "Plan:" in response:
        reasoning, plan = response.split("Plan:", 1)
    else:
        reasoning, plan = response, "No plan generated."

    # ✅ Clean plan (Handle recall, info, and tools properly)
    if "Informational query" in plan:
        clean_plan = "Informational query – no actions to execute."
    else:
        clean_plan = "\n".join(
            re.sub(r'[*`]+', '', line).strip()
            for line in plan.splitlines()
            if ":" in line
        )

    # Save reasoning + interaction
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
        "DiskModifierTool": DiskModifierTool(tf_file="./Agents/modules/terraform/main.tf"),
        "FileQueryTool": FileQueryTool(),
        "RecallHistoryTool": RecallHistoryTool(persistent_memory)  # ✅ Added tool
    }

    aliases = {
        "Terraform": "TerraformTool",
        "DiskModifier": "DiskModifierTool",
        "FileQuery": "FileQueryTool",
        "RecallHistory": "RecallHistoryTool"
    }

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
                elif tool_name in ["FileQueryTool", "RecallHistoryTool"]:
                    output.append(tools[tool_name]._run(command))

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
