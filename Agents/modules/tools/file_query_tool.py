# Agents/modules/tools/file_query_tool.py
from langchain.tools import BaseTool
from Agents.modules.memory import memory

class FileQueryTool(BaseTool):
    name: str = "FileQueryTool"
    description: str = "Fetches relevant infrastructure context (VM details, Terraform, PDFs) from FAISS memory for LLM reasoning."

    def _run(self, query: str) -> str:
        docs = memory.get_relevant_documents(query)
        if not docs:
            return "No relevant context found in memory."

        # Build full context
        context = "\n\n".join(
            f"[Source: {doc.metadata.get('source','unknown')}]\n{doc.page_content}"
            for doc in docs
        )
        return context

    async def _arun(self, query: str):
        raise NotImplementedError("Async not supported for FileQueryTool")
