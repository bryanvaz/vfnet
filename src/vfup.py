# Used to operate on the vfnet config file used by vfup

import install_vfnet as install_vfnet

from typing import List, Dict, Union, Any

# Read configuration of vf interfaces from vfnet config file
def read_vf_config():
    """
    Read the vfnet config file and return the contents as a dictionary.
    """
    config_file = install_vfnet.get_config_file_location()

    if(not config_file):
        raise Exception("vfnet is not installed. Please install vfnet first.")
    
    vf_config: Dict[str,int] = {}

    # Read the config file and update the desired interface
    with open(config_file, 'r') as file:
        lines = file.readlines()

        for line in lines:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            else:
                interface, num_vfs = line.split(":")
                vf_config[interface] = int(num_vfs)

    return vf_config

# Persist vf interface configuration for a pf to the vfnet config file
def persist_pf_config(pf_interface, num_vfs):
    """
    Persist the number of VFs to create for a given PF interface to the vfnet config file.
    If the PF interface already exists in the config file, the number of VFs will be updated.
    If the PF interface does not exist in the config file, it will be added.
    
    * Does not verify if the PF interface exists on the system. 
        (vfup does this, or you should if you're calling this function)
    * Does not verify if the number of VFs is valid for the PF interface. 
        (vfup does this, or you should if you're calling this function)

    Args:
        pf_interface (str): The PF interface name (cannot be PCI address)
                            to persist the number of VFs for.
        num_vfs (int): The number of VFs to persist for the PF interface.
    """
    config_file = install_vfnet.get_config_file_location()

    if(not config_file):
        raise Exception("vfnet is not installed. Please install vfnet first.")
    
    updated_lines = []

    # Read the config file and update the desired interface
    with open(config_file, 'r') as file:
        lines = file.readlines()
        found = False

        for line in lines:
            if line.startswith(pf_interface + ":"):
                updated_lines.append(pf_interface + ":" + str(num_vfs) + "\n")
                found = True
            else:
                updated_lines.append(line)

        # If the interface was not found, append a new line
        if not found:
            updated_lines.append(pf_interface + ":" + str(num_vfs) + "\n")

    # Write the updated lines back to the config file
    with open(config_file, 'w') as file:
        file.writelines(updated_lines)