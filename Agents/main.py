from Agents.modules.graph import build_graph
from Agents.modules.memory import memory

# Index infra context
memory.index_main_tf()
memory.index_vm_sheet()

# Build workflow graph
graph = build_graph()

# Run agent loop
while True:
    query = input("\nEnter DevOps request (or 'exit'): ")
    if query.lower() in ["exit", "quit"]:
        break
    result = graph.invoke({"input": query})
    print("\n[FINAL RESULT]\n", result["result"])
