# tools.py

from langchain.agents import Tool
from modules.parser import parse_request
from modules.vm_manager import modify_disk

def modify_disk_wrapper(input_str: str) -> str:
    return modify_disk(input_str)

def parse_request_wrapper(request: str) -> str:
    result = parse_request(request)
    if result["action"] == "ModifyDiskSize":
        return f"mode={result['mode']};amount={result['amount']}"
    else:
        return "action=unknown"

tools = [
    Tool.from_function(
        name="ParseRequest",
        description="Parses natural language disk resize requests like 'make it 300GB' or 'add 50GB'",
        func=parse_request_wrapper
    ),
    Tool.from_function(
        name="ModifyDiskSize",
        description="Updates disk size in the main.tf file. Input must be: mode=increment|absolute;amount=INT",
        func=modify_disk_wrapper
    ),
]
