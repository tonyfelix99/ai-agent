import subprocess
import os

def get_hcl_dir():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hcl_dir = os.path.join(base_dir, "..", "hcl")
    if not os.path.exists(os.path.join(hcl_dir, "main.tf")):
        raise FileNotFoundError("main.tf not found in hcl directory.")
    return hcl_dir
