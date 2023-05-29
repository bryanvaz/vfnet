############################################################
#
# Set VF Library
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Date Created: 2020-05-20
# Last Modified: 2020-05-20
#
# Manages the settings of virtual functions (VFs) 
# on a given network device.
#
# Copyright (c) 2023 Bryan Vaz.
#
# This file is part of vfnet.
#
# vfnet is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any
# later version.
#
# vfnet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with vfnet. If not, see
# <https://www.gnu.org/licenses/>.
#
############################################################

import glob
import subprocess
import os
import copy
import time
import detection as detection
import text_help as text_help
import mac_generator as mac_generator
import ip_link as ip_link

from typing import List, Dict, Union, Any

def _detect():
    """
    Detect network devices if not already detected.
    """
    if not detection.detection_complete():
        detection.detect_network_devices()

def print_help():
    """Prints the help information for vfnet set"""
    print("Usage: vfnet set [OPTIONS] [ARGS]...")
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
        ['[interface] [number]', 'Persists the specified number of VFs for the specified network device']
    ]
    for command in command_help:
        command_name = command[0]
        command_description = command[1]
        wrapped_description = text_help.wrap_text(command_description, 67)
        for i, description_line in enumerate(wrapped_description):  
            print("  {:<23}{}".format(command_name if i == 0 else "", description_line))

