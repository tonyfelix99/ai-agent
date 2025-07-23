import subprocess


def run_tf_init(_: str) -> str:
    try:
        output = subprocess.check_output(["terraform", "init"], cwd="hcl", text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Terraform init failed:\n{e.output}"

def run_tf_plan(_: str) -> str:
    try:
        output = subprocess.check_output(["terraform", "plan"], cwd="hcl", text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Terraform plan failed:\n{e.output}"

def run_tf_apply(_: str) -> str:
    try:
        output = subprocess.check_output(["terraform", "apply", "-auto-approve"], cwd="hcl", text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Terraform apply failed:\n{e.output}"

def run_tf_destroy(_: str) -> str:
    try:
        output = subprocess.check_output(["terraform", "destroy", "-auto-approve"], cwd="hcl", text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Terraform destroy failed:\n{e.output}"