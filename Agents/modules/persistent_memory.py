import json
import os

class PersistentMemory:
    def __init__(self, file_path="./Agents/modules/configs/conversation_history.json"):
        self.file_path = file_path
        self.history = []
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.history = json.load(f)
        else:
            self.history = []

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.history, f, indent=2)

    def add_interaction(self, query, response):
        self.history.append({"query": query, "response": response})
        self._save()

    def get_history(self):
        """Return formatted history for LLM prompt context."""
        return "\n".join(
            [f"Q: {item['query']}\nA: {item['response']}" for item in self.history[-10:]]  # last 10
        )

    def get_last_interaction(self):
        """Return the most recent query and response."""
        if self.history:
            return self.history[-1]
        return None

    def get_last_n_interactions(self, n=3):
        """Return the last N interactions."""
        return self.history[-n:] if self.history else []
