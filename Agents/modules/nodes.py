from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain.memory import ConversationBufferMemory

from modules.llm import llm
from modules.parser import extract_actions_from_llm_output
from langchain_core.runnables import RunnableLambda
from modules.action_extractor import extract_actions_from_llm_output

def plan_node(memory):
    def _plan(state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = state["input"]
        print(f"\n🧠 User asked: {user_input}")

        prompt = f"""You are a DevOps assistant. Given the user's request below, list the Terraform-related actions needed in execution order.

Respond with only the action names, one per line, like this:

TerraformInit
TerraformPlan
TerraformApply

User request: {user_input}
"""

        # Save input to memory
        memory.save_context({"input": user_input}, {})

        # Call LLM
        response = llm.invoke(prompt)
        llm_output = response.content.strip()
        print(f"\n📋 Raw LLM plan:\n{llm_output}")

        # Save LLM output to memory
        memory.save_context({}, {"output": llm_output})

        # Extract actions
        actions = extract_actions_from_llm_output(llm_output)
        if not actions:
            print("⚠️ No valid actions parsed. Defaulting to: TerraformInit, TerraformPlan")
            actions = ["TerraformInit", "TerraformPlan"]

        # Return new state
        return {
            **state,
            "plan": llm_output,
            "actions": actions,
            "current_action": None,
        }

    return RunnableLambda(_plan)


def validate_node():
    def _validate(state: Dict[str, Any]) -> Dict[str, Any]:
        actions = state.get("actions")
        if actions is None:
            raise ValueError("❌ No actions found in state during validation step.")

        print(f"\n🧠 Planned Actions:\n{actions}")
        # Prompt for confirmation
        confirm = ask_user("Do you want to proceed with these actions? (yes/no): ")
        return {**state, "validation": confirm}

    return RunnableLambda(_validate)


# ✅ Get Next Action Node — pops next action from queue
def get_next_action_node():
    def _get_next(state):
        if state.get("actions"):
            state["current_action"] = state["actions"].pop(0)
        else:
            state["current_action"] = None
        return state

    return RunnableLambda(_get_next)


# ✅ Execute Node — runs the tool corresponding to the current action
def execute_node(tools):
    name_tool_map = {tool.name: tool for tool in tools}

    def _execute(state: Dict[str, Any]) -> Dict[str, Any]:
        action_name = state.get("current_action", "").strip()
        if not action_name or action_name not in name_tool_map:
            result = f"❌ No matching tool found: {action_name}"
        else:
            result = name_tool_map[action_name].invoke(state["input"])
        state["result"] = result
        return state

    return RunnableLambda(_execute)
