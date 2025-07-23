import os
import subprocess
import shutil
import json
import logging
from datetime import datetime
from langchain_ollama import OllamaLLM
import re
from pathlib import Path

# === CONFIG ===
TERRAFORM_FILE = "/mnt/c/Users/TonyFelix/Documents/AI-ASSISTANT/AzureVm/main.tf"
BACKUP_DIR = "/mnt/c/Users/TonyFelix/Documents/AI-ASSISTANT/AzureVm/backups"
LOG_FILE = "/mnt/c/Users/TonyFelix/Documents/AI-ASSISTANT/AzureVm/terraform_assistant.log"

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === LLM SETUP ===
llm = OllamaLLM(model="llama3")

class TerraformAssistant:
    def __init__(self, terraform_file_path, backup_dir):
        self.terraform_file = Path(terraform_file_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def read_terraform_file(self):
        """Read the Terraform file and return its content."""
        if not self.terraform_file.exists():
            logger.error(f"File not found: {self.terraform_file}")
            return ""
        
        try:
            with open(self.terraform_file, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Successfully read Terraform file: {self.terraform_file}")
                return content
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return ""

    def write_terraform_file(self, content):
        """Write content to Terraform file after creating a backup."""
        try:
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"main_{timestamp}.tf"
            shutil.copy(self.terraform_file, backup_path)
            logger.info(f"Backup saved to: {backup_path}")
            print(f"📦 Backup saved to: {backup_path}")

            # Write new content
            with open(self.terraform_file, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            logger.info("Terraform file updated successfully")
            
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            raise

    def validate_terraform_syntax(self, content):
        """Enhanced validation of Terraform syntax."""
        if not content or not content.strip():
            logger.warning("Content is empty")
            return False
            
        # Check for basic Terraform blocks
        required_patterns = [
            r'\bresource\s+"[^"]+"\s+"[^"]+"\s*\{',
            r'\bprovider\s+"[^"]+"\s*\{',
            r'\bdata\s+"[^"]+"\s+"[^"]+"\s*\{',
            r'\bmodule\s+"[^"]+"\s*\{',
            r'\bvariable\s+"[^"]+"\s*\{',
            r'\boutput\s+"[^"]+"\s*\{'
        ]
        
        has_terraform_block = any(re.search(pattern, content) for pattern in required_patterns)
        
        if not has_terraform_block:
            logger.warning("Content doesn't appear to contain valid Terraform blocks")
            return False
        
        # Check for balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        
        if open_braces != close_braces:
            logger.warning(f"Unbalanced braces: {open_braces} open, {close_braces} close")
            # Try to auto-balance if only off by one
            if abs(open_braces - close_braces) == 1:
                logger.info("Attempting to auto-balance braces")
                return self.try_auto_balance_braces(content, open_braces, close_braces)
            return False
            
        # Check for basic syntax issues
        if content.count('"') % 2 != 0:
            logger.warning("Unbalanced quotes detected")
            return False
            
        return True

    def try_auto_balance_braces(self, content, open_count, close_count):
        """Attempt to auto-balance braces if only off by one."""
        if open_count > close_count:
            # Missing closing brace - add it at the end
            content += "\n}"
            logger.info("Added missing closing brace")
        elif close_count > open_count:
            # Extra closing brace - try to remove the last one
            last_brace_pos = content.rfind('}')
            if last_brace_pos != -1:
                content = content[:last_brace_pos] + content[last_brace_pos+1:]
                logger.info("Removed extra closing brace")
        
        # Store the corrected content for potential use
        self._corrected_content = content
        return True

    def get_fix_from_llm(self, tf_code, user_task, error_msg="", retry_count=0):
        """Get updated Terraform configuration from LLM."""
        context = "You are a Terraform expert specializing in Azure infrastructure."
        
        if retry_count > 0:
            context += f" This is retry attempt #{retry_count}. The previous attempt had syntax issues (unbalanced braces). Please be extremely careful with brace matching - every opening brace {{ must have a corresponding closing brace }}."
        
        error_section = f"Terraform Error that needs to be fixed:\n{error_msg}\n" if error_msg else ""
        
        prompt = f"""
{context}

Below is the current Terraform file:
```hcl
{tf_code}
```

User request:
👉 "{user_task}"

{error_section}

CRITICAL INSTRUCTIONS:
- Return ONLY the updated full Terraform file content
- Use proper HCL (HashiCorp Configuration Language) syntax
- ENSURE ALL BRACES ARE BALANCED - count your opening and closing braces carefully
- Every resource block, provider block, and nested block MUST be properly closed
- Include all necessary providers and resources
- Do NOT include markdown formatting, explanations, or backticks
- Make minimal changes to fix the issue or implement the request
- Maintain existing resource naming conventions
- Double-check brace balance before responding

Output only valid HCL code:
"""
        
        logger.info(f"Sending prompt to LLM (attempt {retry_count + 1})")
        
        try:
            raw_response = llm.invoke(prompt).strip()
            logger.info("Received response from LLM")
            
            # Clean the response
            cleaned_response = self.clean_llm_response(raw_response)
            
            # Check if we have a corrected version from auto-balancing
            if hasattr(self, '_corrected_content'):
                cleaned_response = self._corrected_content
                delattr(self, '_corrected_content')
                logger.info("Using auto-corrected content with balanced braces")
            
            if not self.validate_terraform_syntax(cleaned_response):
                logger.warning("LLM response failed validation")
                if retry_count < 2:  # Allow up to 3 attempts
                    logger.info("Retrying with LLM...")
                    error_detail = "Previous attempt had syntax issues. Please ensure proper HCL syntax with balanced braces."
                    if error_msg:
                        error_detail += f"\n\nOriginal error: {error_msg}"
                    return self.get_fix_from_llm(tf_code, user_task, error_detail, retry_count + 1)
                else:
                    logger.error("LLM failed to generate valid Terraform code after multiple attempts")
                    # Return the best attempt we have, even if not perfect
                    print("⚠️ Warning: LLM struggled to generate perfect syntax. You may need to manually review the output.")
                    return cleaned_response
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Error getting fix from LLM: {e}")
            raise

    def clean_llm_response(self, raw_response):
        """Enhanced cleaning of LLM response to extract only valid HCL code."""
        # Remove markdown code blocks if present
        raw_response = re.sub(r'```\w*\n?', '', raw_response)
        raw_response = re.sub(r'```', '', raw_response)
        
        # Remove common LLM explanatory prefixes
        prefixes_to_remove = [
            r'^Here\'s the updated Terraform configuration:?\s*\n',
            r'^Here is the updated Terraform file:?\s*\n',
            r'^Updated Terraform configuration:?\s*\n',
            r'^The updated configuration is:?\s*\n'
        ]
        
        for prefix in prefixes_to_remove:
            raw_response = re.sub(prefix, '', raw_response, flags=re.IGNORECASE | re.MULTILINE)
        
        # Split into lines for processing
        lines = raw_response.splitlines()
        cleaned_lines = []
        terraform_started = False
        brace_count = 0
        
        for line in lines:
            stripped_line = line.strip()
            
            # Skip empty lines at the beginning
            if not terraform_started and not stripped_line:
                continue
                
            # Start capturing when we see terraform blocks
            if re.match(r'^\s*(resource|provider|variable|output|module|data|terraform|locals)\b', line):
                terraform_started = True
                cleaned_lines.append(line)
                brace_count += line.count('{') - line.count('}')
            elif terraform_started:
                # Continue capturing all lines after terraform blocks start
                cleaned_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                
                # If we've closed all braces and hit a non-terraform line, we might be done
                if brace_count == 0 and stripped_line and not re.match(r'^\s*(#|//)', line) and not any(char in stripped_line for char in '{}'):
                    # This might be explanatory text after the code, stop here
                    break
            elif not terraform_started and stripped_line and not stripped_line.startswith('#'):
                # Skip explanatory text before terraform blocks
                continue
            else:
                # Include comments and empty lines if terraform has started
                if terraform_started:
                    cleaned_lines.append(line)
        
        result = "\n".join(cleaned_lines).strip()
        
        # Final cleanup - remove any trailing explanatory text that might have slipped through
        result = re.sub(r'\n\n[A-Za-z][^{}\n]*$', '', result, flags=re.MULTILINE | re.DOTALL)
        
        logger.info(f"Cleaned LLM response - {len(lines)} lines -> {len(cleaned_lines)} lines")
        return result

    def run_terraform_command(self, command, cwd=None):
        """Run a terraform command and return the result."""
        if cwd is None:
            cwd = self.terraform_file.parent
            
        logger.info(f"Running terraform command: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command, 
                cwd=cwd, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Command successful: {' '.join(command)}")
            else:
                logger.warning(f"Command failed with return code {result.returncode}")
                
            return result
            
        except subprocess.TimeoutExpired:
            logger.error("Terraform command timed out")
            raise
        except Exception as e:
            logger.error(f"Error running terraform command: {e}")
            raise

    def get_error_suggestions(self, tf_code, user_task, error_msg):
        """Get detailed suggestions and explanations for fixing Terraform errors."""
        prompt = f"""
You are a Terraform expert consultant. Instead of providing code, give detailed explanations and suggestions.

Current Terraform Configuration:
```hcl
{tf_code}
```

User's Original Request: "{user_task}"

Terraform Error Output:
{error_msg}

Please provide a detailed analysis in the following format:

## 🔍 ERROR ANALYSIS
[Explain what the error means in simple terms]

## 🎯 ROOT CAUSE
[Identify the specific cause of the error]

## 💡 STEP-BY-STEP SOLUTION
[Provide numbered steps to fix the issue]

## ⚠️ THINGS TO WATCH OUT FOR
[Mention any potential pitfalls or considerations]

## 📚 ADDITIONAL CONTEXT
[Any relevant Terraform/Azure best practices or documentation links]

Be detailed in your explanations but keep it practical and actionable. Focus on helping the user understand WHY the fix is needed, not just WHAT to change.
"""
        
        logger.info("Requesting error analysis from LLM")
        
        try:
            response = llm.invoke(prompt).strip()
            logger.info("Received error analysis from LLM")
            return response
            
        except Exception as e:
            logger.error(f"Error getting suggestions from LLM: {e}")
            return f"❌ Error getting suggestions: {e}\n\nPlease analyze the error manually:\n{error_msg}"

    def provide_specific_guidance(self, error_output, current_code):
        """Provide more specific guidance based on error patterns."""
        print("\n🔍 SPECIFIC GUIDANCE BASED ON ERROR PATTERNS:")
        print("-" * 60)
        
        # Common error patterns and suggestions
        error_patterns = {
            r"Error: Reference to undeclared resource": {
                "issue": "Resource Reference Error",
                "explanation": "You're referencing a resource that doesn't exist or is misspelled.",
                "solution": "Check resource names and ensure they match exactly (case-sensitive)."
            },
            r"Error: Duplicate resource": {
                "issue": "Duplicate Resource Definition", 
                "explanation": "You have defined the same resource twice with the same name.",
                "solution": "Remove the duplicate resource or rename one of them."
            },
            r"Error: Invalid resource name": {
                "issue": "Invalid Naming Convention",
                "explanation": "Resource names must follow specific naming rules.",
                "solution": "Use only letters, numbers, underscores, and hyphens. No spaces or special characters."
            },
            r"Error: Missing required argument": {
                "issue": "Required Parameter Missing",
                "explanation": "A required parameter is not specified in your resource configuration.",
                "solution": "Add the missing required parameter to your resource block."
            },
            r"Error: Unsupported argument": {
                "issue": "Invalid Parameter",
                "explanation": "You're using a parameter that doesn't exist for this resource type.",
                "solution": "Check the Terraform documentation for valid parameters for this resource."
            }
        }
        
        found_patterns = []
        for pattern, info in error_patterns.items():
            if re.search(pattern, error_output, re.IGNORECASE):
                found_patterns.append(info)
        
        if found_patterns:
            for i, pattern_info in enumerate(found_patterns, 1):
                print(f"\n{i}. 🎯 {pattern_info['issue']}")
                print(f"   📖 Explanation: {pattern_info['explanation']}")
                print(f"   🔧 Solution: {pattern_info['solution']}")
        else:
            print("No specific patterns detected. Please refer to the full error analysis above.")
        
        print("\n💡 TIP: Make small, incremental changes and test each one with 'terraform plan'.")

    def show_current_file(self):
        """Display the current Terraform file content."""
        current_content = self.read_terraform_file()
        if current_content:
            print("\n" + "="*60)
            print("📄 CURRENT TERRAFORM FILE CONTENT:")
            print("="*60)
            
            # Add line numbers for easier reference
            lines = current_content.splitlines()
            for i, line in enumerate(lines, 1):
                print(f"{i:3d} | {line}")
            
            print("="*60)
        else:
            print("❌ Could not read current file content.")

    def modify_terraform_file(self, task_description):
        """Main method to modify Terraform file based on user task."""
        try:
            print("\n📄 Reading existing Terraform configuration...")
            tf_code = self.read_terraform_file()
            if not tf_code:
                return False

            print("\n🧠 Getting updated configuration from LLM...")
            raw_response = self.get_fix_from_llm(tf_code, task_description)

            print("\n🔍 LLM-generated updated Terraform configuration:\n")
            print("=" * 60)
            print(raw_response)
            print("=" * 60)

            confirm = input("\n✅ Do you want to apply this update? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("❌ Change cancelled.")
                return False

            self.write_terraform_file(raw_response)
            print("✅ Terraform file updated successfully.")

            # Ask about running terraform plan
            run_plan = input("\n🔍 Run 'terraform plan' to validate? (yes/no): ").strip().lower()
            if run_plan in ['yes', 'y']:
                return self.handle_terraform_workflow(task_description)
            else:
                print("🔁 Skipped terraform plan.")
                return True
                
        except Exception as e:
            logger.error(f"Error in modify_terraform_file: {e}")
            print(f"❌ Error: {e}")
            return False

    def handle_terraform_workflow(self, task_description):
        """Handle the terraform init, plan, and apply workflow."""
        try:
            repo_dir = self.terraform_file.parent
            
            # Run terraform init
            print("\n🔄 Running terraform init...")
            init_result = self.run_terraform_command(
                ["terraform", "init", "-input=false", "-upgrade"], 
                repo_dir
            )
            
            if init_result.returncode != 0:
                print("❌ Terraform init failed:")
                print(init_result.stderr)
                return False

            # Run terraform plan
            print("\n📋 Running terraform plan...")
            plan_result = self.run_terraform_command(["terraform", "plan"], repo_dir)

            if plan_result.returncode == 0:
                print("✅ Plan successful!")
                print(plan_result.stdout)
                
                run_apply = input("\n🚀 Do you want to apply these changes? (yes/no): ").strip().lower()
                if run_apply in ['yes', 'y']:
                    apply_result = self.run_terraform_command(
                        ["terraform", "apply", "-auto-approve"], 
                        repo_dir
                    )
                    if apply_result.returncode == 0:
                        print("🎉 Changes applied successfully!")
                        return True
                    else:
                        print("❌ Apply failed:")
                        print(apply_result.stderr)
                        return False
                else:
                    print("⏭️ Apply skipped.")
                    return True
            else:
                print("⚠️ Terraform plan failed. Attempting to fix...")
                return self.handle_terraform_error(plan_result, task_description)
                
        except Exception as e:
            logger.error(f"Error in terraform workflow: {e}")
            print(f"❌ Terraform workflow error: {e}")
            return False

    def handle_terraform_error(self, error_result, task_description):
        """Handle terraform errors by providing detailed suggestions for manual fixing."""
        error_output = error_result.stderr + "\n" + error_result.stdout
        print("\n🔧 Analyzing error and generating suggestions...")
        
        try:
            current_code = self.read_terraform_file()
            suggestions = self.get_error_suggestions(current_code, task_description, error_output)
            
            print("\n" + "="*80)
            print("🚨 TERRAFORM ERROR ANALYSIS & SUGGESTIONS")
            print("="*80)
            print(suggestions)
            print("="*80)
            
            print("\n📝 Please manually edit your Terraform file based on these suggestions.")
            print("💡 After making changes, you can return to this assistant to continue.")
            
            while True:
                user_choice = input("\nChoose an option:\n"
                                  "1. I've made the changes - continue with terraform workflow\n"
                                  "2. Show me the current file content\n"
                                  "3. Get more specific suggestions\n"
                                  "4. Return to main menu\n"
                                  "Enter choice (1-4): ").strip()
                
                if user_choice == "1":
                    print("🔄 Continuing with terraform workflow...")
                    return self.handle_terraform_workflow(task_description)
                elif user_choice == "2":
                    self.show_current_file()
                elif user_choice == "3":
                    self.provide_specific_guidance(error_output, current_code)
                elif user_choice == "4":
                    return False
                else:
                    print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except Exception as e:
            logger.error(f"Error analyzing terraform error: {e}")
            print(f"❌ Error analyzing terraform issues: {e}")
            return False

def main():
    """Main function to run the Terraform AI Assistant."""
    assistant = TerraformAssistant(TERRAFORM_FILE, BACKUP_DIR)
    
    print("🤖 Enhanced Terraform AI Assistant with Manual Error Resolution")
    print("=" * 70)
    print("✨ Features:")
    print("  - AI-powered Terraform configuration generation")
    print("  - Detailed error analysis with step-by-step suggestions")  
    print("  - Manual control over all file modifications")
    print("  - Smart backup system")
    print("=" * 70)
    print("Commands:")
    print("  - Describe your terraform modification request")
    print("  - Type 'show' to view current file content")
    print("  - Type 'help' for more information")
    print("  - Type 'exit' to quit")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\n🔧 ai> Enter your request: ").strip()
            
            if user_input.lower() == "exit":
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "help":
                print("\n📚 HELP GUIDE:")
                print("-" * 50)
                print("🔹 MAKING REQUESTS:")
                print("   You can ask me to modify your Terraform configuration. Examples:")
                print("   • 'Add a new virtual machine with 4 GB RAM'")
                print("   • 'Change the VM size to Standard_B2s'") 
                print("   • 'Add a storage account with hot tier'")
                print("   • 'Remove the network security group'")
                print("\n🔹 ERROR HANDLING:")
                print("   When errors occur, I'll provide:")
                print("   • Detailed explanation of what went wrong")
                print("   • Step-by-step instructions to fix it")
                print("   • Common pitfalls to avoid")
                print("   • You maintain full control - no automatic fixes!")
                print("\n🔹 ADDITIONAL COMMANDS:")
                print("   • 'show' - Display current Terraform file")
                print("   • 'help' - Show this help message")
                print("   • 'exit' - Quit the assistant")
                continue
            elif user_input.lower() == "show":
                assistant.show_current_file()
                continue
            elif not user_input:
                print("⚠️ Please enter a request, 'show', 'help', or 'exit'.")
                continue
                
            success = assistant.modify_terraform_file(user_input)
            if success:
                print("✅ Task completed successfully!")
            else:
                print("❌ Task encountered issues. Please review the suggestions above.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            print(f"❌ Unexpected error: {e}")
            print("💡 You can continue using the assistant or type 'exit' to quit.")

if __name__ == "__main__":
    main()