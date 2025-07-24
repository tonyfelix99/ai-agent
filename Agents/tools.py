# === tools.py ===
from langchain.tools import Tool
from modules.terraform_runner import run_tf_init, run_tf_plan, run_tf_apply, run_tf_destroy
from modules.vm_manager import modify_disk, create_vm
from modules.terraform_io import read_terraform

tools = [
    Tool.from_function(name="TerraformInit", func=run_tf_init, description="Run Terraform init"),
    Tool.from_function(name="TerraformPlan", func=run_tf_plan, description="Run Terraform plan"),
    Tool.from_function(name="TerraformApply", func=run_tf_apply, description="Run Terraform apply"),
    Tool.from_function(name="TerraformDestroy", func=run_tf_destroy, description="Run Terraform destroy"),
    Tool.from_function(name="ModifyDiskSize", func=modify_disk, description="Modify disk size of a VM"),
    Tool.from_function(name="CreateVM", func=create_vm, description="Add new VM to main.tf"),
    Tool.from_function(name="ReadTerraformFile", func=read_terraform, description="Read main.tf contents")
]