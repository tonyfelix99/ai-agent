# === memory.py ===
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.memory import VectorStoreRetrieverMemory

import os

def get_memory(persist_dir="faiss_store"):
    embeddings = OllamaEmbeddings(model="llama3")

    # If FAISS store exists, load it
    if os.path.exists(persist_dir):
        try:
            db = FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"[⚠️] Failed to load FAISS memory: {e}\nCreating new one...")
            db = FAISS.from_texts(["Initial setup..."], embedding=embeddings)
    else:
        db = FAISS.from_texts(["Initial setup..."], embedding=embeddings)

    db.save_local(persist_dir)
    
    retriever = db.as_retriever(search_kwargs={"k": 5})
    memory = VectorStoreRetrieverMemory(retriever=retriever)
    return memory