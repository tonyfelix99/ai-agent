from langchain.tools import BaseTool
from typing import Type

class RecallHistoryTool(BaseTool):
    name: str = "RecallHistoryTool"  # ✅ Type annotation fixed
    description: str = "Recalls the user's last query and response from persistent memory."
    persistent_memory: any  # ✅ Declare as a Pydantic field

    def __init__(self, persistent_memory):
        super().__init__(persistent_memory=persistent_memory)  # ✅ Pass via super init

    def _run(self, query: str) -> str:
        last_interaction = self.persistent_memory.get_last_interaction()
        if last_interaction:
            return f"Last query: {last_interaction['query']}\nResponse: {last_interaction['response']}"
        else:
            return "No previous query found in memory."

    async def _arun(self, query: str) -> str:
        return self._run(query)
