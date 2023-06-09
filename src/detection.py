############################################################
#
# Detection Library
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Date Created: 2023-05-20
# Last Modified: 2023-05-28
#
# The methods in this library help with detecting the
# current status of the VFs on the server.
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

import os
import subprocess
import copy
import glob
from typing import Dict, List, Union, TypedDict, List, Union, TypedDict

import tables as tables
import install_vfnet as install_vfnet
import vfup as vfup
import ip_link as ip_link

NIC_DIR = "/sys/class/net"
LSPCI_OUTPUT = []

class PhysicalNIC(TypedDict):
    pci_address: str
    interface: str
    device_path: str
    subsystem: str
    device_name: str
    driver: str
    module: str
    iommu_group: str
    vendor: str
    sriov_capable: bool
    sriov_numvfs: int
    sriov_totalvfs: int
    mac_address: str
    virtfn: dict[str, dict[str, str]]

class VFNIC(TypedDict):
    pci_address: str
    interface: str
    parent_pci_address: str
    device_path: str
    mac_address: Union[str, None]
    device_name: str
    driver: str
    module: str
    iommu_group: str
    vendor: str
    ip_link_vfinfo: dict[str, str]
    vf_num: int

# Declare a list to store NIC information
# Do not use directly except from within this file
_physical_nics: Dict[str, PhysicalNIC] = {}
_vf_nics: Dict[str, VFNIC] = {}
_detection_complete = False

def detection_complete():
    """
    Check if detection has already been run.

    Returns:
        bool: True if detection has already been run.
    """
    return _detection_complete

def clear_cache():
    """
    Clear the cache of detected network devices.
    """
    global _detection_complete, _physical_nics, _vf_nics
    _detection_complete = False
    _physical_nics = {}
    _vf_nics = {}

def physical_nics():
    """
    Get a copy of the list of physical NICs.

    Returns:
        dict: A copy of the list of physical NICs.
    """
    return copy.deepcopy(_physical_nics)

def vf_nics():
    """
    Get a copy of the list of virtual NICs.

    Returns:
        dict: A copy of the list of virtual NICs.
    """
    return copy.deepcopy(_vf_nics)

def get_pf(network_device):
    """
    Get the physical function (PF) for a given network device.
    Assumes that detection already have been run.

    Args:
        network_device (str): PCI address or Interface Name of 
                                the network device to manage.
    
    Returns:
        dict: A copy PF for the given network device. None if not found.
    """
    # Loop through the physical nics checking both th pci_address
    # and interface keys for a match
    for nic in _physical_nics.values():
        if nic["interface"] == network_device:
            return copy.deepcopy(nic)
        elif nic["pci_address"] == network_device:
            return copy.deepcopy(nic)
    return None

def get_vf(network_device):
    """
    Get the virtual function (VF) for a given network device.
    Assumes that detection already have been run.

    Args:
        network_device (str): PCI address or Interface Name of 
                                the network device to manage.
    
    Returns:
        dict: A copy VF for the given network device. None if not found.
    """
    # Loop through the physical nics checking both th pci_address
    # and interface keys for a match
    for vf in _vf_nics.values():
        if vf["interface"] == network_device:
            return copy.deepcopy(vf)
        elif vf["pci_address"] == network_device:
            return copy.deepcopy(vf)
    return None

def get_module_of_vf_by_pf(pf_interface_name: str, vf_index: int) -> str:
    """
    Get the kernel module name of a VF network device using only its parent and vf number sysfs

    Args:
        interface_name (str): The interface name of the VF network device (e.g. eth0).
    """
    # verify that the interface exists via sysfs
    if not os.path.exists(os.path.join(NIC_DIR, pf_interface_name)):
        raise ValueError(f"Interface '{pf_interface_name}' does not exist.")
    
    # verify that the interface has a vf at the index specified
    if not os.path.exists(os.path.join(NIC_DIR, pf_interface_name, "device", "virtfn" + str(vf_index))):
        raise ValueError(f"Interface '{pf_interface_name}' does not have a VF at index {vf_index}.")

    # Get the kernel module name of the VF network device
    module_name = os.path.basename(os.path.realpath(os.path.join(NIC_DIR, pf_interface_name, "device", "virtfn" + str(vf_index), "driver", "module")))
    print("module_name: " + module_name)
    return module_name

