# === File: main.py ===
from langchain.agents import Tool
from langchain.agents import initialize_agent
from langchain_community.llms import Ollama

from modules.parser import parse_request
from langchain_core.agents import AgentAction,AgentFinish
from modules.terraform_io import read_terraform
from modules.vm_manager import modify_disk, create_vm
from modules.terraform_runner import run_tf_plan, run_tf_apply, run_tf_destroy, run_tf_init,confirm_then_run,init_and_plan,plan_then_confirm_apply



llm = Ollama(model="llama3")

tools = [
    Tool(name="ParseRequest", func=parse_request, description="Parses user input into structured action"),
    Tool(name="ReadTerraform", func=read_terraform, description="Reads the Terraform file content"),
    Tool(name="ModifyDiskSize", func=modify_disk, description="Modifies disk size in Terraform HCL"),
    Tool(name="CreateVM", func=create_vm, description="Creates a new VM in Terraform HCL"),
    Tool(
        name="TerraformInit",
        func=run_tf_init,
        description="Initializes the Terraform working directory. Must be run before plan or apply."
    ),
    Tool(
        name="TerraformPlan",
        func=confirm_then_run(run_tf_plan, "Terraform is about to run PLAN. Proceed?"),
        description="Runs 'terraform plan'. Only works if 'terraform init' was run beforehand and asks for apply confirmation from user"
    ),
    Tool(
        name="TerraformApply",
        func=confirm_then_run(run_tf_apply, "Terraform is about to APPLY changes. Proceed?"),
        description="Runs 'terraform apply'. Only works if 'terraform init' and 'terraform plan' were run beforehand"
    ),
    Tool(
        name="TerraformDestroy",
        func=confirm_then_run(run_tf_destroy, "Terraform is about to DESTROY infrastructure. Proceed?"),
        description="Destroy infrastructure using Terraform"
    ),
    Tool(
        name="InitAndPlan",
        func=confirm_then_run(init_and_plan, "Terraform is about to run INIT and PLAN. Proceed?"),
        description="Initialize and plan Terraform changes"
    ),
    Tool(
    name="TerraformPlanThenApply",
    func=plan_then_confirm_apply,
    description="Plans the infrastructure and then asks for confirmation before applying it."
)


    
]

# Tool names that require confirmation
tools_requiring_confirmation = ["TerraformApply","TerraformPlan","TerraformDestroy", "ModifyDiskSize", "CreateVM"]

# Create the agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
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
        if type(e).__name__ == "CancelledByUser":
            print(f"\n🚫 {e}")
            continue  # Go back to user input
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

 