# Executed when the user calls vfnet set [COMMAND_ARGS]
def set_command(command_args: List[str]):
    """
    Sets the number of virtual functions for a network device across reboots

    Args:
        command_args (list): The arguments for the persist command. 
                              Assumes you have already removed the "vfnet set"
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
    if(network_device == None or target_vfs == None):
        raise Exception("Error: Missing arguments. Please provide the name of the network device and the number of VFs to create.")
    set_vfs(network_device, target_vfs)

def set_vfs(network_device, num_vfs):
    """
    Sets the number virtual functions (VFs) for a given network device.
    
    Args:
        network_device (str): PCI address or Interface Name of 
                                the network device to manage.
        num_vfs (int): Number of VFs to create. Must be greater than zero
    
    Notes:
    *   Will not rerun detection if already run.
    *   Will throw an error if the maximum number of VFs is exceeded.
        This should be handled in the calling function to call with
        the correct number.
    *   Will throw an error if the network device does not exist.
    *   Will throw an error if the network device is not capable of
        creating VFs.
    *   Will destroy VFs if already exist!
    *   This function will attempt to wait for the VFs number to change
    """
    _detect()

    # Check if the network device exists
    pf = detection.get_pf(network_device)
    if pf is None:
        raise Exception("Network device not found.")
    
    # Check if the PF is capable of creating VFs
    if not pf["sriov_capable"] or pf["sriov_totalvfs"] == 0:
        raise Exception("Network device is not capable of creating VFs.")
    
    # check if num_vfs is an integer number
    if not isinstance(num_vfs, int):
        raise Exception("Number of VFs must be an integer between 0 and the maximum number of VFs ({})".format(pf["sriov_totalvfs"]))

    # If the number of VFs is greater than max_vfs, throw an error
    if num_vfs > pf["sriov_totalvfs"]:
        raise Exception("Number of VFs exceeds maximum number of VFs.")
    
    # check if the number of VFs is greater than or equal to zero
    if num_vfs < 0:
        raise Exception("Number of VFs must be greater than or equal to zero.")
    
    # Check if the number of VFs is already set to the correct number
    if pf["sriov_numvfs"] == num_vfs:
        print(f"Current VF count {pf['sriov_numvfs']} matches desired {num_vfs}. Doing nothing.")
        return
    
    # Check if the PF is already has VFs enabled and the desired number
    # is greater than zero (if the desired number is zero, then this is
    # a call to remove the VFs and the following code will handle that)
    if pf["sriov_numvfs"] > 0 and num_vfs > 0:
        # Delete all VFs if some exist. They have to be recreated
        print("Existing VFs found. Removing existing VFs...")
        delete_vfs(network_device)

    # Set the VFs
    # Write the number of VFs to the sriov_numvfs file
    print(f"Setting VFs to {num_vfs}...")
    _write_numvfs(pf["device_path"], num_vfs)
    
    # Wait for the number of VFs to change
    curr_numvfs = _read_numvfs(pf["device_path"])
    curr_virtfn = _count_virtfn(pf["device_path"])
    if(curr_numvfs != num_vfs or curr_virtfn != num_vfs):
        print(f"Waiting for VFs VFs to be created {num_vfs}...")
        for i in range(60):
            curr_numvfs = _read_numvfs(pf["device_path"])
            print(f"Current VFs: {curr_numvfs}")
            if curr_numvfs == num_vfs:
                break
            time.sleep(1)
        for i in range(60):
            # now check virtfnX directories
            curr_virtfn = _count_virtfn(pf["device_path"])
            print(f"Current virtfnX: {curr_virtfn}")
            if curr_virtfn == num_vfs:
                break
            time.sleep(1)

        for i in range(60):
            ip_link_output = ip_link.get_ip_link()
            ip_link_iface = ip_link_output[pf["interface"]]
            print(f"ip_link_iface: {ip_link_iface}")
            if(ip_link_iface != None):
                if(ip_link_iface["vfinfo_list"] != None):
                    vfinfo_list_len = len(ip_link_iface["vfinfo_list"])
                    print(f"Current ip link vf count: {vfinfo_list_len}")
                    if vfinfo_list_len == num_vfs:
                        break
            time.sleep(1)
        

    # Check if the number of VFs was set correctly
    if(curr_numvfs != num_vfs):
        raise Exception("Number of VFs was not set correctly. Expected {} VFs, but found {} VFs.".format(num_vfs, curr_numvfs))
    if(curr_virtfn != num_vfs):
        raise Exception("Number of VFs was not set correctly. Expected {} VFs, but found {} VFs.".format(num_vfs, curr_virtfn))
    
    print("VFs created successfully. Refreshing...")
    
    # loop through all VFs and set the MAC address
    resetvf_driver = False
    ip_link_output = ip_link.get_ip_link()
    ip_link_iface = ip_link_output[pf["interface"]]

    for vf_iface in ip_link_iface["vfinfo_list"]:
        mac_address = mac_generator.generate_mac(pf["mac_address"], vf_iface["vf"] ,pf["device_name"])
        if(vf_iface["address"] == mac_address):
            print(f"MAC address for VF {vf_iface['vf']} already set to {mac_address}. Doing nothing.")
            continue
        # set the mac address
        print(f"Setting MAC address for VF {vf_iface['vf']} from {vf_iface['address']} to {mac_address}...")
        ip_link.set_vf_mac_address(pf["interface"], vf_iface['vf'], mac_address)
        resetvf_driver = True

    # if one or more VFs had their mac address reset, the entire vf driver needs to be reloaded
    if(resetvf_driver):
        # detect kernel module name
        module_name = detection.get_module_of_vf_by_pf(pf["interface"],0)
        # Define the reload_vf_driver function
        print(f"At least one MAC address was reset. Reloading the vf driver {module_name}...")
        _reload_module(module_name)
        print("VF driver reloaded successfully.")


def _reload_module(module_name):
    subprocess.run(["modprobe", "-r", module_name])
    subprocess.run(["modprobe", module_name])

    
    
def _write_numvfs(device_path: str, num_vfs: int) -> None:
    """
    Writes the number of virtual functions (VFs) to be enabled on a given network device to sysfs.
    * Does not wait for the number of VFs to change.

    Args:
        device_path (str): Path to the network device to manage.
        num_vfs (int): Number of VFs to enable.
    """
    with open(os.path.join(device_path, "device", "sriov_numvfs"), "w") as f:
        f.write(str(num_vfs))

def _read_numvfs(device_path: str) -> int:
    """
    Reads the number of virtual functions (VFs) enabled on a given network device from sysfs.

    Args:
        device_path (str): Path to the network device to manage.

    Returns:
        int: Number of VFs enabled on the network device.
    """
    with open(os.path.join(device_path, "device", "sriov_numvfs"), "r") as f:
        return int(f.read())

def _count_virtfn(device_path: str) -> int:
    """
    Counts the number of virtfn devices enabled on a given network device.

    Args:
        device_path (str): Path to the network device to manage.

    Returns:
        int: Number of virtfn devices enabled on the network device.
    """
    virtfn_paths = glob.glob(os.path.join(device_path, "device", "virtfn*"))
    return len(virtfn_paths)

def delete_vfs(network_device):
    """
    Deletes all virtual functions (VFs) for a given network device.

    Args:
        network_device (str): Name of the network device to manage.
    """
    set_vfs(network_device, 0)
    

def get_vf_status(network_device, vf_index):
    """
    Get the status of a specific virtual function (VF) of a network device.

    Args:
        network_device (str): Name of the network device to manage.
        vf_index (int): Index of the VF to get the status of.

    Returns:
        str: Status of the VF (e.g., "enabled" or "disabled").
    """
    # Implement your code here
    raise Exception("'get_vf_status' Function not implemented")


