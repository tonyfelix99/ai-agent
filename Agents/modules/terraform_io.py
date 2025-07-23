import os

TERRAFORM_PATH = "hcl/main.tf"

def read_terraform(_: str) -> str:
    if not os.path.exists(TERRAFORM_PATH):
        return "main.tf not found"
    with open(TERRAFORM_PATH, "r") as f:
        return f.read()

def write_terraform(content: str) -> str:
    try:
        with open(TERRAFORM_PATH, "w") as f:
            f.write(content)
        return "main.tf updated"
    except Exception as e:
        return f"Error writing Terraform file: {e}"
