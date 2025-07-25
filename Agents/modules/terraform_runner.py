import subprocess
import os

def get_hcl_dir():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hcl_dir = os.path.join(base_dir, "..", "hcl")
    if not os.path.exists(os.path.join(hcl_dir, "main.tf")):
        raise FileNotFoundError("main.tf not found in hcl directory.")
    return hcl_dir

class CancelledByUser(Exception):
    pass

def confirm_then_run(action_func, message: str):
    def wrapper(_: str) -> str:
        confirmation = input(f"\n⚠️  {message} (yes/no): ").strip().lower()
        if confirmation != "yes":
          raise CancelledByUser("Terraform operation cancelled by user.")
        return action_func("")
    return wrapper
def plan_then_confirm_apply(_: str) -> str:
    plan_output = run_tf_plan("")
    print(plan_output)  # Display plan
    confirm = input("Do you want to APPLY these changes? (yes/no): ").strip().lower()
    if confirm != "yes":
        raise CancelledByUser("Terraform operation cancelled by user.")
    return run_tf_apply("")
def run_tf_init(_: str) -> str:
    try:
        os.chdir(get_hcl_dir())
        result = subprocess.run(["terraform", "init"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running terraform init: {e}"

def run_tf_plan(_: str) -> str:
    try:
        os.chdir(get_hcl_dir())
        result = subprocess.run(["terraform", "plan"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running terraform plan: {e}"

def run_tf_apply(_: str) -> str:
    try:
        os.chdir(get_hcl_dir())
        result = subprocess.run(["terraform", "apply", "-auto-approve"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running terraform apply: {e}"

def run_tf_destroy(_: str) -> str:
    try:
        os.chdir(get_hcl_dir())
        result = subprocess.run(["terraform", "destroy", "-auto-approve"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running terraform destroy: {e}"

def init_and_plan(_: str) -> str:
    init_result = run_tf_init("")
    if "Error" in init_result or "failed" in init_result.lower():
        return f"Terraform init failed:\n{init_result}"
    return run_tf_plan("")

