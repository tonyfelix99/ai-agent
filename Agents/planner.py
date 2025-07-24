# === planner.py ===
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langgraph.graph import StateGraph, END
from tools import tools
from modules.memory import get_memory

from modules.nodes import plan_node, execute_node, human_validation_node


from typing import TypedDict, Optional
class GraphState(TypedDict):
    input: str
    plan: Optional[str]
    action: Optional[str]
    result: Optional[str]
    approved: Optional[bool]
    current_action: Optional[str]

# === Setup ===
llm = ChatOllama(model="llama3")
memory = get_memory()

# === Build LangGraph ===
graph = StateGraph(state_schema)

graph.add_node("planner", plan_node(memory))
graph.add_node("validator", validate_node())

# Correct edges
graph.set_entry_point("planner")
graph.add_edge("planner", "validator")
graph.set_entry_point("planner")
graph.add_edge("planner", "validator")
# ✅ FIXED: Removed invalid `condition=` keyword
graph.add_conditional_edges(
    "validator",
    lambda state: "execute" if state["approved"] else "end",
    {
        "execute": "execute",
        "end": END
    }
)

graph.add_edge("execute", END)

# === Compile graph and run loop ===
app = graph.compile()

print("\U0001F6E0️ LangGraph DevOps Assistant (type 'exit' to quit)")
while True:
    user_input = input("\n> You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    output = app.invoke({"input": user_input})
    print(f"\n✅ Final Output: {output.get('result', output)}")