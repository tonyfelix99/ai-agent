from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict
from Agents.modules.memory import memory
from Agents.modules.tools import TerraformTool, DiskModifierTool
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
# Initialize LLM
# ----------------------------
llm = ChatOllama(model="llama3")

# ----------------------------
# Planner Node
# ----------------------------
def planner_node(state: GraphState):
    query = state["input"]
    docs = memory.get_relevant_documents(query)
    context = "\n".join([doc.page_content for doc in docs]) or "No relevant infra context found."

    # Build prompt dynamically
    instructions = INSTRUCTIONS.get("base", "")
    if "disk" in query.lower():
        instructions += "\n" + INSTRUCTIONS.get("disk_resize", "")
    instructions += "\n" + INSTRUCTIONS.get("terraform_ops", "")

    prompt = PromptTemplate(
        input_variables=["query", "context", "instructions"],
        template=INSTRUCTIONS["planner_prompt"]
    )

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "query": query,
        "context": context,
        "instructions": instructions
    })

    # Split reasoning & plan
    if "Plan:" in response:
        reasoning, plan = response.split("Plan:", 1)
    else:
        reasoning, plan = response, "No plan generated."

    # Clean & keep valid commands
    clean_plan = "\n".join(
        re.sub(r'[*`]+', '', line).strip()
        for line in plan.splitlines()
        if ":" in line
    )

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
    aliases = {
        "Terraform": "TerraformTool",
        "DiskModifier": "DiskModifierTool"
    }

    output = []
    for line in state["plan"].splitlines():
        if ":" in line:
            tool_name, command = line.split(":", 1)
            tool_name, command = tool_name.strip(), command.strip()
            tool_name = aliases.get(tool_name, tool_name)

            # Confirm before each step
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
                        # Extra confirmation for apply
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
