from Agents.modules.graph import build_graph
from Agents.modules.memory import memory

# --------------------------------------
# Initial indexing of infrastructure data
# --------------------------------------
print("[Startup] Indexing infrastructure context...")
memory.index_main_tf()         # Terraform file
memory.index_vm_sheet()        # VM details Excel
memory.index_pdf()            # ✅ PDF files in ./Agents/modules/infra/docs

# --------------------------------------
# Build LangGraph workflow
# --------------------------------------
graph = build_graph()

print("\n[AI DevOps Assistant Ready]")
print("Type 'exit' to quit.")

# --------------------------------------
# Main agent loop
# --------------------------------------
while True:
    query = input("\nEnter DevOps request (or 'exit'): ")
    if query.lower() in ["exit", "quit"]:
        print("[Exit] Shutting down DevOps Assistant.")
        break

    # Execute graph with user query
    result = graph.invoke({"input": query})

    # Final response
    print("\n[FINAL RESULT]")
    print(result["result"] or "No actionable result.")
