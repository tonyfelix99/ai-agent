import hcl2
import re

class DiskModifierTool:
    def __init__(self, tf_file="./Agents/modules/terraform/main.tf"):
        self.tf_file = tf_file

    def run(self, command: str) -> str:
        """Entry point for executor_node: Parse commands like 'resize-disk <vm_name> <new_size>'"""
        parts = command.split()
        if len(parts) != 3 or parts[0] != "resize-disk":
            return "[DiskModifier] Invalid command format. Use: resize-disk <vm_name> <new_size>"

        _, vm_name, new_size = parts
        return self.modify_disk_size(vm_name, new_size)

    def modify_disk_size(self, vm_name, new_size):
        """Modify the disk size of a VM in main.tf and save changes."""
        try:
            # ✅ Extract numeric part if given as "50GB", "50 gb", etc.
            if isinstance(new_size, str):
                match = re.search(r'\d+', new_size)
                if match:
                    new_size = int(match.group())
                else:
                    return f"[DiskModifier] Invalid size format: {new_size}"
            else:
                new_size = int(new_size)

            with open(self.tf_file, "r") as f:
                parsed = hcl2.load(f)

            modified = False
            for res in parsed.get("resource", []):
                for rtype, instances in res.items():
                    for _, config in instances.items():
                        # ✅ Azure
                        if rtype in ["azurerm_linux_virtual_machine", "azurerm_virtual_machine"] and config["name"] == vm_name:
                            config["os_disk"][0]["disk_size_gb"] = new_size
                            modified = True
                        # ✅ AWS
                        elif rtype == "aws_instance" and config.get("tags", {}).get("Name") == vm_name:
                            config["root_block_device"][0]["volume_size"] = new_size
                            modified = True
                        # ✅ GCP
                        elif rtype == "google_compute_instance" and config["name"] == vm_name:
                            config["boot_disk"][0]["initialize_params"][0]["size"] = new_size
                            modified = True

            if not modified:
                return f"[DiskModifier] VM '{vm_name}' not found in main.tf."

            # Save updated HCL back to main.tf
            self._write_hcl(parsed)
            return f"[DiskModifier] Disk size for VM '{vm_name}' updated to {new_size}GB."

        except Exception as e:
            return f"[DiskModifier] Error modifying disk size: {str(e)}"

    def _write_hcl(self, parsed_hcl):
        """Convert parsed HCL (dict) back to text and save it."""
        hcl_lines = []
        for res in parsed_hcl.get("resource", []):
            for rtype, instances in res.items():
                for name, config in instances.items():
                    hcl_lines.append(f'resource "{rtype}" "{name}" ' + "{")
                    for key, value in config.items():
                        if isinstance(value, list) and isinstance(value[0], dict):
                            hcl_lines.append(f"  {key} {{")
                            for sub_k, sub_v in value[0].items():
                                if isinstance(sub_v, list) and isinstance(sub_v[0], dict):
                                    hcl_lines.append(f"    {sub_k} {{")
                                    for s_k, s_v in sub_v[0].items():
                                        hcl_lines.append(f"      {s_k} = \"{s_v}\"")
                                    hcl_lines.append("    }")
                                else:
                                    hcl_lines.append(f"    {sub_k} = \"{sub_v}\"")
                            hcl_lines.append("  }")
                        else:
                            hcl_lines.append(f"  {key} = \"{value}\"")
                    hcl_lines.append("}\n")

        with open(self.tf_file, "w") as f:
            f.write("\n".join(hcl_lines))
