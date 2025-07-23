# modules/parser.py
import re

def parse_request(request: str):
    request = request.lower()

    # Relative increase: "add 50GB", "increase by 20GB"
    inc_match = re.search(r'(increase|add|raise).*?(\d+)\s*gb', request)
    # Absolute set: "make it 300GB", "set to 150GB"
    abs_match = re.search(r'(set|make|change).*?(\d+)\s*gb', request)

    if inc_match:
        return {
            "action": "ModifyDiskSize",
            "mode": "increment",
            "amount": int(inc_match.group(2))
        }

    elif abs_match:
        return {
            "action": "ModifyDiskSize",
            "mode": "absolute",
            "amount": int(abs_match.group(2))
        }

    return {"action": "unknown"}
