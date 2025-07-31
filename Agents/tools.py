# tools.py
from langchain.agents import Tool
from modules.parser import parse_request
from modules.vm_manager import modify_disk

def modify_disk_wrapper(input_str: str) -> str:
    # Expects format: "mode=increment;amount=50"
    try:
        parts = dict(item.split("=") for item in input_str.split(";"))
        mode = parts.get("mode")
        amount = int(parts.get("amount"))  # Ensure amount is integer
        return modify_disk({"mode": mode, "amount": amount})
    except Exception as e:
        return f"❌ Invalid ModifyDiskSize input: {e}"

def parse_request_wrapper(request: str) -> str:
    result = parse_request(request)
    if result.get("action") == "ModifyDiskSize":
        # Ensure proper format for ModifyDiskSize tool
        return f"mode={result['mode']};amount={result['amount']}"
    else:
        raise ValueError(f"❌ Unsupported action: {result.get('action')}")

tools = [
    Tool.from_function(
        name="ParseRequest",
        description="Parse natural language disk resize requests like 'make it 300GB' or 'add 50GB'. Returns mode and amount.",
        func=parse_request_wrapper
    ),
    Tool.from_function(
        name="ModifyDiskSize",
        description="Modify disk size in main.tf. Input: 'mode=increment|absolute;amount=INT'",
        func=modify_disk_wrapper
    ),
]
