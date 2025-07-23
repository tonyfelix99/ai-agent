from langchain_core.agents import AgentAction, AgentFinish
 
from langchain_core.agents import AgentExecutor  # Add this import if needed

# Initialize or import your agent here
agent = AgentExecutor(...)  # Replace ... with appropriate arguments for your agent

def invoke_with_confirmation(user_input: str):
    steps = agent.iter(user_input)
    for step in steps:
        if isinstance(step, AgentAction):
            print(f"\n🤖 Proposed Action: {step.tool} -> {step.tool_input}")
            
            # Prompt for confirmation only on critical tools
            if step.tool in ["ModifyDiskSize", "CreateVM", "TerraformApply", "TerraformDestroy"]:
                confirm = ask_user("This action might modify infrastructure. Proceed? (yes/no): ")
                if confirm.strip().lower() not in ["yes", "y"]:
                    return f"❌ Action '{step.tool}' was cancelled by user."

        elif isinstance(step, AgentFinish):
            return step.return_values["output"]
