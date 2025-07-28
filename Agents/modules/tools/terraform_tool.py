import subprocess
import os

class TerraformTool:
    def __init__(self, working_dir="./Agents/modules/terraform"):
        self.working_dir = working_dir

    def run(self, command):
        """Run a Terraform CLI command in the given working directory."""
        print(f"[Terraform] Running: terraform {command}")
        result = subprocess.run(
            ["terraform"] + command.split(),
            cwd=self.working_dir,
            text=True,
            capture_output=True
        )
        if result.returncode == 0:
            print(f"[Terraform] Success:\n{result.stdout}")
            return result.stdout.strip()
        else:
            print(f"[Terraform] Error:\n{result.stderr}")
            return result.stderr.strip()

    def init(self):
        """Initialize Terraform providers if not already initialized."""
        terraform_dir = os.path.join(self.working_dir, ".terraform")
        if not os.path.exists(terraform_dir):
            print("[Terraform] No .terraform folder detected. Running init...")
            return self.run("init -input=false")
        else:
            print("[Terraform] .terraform already initialized. Skipping init.")
            return "Terraform already initialized."

    def plan(self):
        """Run terraform init (if needed) then plan."""
        self.init()
        return self.run("plan -no-color")

    def apply(self):
        """Run terraform init (if needed) then apply."""
        self.init()
        return self.run("apply -auto-approve -no-color")
