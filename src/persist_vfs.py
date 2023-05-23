# The command function for vfnet persist

import text_help as text_help
import detection as detection
import vfup as vfup
import install_vfnet as install_vfnet

from typing import List, Dict, Union, Any

def print_help():
    """Prints the help information for vfnet persist"""
    print("Usage: vfnet persist [OPTIONS] [ARGS]...")
    print("")
    print("\nOptions:")
    option_help = [
        ['-h, --help', 'Print help information'],
    ]
    for option in option_help:
        option_name = option[0]
        option_description = option[1]
        wrapped_description = text_help.wrap_text(option_description, 73)
        for i, description_line in enumerate(wrapped_description):
            print("  {:<14}{}".format(option_name if i == 0 else "", description_line))

    print("\n Arguments:")
    command_help = [
        ['<no args>','When no arguments are passed, persists the current number of virtual functions for all network devices'],
        ['[interface]', 'Persists the current number VFs for the specified network device'],
        ['[interface] [number]', 'Persists the specified number of VFs for the specified network device']
    ]
    for command in command_help:
        command_name = command[0]
        command_description = command[1]
        wrapped_description = text_help.wrap_text(command_description, 67)
        for i, description_line in enumerate(wrapped_description):  
            print("  {:<23}{}".format(command_name if i == 0 else "", description_line))

# Executed when the user calls vfnet persist [COMMAND_ARGS]
def persist_command(command_args: List[str]):
    """
    Persists the number of virtual functions for a network device across reboots

    Args:
        command_args (list): The arguments for the persist command. 
                              Assumes you have already removed the "vfnet persist"
                              portion.
    """

    network_device = None
    target_vfs = None
    for arg in command_args:
        if not arg.startswith("-"):
            if(network_device == None):
              network_device = arg
            elif(target_vfs == None):
              target_vfs = int(arg)
              break
            
        
    # If no arguments are passed, persist the current number of VFs for all network devices
    if network_device == None:
        _persist_for_all_devices()
    else:
        _persist_for_device(network_device, target_vfs)

def _persist_for_all_devices():
    """Persists the current number of virtual functions for all network devices"""
    # detect
    detection.detect_network_devices()

    # get all network devices
    pfs = detection.physical_nics().values()

    for pf in pfs:
        # Check if pf supports SR-IOV
        if(pf['sriov_capable']):
          _persist_for_device(pf['interface'])


def _persist_for_device(network_device: str, target_vfs: int = None):
    """
    Persists the specified number of virtual functions for the specified network device

    Args:
        network_device (str): The network device to persist the number of VFs for
        target_vfs (int): The number of VFs to persist for the specified network device
                          if None is passed, persists the current number of VFs
    """

    # Check for vfnet is installed
    if not install_vfnet.is_installed():
        raise ValueError("vfnet is not installed on this system. Run 'vfnet install' to install vfnet first")
    
    # Check if service is enabled
    if not install_vfnet.is_service_enabled():
        # Notify user that service is not enabled, but can still persist VF settings, they just won't run on boot
        print("Warning: vfnet service is not enabled. VF settings will be saved, but will not be applied on boot")
        
    # detect
    detection.detect_network_devices()
    # get the network device from detection
    pf = detection.get_pf(network_device)

    if(pf == None):
        raise ValueError("The specified network device does not exist")

    # Check if pf supports SR-IOV
    if(pf['sriov_totalvfs'] == 0):
        raise ValueError("The specified network device does not support SR-IOV")
    
    # check if total_vfs is less than greater than 
    curr_vfs = pf['sriov_numvfs']
    vfs_to_set = curr_vfs if target_vfs == None else target_vfs

    # check if vfs_to_set is less than 0 or greater than total_vfs
    if(vfs_to_set < 0 or vfs_to_set > pf['sriov_totalvfs']):
        raise ValueError("The specified number of VFs is invalid for the specified network device")
    
    # TODO: only output if verbose
    print("Persisting {} VFs for {}".format(vfs_to_set, pf['interface']))

    # set vfs
    vfup.persist_pf_config(pf['interface'], vfs_to_set)
    