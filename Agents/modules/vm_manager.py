from modules.terraform_io import read_terraform, write_terraform

# modules/vm_manager.py

import re

def modify_disk(input: str) -> str:
    try:
        # Step 1: Load Terraform file
        from modules.terraform_io import read_terraform, write_terraform
        tf_content = read_terraform("")

        # Step 2: Extract number from plain language
        match = re.search(r'(\d+)', input)
        if not match:
            return "[❌] Error: Couldn't extract disk size from input"

        amount = int(match.group(1))

        # Step 3: Find current size
        current_size_match = re.search(
            r'os_disk\s*{[^}]*?disk_size_gb\s*=\s*(\d+)',
            tf_content,
            re.DOTALL
        )

        if not current_size_match:
            return "[❌] Error: Could not find current disk size in tf_content"

        current_size = int(current_size_match.group(1))
        new_size = current_size + amount

        # Step 4: Replace and write
        updated_tf = re.sub(
            r'(os_disk\s*{[^}]*disk_size_gb\s*=\s*)\d+',
            rf'\g<1>{new_size}',
            tf_content,
            flags=re.DOTALL
        )
        write_terraform(updated_tf)

        return f"[✅] Disk size updated from {current_size} to {new_size}GB in main.tf"
    except Exception as e:
        return f"[❌] Error: {e}"


def create_vm(input: str) -> str:
    parts = dict(item.split("=") for item in input.split(";"))
    vm_name, region, size = parts["vm"], parts["region"], parts["size"]
    
    block = f"""
resource "azurerm_linux_virtual_machine" "{vm_name}" {{
  name                = "{vm_name}"
  location            = "{region}"
  resource_group_name = "your-rg-name"
  size                = "Standard_B1s"
  admin_username      = "azureuser"
  network_interface_ids = ["<nic_id>"]
  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size = ''.join(filter(str.isdigit, size))
...
disk_size_gb         = "{disk_size}"
  }}
  source_image_reference {{
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "20_04-lts"
    version   = "latest"
  }}
}}
"""
    tf = read_terraform("")
    updated = tf + "\n" + block
    result = write_terraform(updated)
    return f"Created VM block for {vm_name}. {result}"
