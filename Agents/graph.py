 # === File: graph.py ===
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import chat_agent_executor
from langchain_ollama import ChatOllama
from tools import tools
from nodes import planner_node, validator_node, executor_node

# Define the graph
workflow = StateGraph()

# Add nodes
workflow.add_node("planner", planner_node)
workflow.add_node("validator", validator_node)
workflow.add_node("executor", executor_node)

# Define edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "validator")
workflow.add_edge("validator", "executor")
workflow.add_edge("executor", END)

# Compile the graph
graph = workflow.compile()