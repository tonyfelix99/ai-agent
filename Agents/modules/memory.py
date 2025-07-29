import os
import time
import threading
import faiss
import hcl2
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.document_loaders import PyPDFLoader


class MemoryStore:
    def __init__(self, index_path="./Agents/modules/storage/faiss_index"):
        self.index_path = index_path
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.tf_file = "./Agents/modules/terraform/main.tf"
        self.vm_sheet = "./Agents/modules/infra/vm_details.xlsx"
        self.pdf_file = "./Agents/modules/infra/infra_details.pdf"

        # ✅ Load or create FAISS index safely
        if os.path.exists(index_path):
            try:
                print("[Memory] Loading existing FAISS index...")
                self.vectorstore = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                print(f"[Memory] FAISS index corrupted: {e}. Rebuilding...")
                self._create_empty_index()
                self._first_time_index()
        else:
            print("[Memory] No FAISS index found. Creating new empty index...")
            self._create_empty_index()
            self._first_time_index()

        # ✅ Start file watcher in background
        threading.Thread(target=self._start_watcher, daemon=True).start()

    # ----------------------
    # Helper: Create Empty FAISS Index
    # ----------------------
    def _create_empty_index(self):
        dim = len(self.embeddings.embed_query("test"))
        index = faiss.IndexFlatL2(dim)
        self.vectorstore = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )
        print("[Memory] Empty FAISS index created.")

    def save(self):
        self.vectorstore.save_local(self.index_path)

    # ----------------------
    # Initial Indexing
    # ----------------------
    def _first_time_index(self):
        print("[Memory] Running first-time indexing for Terraform, VM inventory, and PDF...")
        self.index_main_tf()
        self.index_vm_sheet()
        self.index_pdf()

    # ----------------------
    # Terraform Indexing
    # ----------------------
    def index_main_tf(self):
        self._remove_old_docs("main.tf")
        if not os.path.exists(self.tf_file):
            print("[Memory] main.tf not found, skipping indexing.")
            return

        print("[Memory] Indexing main.tf...")
        with open(self.tf_file, "r") as f:
            parsed = hcl2.load(f)

        docs = []
        for res in parsed.get("resource", []):
            for rtype, instances in res.items():
                provider = rtype.split("_")[0]
                for _, config in instances.items():
                    if provider == "aws" and rtype == "aws_instance":
                        content = (
                            f"[AWS VM]\nVM Name: {config['tags'].get('Name', 'N/A')}\n"
                            f"Region: {config.get('availability_zone', 'N/A')}\n"
                            f"Instance Type: {config.get('instance_type', 'N/A')}\n"
                            f"Disk Size: {config.get('root_block_device', [{}])[0].get('volume_size', 'N/A')} GB"
                        )
                        docs.append(Document(page_content=content, metadata={"source": "main.tf"}))
                    elif provider == "azurerm" and rtype in ["azurerm_virtual_machine", "azurerm_linux_virtual_machine"]:
                        content = (
                            f"[Azure VM]\nVM Name: {config.get('name', 'N/A')}\n"
                            f"Resource Group: {config.get('resource_group_name', 'N/A')}\n"
                            f"Location: {config.get('location', 'N/A')}\n"
                            f"VM Size: {config.get('size', 'N/A')}\n"
                            f"OS Disk Size: {config.get('os_disk', [{}])[0].get('disk_size_gb', 'N/A')} GB"
                        )
                        docs.append(Document(page_content=content, metadata={"source": "main.tf"}))
                    elif provider == "google" and rtype == "google_compute_instance":
                        content = (
                            f"[GCP VM]\nVM Name: {config['name']}\n"
                            f"Zone: {config['zone']}\n"
                            f"Machine Type: {config['machine_type']}\n"
                            f"Disk Size: {config['boot_disk'][0]['initialize_params'][0]['size']} GB"
                        )
                        docs.append(Document(page_content=content, metadata={"source": "main.tf"}))

        if docs:
            self.vectorstore.add_documents(docs)
            self.save()
            print(f"[Memory] Indexed {len(docs)} VM(s) from main.tf.")
        else:
            print("[Memory] No VMs found in main.tf.")

    # ----------------------
    # Excel Indexing
    # ----------------------
    def index_vm_sheet(self):
        self._remove_old_docs("vm_details.xlsx")
        if not os.path.exists(self.vm_sheet):
            print("[Memory] VM details sheet not found, skipping indexing.")
            return

        print("[Memory] Indexing vm_details.xlsx...")
        df = pd.read_excel(self.vm_sheet)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        required_columns = ["vm_name", "zone", "disk_size", "cpu", "memory", "os"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"[Memory] Missing required columns: {missing_columns}")
            return

        docs = []
        for _, row in df.iterrows():
            content = (
                f"VM Name: {row['vm_name']}\n"
                f"Zone: {row['zone']}\n"
                f"Disk Size: {row['disk_size']}GB\n"
                f"CPU: {row['cpu']}\n"
                f"Memory: {row['memory']}\n"
                f"OS: {row['os']}"
            )
            docs.append(Document(page_content=content, metadata={"source": "vm_details.xlsx"}))

        if docs:
            self.vectorstore.add_documents(docs)
            self.save()
            print(f"[Memory] Indexed {len(docs)} VM(s) from vm_details.xlsx.")

    # ----------------------
    # PDF Indexing
    # ----------------------
    def index_pdf(self):
        self._remove_old_docs("infra_details.pdf")
        if not os.path.exists(self.pdf_file):
            print("[Memory] PDF not found, skipping indexing.")
            return

        print("[Memory] Indexing infra_details.pdf...")
        loader = PyPDFLoader(self.pdf_file)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = "infra_details.pdf"

        if docs:
            self.vectorstore.add_documents(docs)
            self.save()
            print(f"[Memory] Indexed {len(docs)} pages from infra_details.pdf.")

    # ----------------------
    # Remove Old Docs by Source
    # ----------------------
    def _remove_old_docs(self, source_name):
        self.vectorstore.docstore._dict = {
            k: v for k, v in self.vectorstore.docstore._dict.items() if v.metadata.get("source") != source_name
        }

    # ----------------------
    # File Watcher
    # ----------------------
    def _start_watcher(self):
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, memory):
                self.memory = memory

            def on_modified(self, event):
                if event.src_path.endswith("main.tf"):
                    print("\n[Watcher] main.tf changed -> Re-indexing...")
                    self.memory.index_main_tf()
                elif event.src_path.endswith("vm_details.xlsx"):
                    print("\n[Watcher] vm_details.xlsx changed -> Re-indexing...")
                    self.memory.index_vm_sheet()
                elif event.src_path.endswith("infra_details.pdf"):
                    print("\n[Watcher] infra_details.pdf changed -> Re-indexing...")
                    self.memory.index_pdf()

        observer = Observer()
        handler = ChangeHandler(self)
        observer.schedule(handler, "./Agents/modules/terraform", recursive=False)
        observer.schedule(handler, "./Agents/modules/infra", recursive=False)
        observer.start()

        print("[Memory] Watching main.tf, vm_details.xlsx, and infra_details.pdf for changes...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    # ----------------------
    # Retrieve Combined Context
    # ----------------------
    def get_relevant_documents(self, query):
        try:
            docs = self.vectorstore.similarity_search(query, k=10)
        except ValueError as e:
            print(f"[Memory] Retrieval error: {e}. Rebuilding FAISS index...")
            self._create_empty_index()
            self._first_time_index()
            docs = self.vectorstore.similarity_search(query, k=10)

        print("\n[Memory] Retrieved relevant docs:")
        for d in docs:
            print(f"- Source: {d.metadata['source']} | Snippet: {d.page_content[:80]}...")

        # ✅ Prioritize: PDF > Excel > Terraform
        pdf_docs = [d for d in docs if d.metadata["source"] == "infra_details.pdf"]
        excel_docs = [d for d in docs if d.metadata["source"] == "vm_details.xlsx"]
        tf_docs = [d for d in docs if d.metadata["source"] == "main.tf"]

        return pdf_docs + excel_docs + tf_docs


# ✅ Initialize Memory
memory = MemoryStore()
