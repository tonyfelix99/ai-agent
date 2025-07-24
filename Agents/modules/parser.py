import re

def extract_actions_from_llm_output(output: object) -> list[str]:
    """
    Extracts Terraform-related actions from the LLM output.
    Accepts both clean and messy formats like bullet points, numbered lists, or paragraphs.
    Handles both string and AIMessage input.
    """

    # ✅ Extract content if output is an AIMessage or similar
    if hasattr(output, "content"):
        output = output.content

    output = output.strip()

    # Known supported actions
    valid_actions = {
        "TerraformInit", "TerraformPlan", "TerraformApply", "TerraformDestroy",
        "ModifyDiskSize", "CreateVirtualMachine", "DeleteVirtualMachine"
    }

    extracted = set()

    # Look for capitalized action names
    for match in re.findall(r"(Terraform[A-Z][a-zA-Z]+|ModifyDiskSize|CreateVirtualMachine|DeleteVirtualMachine)", output):
        if match in valid_actions:
            extracted.add(match)

    # Fallback if nothing was found
    if not extracted:
        lines = output.splitlines()
        for line in lines:
            for action in valid_actions:
                if action.lower() in line.lower():
                    extracted.add(action)

    return list(extracted)