def _get_mac_address(device: str) -> str:
    """
    Returns the MAC address of the specified VF network device.
    """
    with open(f'/sys/class/net/{device}/address', 'r') as f:
        mac_address = f.read().strip()
    return mac_address
    
def detect_network_devices():
    global _detection_complete, _physical_nics, _vf_nics
    # print("------ Detecting network devices... ------")

    ip_link_output = ip_link.get_ip_link()

    # Loop through each network device
    for device in os.listdir(NIC_DIR):
        device_path = os.path.join(NIC_DIR, device)

        is_device = os.path.isdir(os.path.join(device_path, "device"))
        is_pf = is_device and not os.path.islink(os.path.join(device_path, "device", "physfn"))

        # Check if the device is a physical NIC
        if is_pf:
            # Determine the PCI address for the physical NIC
            pci_address = os.path.basename(os.path.realpath(os.path.join(device_path, "device")))
            
            # Get the subsystem for the physical NIC
            subsystem = "unknown"
            if os.path.exists(os.path.join(device_path, "device", "subsystem")) and os.path.islink(os.path.join(device_path, "device", "subsystem")):
              subsystem = os.path.basename(os.path.realpath(os.path.join(device_path, "device", "subsystem")))

            # Get the interface name for the physical NIC
            interface = os.path.basename(os.path.realpath(device_path))

            # Determine if the nic is capable of SR-IOV
            sriov_capable = False
            if os.path.exists(os.path.join(device_path, "device", "sriov_numvfs")):
              sriov_capable = True
            
            # if capable, get the number of VFs
            sriov_numvfs = 0
            if sriov_capable:
              with open(os.path.join(device_path, "device", "sriov_numvfs"), 'r') as f:
                sriov_numvfs = int(f.read())
            
            # if capable, get the maximum number of VFs
            sriov_totalvfs = 0
            if sriov_capable:
              with open(os.path.join(device_path, "device", "sriov_totalvfs"), 'r') as f:
                sriov_totalvfs = int(f.read())
            
            if sriov_capable and sriov_totalvfs == 0:
                sriov_capable = False

            # for now only use PFs attached directly to the PCI bus
            if subsystem == "pci":
                # Execute lspci command and store the output
                lspci_output = subprocess.run(["lspci", "-vmmks", pci_address], capture_output=True, text=True)
                lines = lspci_output.stdout.strip().split('\n')

                pci_data = {}

                for line in lines:
                    key, value = line.strip().split(':', 1)
                    pci_data[key] = value.strip()

                mac_address = _get_mac_address(interface)

                # Catalog all the virtfn* files in the device's sysfs directory and the underlying pci address linked by the virtfn files
                virtfn_files = glob.glob(os.path.join(device_path, "device", "virtfn*"))
                virtfn_files.sort()
                virtfn = {}
                for virtfn_file in virtfn_files:
                    virtfn_pci_address = os.path.basename(os.path.realpath(virtfn_file))
                    virtfn_name = os.path.basename(virtfn_file)
                    vf_index = int(virtfn_name.replace("virtfn", ""))
                    virtfn[virtfn_name] = {
                        'vf': vf_index, 
                        'pci_address': virtfn_pci_address,
                        'virtfn_name': virtfn_pci_address,
                        'parent_pci_address': pci_address,
                        'parent_interface': interface,
                        'virtfn_path': virtfn_file,
                    }

                # Store the NIC information in the _physical_nics dictionary
                _physical_nics[pci_address] = {
                    'pci_address': pci_address,
                    'interface': interface,
                    'device_path': device_path,
                    'subsystem': subsystem,
                    'device_name': pci_data.get('Device', 'unknown'),
                    'driver': pci_data.get('Driver','unknown'),
                    'module': pci_data.get('Module','unknown'),
                    'iommu_group': pci_data.get('IOMMUGroup','unknown'),
                    'vendor': pci_data.get('Vendor','unknown'),
                    'sriov_capable': sriov_capable,
                    'sriov_numvfs': sriov_numvfs,
                    'sriov_totalvfs': sriov_totalvfs,
                    'mac_address': mac_address,
                    'virtfn': virtfn
                }

        # Check if the device is a VF network device
        if is_device and not is_pf:
            vf_pci_address = os.path.basename(os.path.realpath(os.path.join(device_path, "device")))

            # Get the VF interface name
            vf_interface = device

            # Get the parent device path
            parent_path = os.path.realpath(os.path.join(device_path, "device", "physfn"))
            parent_pci_address = os.path.basename(parent_path)

            mac_address = _get_mac_address(vf_interface)

            # Execute lspci command and store the output
            lspci_output = subprocess.run(["lspci", "-vmmks", vf_pci_address], capture_output=True, text=True)
            lines = lspci_output.stdout.strip().split('\n')

            pci_data = {}

            for line in lines:
                key, value = line.strip().split(':', 1)
                pci_data[key] = value.strip()

            # Store the VF NIC information and parent in the _vf_nics dictionary
            _vf_nics[vf_pci_address] = {
                'pci_address': vf_pci_address,
                'interface': vf_interface,
                'parent_pci_address': parent_pci_address,
                'device_path': device_path,
                'mac_address': mac_address if mac_address else "unknown",
                'device_name': pci_data.get('Device', 'unknown'),
                'driver': pci_data.get('Driver','unknown'),
                'module': pci_data.get('Module','unknown'),
                'iommu_group': pci_data.get('IOMMUGroup','unknown'),
                'vendor': pci_data.get('Vendor','unknown'),
            }
    


    # Go through pfs and check if they have any VFs
    for pf_pci_address, pf in _physical_nics.items():
        # check if ip_link_output has key pf['interface']
        if pf['interface'] not in ip_link_output:
            continue
        if 'vfinfo_list' not in ip_link_output[pf['interface']]:
            continue
        ip_link_vfinfo_list = ip_link_output[pf['interface']]['vfinfo_list']
        # iterate through the virtfn dictionary
        for vf_name, virtfn in pf['virtfn'].items():
            ip_link_vfinfo = {}
            for ip_link_vf in ip_link_vfinfo_list:                
                if(ip_link_vf['vf'] == virtfn['vf']):
                    ip_link_vfinfo = ip_link_vf

            vf_pci_address = virtfn['pci_address']
            parent_pci_address = pf_pci_address
            device_path = virtfn['virtfn_path']
            mac_address = ip_link_vfinfo['address'] if ip_link_vfinfo else "unknown"

            # try to find any VFs that did not show up in the net search
            # this usually means they are already assigned to a VM
            if virtfn['pci_address'] not in _vf_nics:

                # Execute lspci command and store the output
                lspci_output = subprocess.run(["lspci", "-vmmks", vf_pci_address], capture_output=True, text=True)
                lines = lspci_output.stdout.strip().split('\n')

                pci_data = {}

                for line in lines:
                    key, value = line.strip().split(':', 1)
                    pci_data[key] = value.strip()
                    
                # add the vf to the _vf_nics dictionary
                _vf_nics[virtfn['pci_address']] = {
                'pci_address': vf_pci_address,
                'interface': None,
                'parent_pci_address': parent_pci_address,
                'device_path': device_path,
                'mac_address': mac_address,
                'device_name': pci_data.get('Device', 'unknown'),
                'driver': pci_data.get('Driver','unknown'),
                'module': pci_data.get('Module','unknown'),
                'iommu_group': pci_data.get('IOMMUGroup','unknown'),
                'vendor': pci_data.get('Vendor','unknown'),

                }
            # Attach ip link data to the vf
            _vf_nics[virtfn['pci_address']]['ip_link_vfinfo'] = ip_link_vfinfo
            _vf_nics[virtfn['pci_address']]['vf_num'] = virtfn['vf']


    _detection_complete = True


def print_detection_results():
    # Detect network devices if not already detected
    if not _detection_complete:
        print("Error: Network devices detection has not been completed yet.")

    # Count the number of physical NICs
    num_physical_nics = len(_physical_nics)

    # Print the number of physical NICs detected
    if num_physical_nics == 0:
        print(" - No physical NICs detected.")
    elif num_physical_nics == 1:
        print(" - 1 physical NIC detected.")
    else:
        print(f" - {num_physical_nics} physical NICs detected.")

    # Count the number of VF NICs
    num_vf_nics = len(_vf_nics)

    # Print the number of VF NICs detected
    if num_vf_nics == 0:
        print(" - No VF network devices detected.")
    elif num_vf_nics == 1:
        print(" - 1 VF network device detected.")
    else:
        print(f" - {num_vf_nics} VF network devices detected.")
