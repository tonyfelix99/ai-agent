# === File: main.py ===
from langchain.agents import Tool
from langchain.agents import initialize_agent
from langchain_community.llms import Ollama

from modules.parser import parse_request
from modules.terraform_io import read_terraform
from modules.vm_manager import modify_disk, create_vm
from modules.prompt_user import ask_user
from modules.terraform_runner import run_tf_init,run_tf_plan,run_tf_init,run_tf_apply,run_tf_destroy

llm = Ollama(model="llama3")

tools = [
    Tool(name="ParseRequest", func=parse_request, description="Parses user input into structured action"),
    Tool(name="ReadTerraform", func=read_terraform, description="Reads the Terraform file content"),
    Tool(name="ModifyDiskSize", func=modify_disk, description="Modifies disk size in Terraform HCL"),
    Tool(name="CreateVM", func=create_vm, description="Creates a new VM in Terraform HCL"),
    Tool(name="AskForConfirmation", func=ask_user, description="Asks for user confirmation"),
    Tool(name="TerraformInit", func=run_tf_init, description="Initializes Terraform in the working directory"),
    Tool(name="TerraformPlan", func=run_tf_plan, description="Runs terraform plan"),
    Tool(name="TerraformApply", func=run_tf_apply, description="Runs terraform apply"),
    Tool(name="TerraformDestroy", func=run_tf_destroy, description="Runs terraform destroy")
]

agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True,
)

# === Interactive chat loop ===
print("🛠️ DevOps Assistant Chat (type 'exit' to quit)")
while True:
    user_input = input("\n> You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting assistant.")
        break
    try:
        response = agent.invoke(user_input)
        print(f"\n🤖 Assistant: {response}")
    except Exception as e:
        print(f"\n⚠️ Error: {e}")


# === File: modules/parser.py ===
def parse_request(input: str) -> str:
    # This is a placeholder; ideally, you parse with regex or structured LLM output
    return f"Parsed: action=increase_disk, vm=dev-vm, region=us-central1, size=100GB"


# === File: modules/terraform_io.py ===
def read_terraform(_: str) -> str:
    try:
        with open("hcl/main.tf", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "main.tf not found"


# === File: modules/vm_manager.py ===
def modify_disk(input: str) -> str:
    # Simulate HCL modification
    return f"Updated dev-vm disk size to {input} in main.tf"

def create_vm(input: str) -> str:
    return f"Appended new VM block to main.tf for {input}"


# === File: modules/prompt_user.py ===
def ask_user(_: str) -> str:
    return input("Do you want to continue? (yes/no): ")


# === File: modules/terraform_runner.py ===
def run_tf_init(_: str) -> str:
    return "Terraform init output: ✓ Initialization complete"

def run_tf_plan(_: str) -> str:
    return "Terraform plan output: ✓ Changes detected"

def run_tf_apply(_: str) -> str:
    return "Terraform apply output: ✓ Changes applied"

def run_tf_destroy(_: str) -> str:
    return "Terraform destroy output: ✓ Resources destroyed"


