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
import bcrypt
import glob
import hashlib
import base64
from typing import Dict

import tables as tables
import install_vfnet as install_vfnet
import vfup as vfup

NIC_DIR = "/sys/class/net"
LSPCI_OUTPUT = []

# Declare a list to store NIC information
# Do not use directly except from within this file
_physical_nics: Dict[str, dict] = {}
_vf_nics: Dict[str, dict] = {}
_detection_complete = False

def detection_complete():
    """
    Check if detection has already been run.

    Returns:
        bool: True if detection has already been run.
    """
    return _detection_complete

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
                virtfn = []
                for virtfn_file in virtfn_files:
                    virtfn_pci_address = os.path.basename(os.path.realpath(virtfn_file))
                    virtfn.append(virtfn_pci_address)

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

            # Store the VF NIC information and parent in the _vf_nics dictionary
            _vf_nics[vf_pci_address] = {
                'pci_address': vf_pci_address,
                'interface': vf_interface,
                'parent_pci_address': parent_pci_address,
                'device_path': device_path,
                'mac_address': mac_address if mac_address else "unknown",
            }
    for vf in _vf_nics.values():

        pf = _physical_nics[vf['parent_pci_address']]

        # determine the vf number of the vf
        vf_num = 0
        virtfns = pf['virtfn']
        for i in range(len(virtfns)):
            if virtfns[i] == vf['pci_address']:
                vf_num = i + 1
                break

        # Calculate deterministic salt based on device name
        salt = base64.urlsafe_b64encode(hashlib.sha256(pf['device_name'].encode()).digest()).decode()[:23].replace('-', 'a').replace('_', 'b')
        salt_str = '$2b${}${}'.format("12",salt)
        # calculate bcrypted mac address
        vf_mac_bcrypted = bcrypt.hashpw(f"${pf['mac_address']}v{vf_num}".encode(), salt_str.encode()).decode()
        # calc the sha256 of the bcrypted mac address and show it in hex
        vf_mac = (hashlib.sha256(vf_mac_bcrypted.encode()).hexdigest())[:12]
        
        # Force to LAA Unicast MAC Address
        vf_mac_bytes = bytes.fromhex(vf_mac)
        vf_mac_bytes = bytearray(vf_mac_bytes)
        vf_mac_bytes[0] = (vf_mac_bytes[0] | 0b00000010) & 0b11111110
        vf_mac_laa = vf_mac_bytes.hex()
        vf_mac_formatted = ':'.join([vf_mac_laa[i:i+2] for i in range(0, len(vf_mac_laa), 2)])

        vf['calc_mac_address'] = vf_mac_formatted


        # print(" - Detection Complete.")
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

# TODO: Move to list library
def print_physical_nics():

    # Detect network devices if not already detected
    if not _detection_complete:
        print("Error: Network devices detection has not been completed yet.")

    vf_config = {}

    # Try to load in settings from file
    if(install_vfnet.is_installed()):
        vf_config = vfup.read_vf_config()
    
    nics = [copy.copy(nic_dict) for nic_dict in _physical_nics.values()]
    for nic in nics:
        if nic['sriov_capable'] and nic['sriov_totalvfs'] > 0:
            nic['can_vf_display'] = 'Yes'
            nic['vfs_display'] = "{}/{}".format(nic['sriov_numvfs'], nic['sriov_totalvfs'])
        else:
            nic['can_vf_display'] = 'No'
            nic['vfs_display'] = ''
        if nic['interface'] in vf_config:
            nic['vfs_configured'] =  "{}/{}".format(vf_config[nic['interface']], nic['sriov_totalvfs'])
        else:
            nic['vfs_configured'] = 'N/A'

    # Define the keys and headers for the physical NICs table
    keys = ['pci_address', 'interface', 'subsystem', 'device_name', 'driver', 'can_vf_display', 'vfs_display', 'vfs_configured', 'iommu_group', 'device_path']
    headers = ['PCI BDF', 'Interface', 'Subsystem', 'Description', 'Driver', 'Can VF?', 'Active VFs', 'Config VFs', 'IOMMU Grp', 'Device Path']

    # Print the physical NICs table
    print("\nPF Network Devices:")
    tables.print_table(nics, keys, headers, 'pci_address')

# TODO: Move to list library
def print_vf_nics():
    
    # Detect network devices if not already detected
    if not _detection_complete:
        print("Error: Network devices detection has not been completed yet.")

    nics = [copy.copy(nic_dict) for nic_dict in _vf_nics.values()]

    for nic in nics:
        parent = _physical_nics[nic['parent_pci_address']]
        # Detect if parent was found
        if parent:
            nic['parent_interface'] = parent['interface']
        else:
            nic['parent_interface'] = 'Unknown'
        

    # Define the keys and headers for the VF network devices table
    keys = ['pci_address', 'interface', 'mac_address', 'parent_interface', 'parent_pci_address', 'device_path']
    headers = ['PCI BDF', 'Interface', 'MAC Address', 'Parent', 'Parent BDF', 'Device Path']

    # Print the VF network devices table
    print("\nVF Network Devices:")
    tables.print_table(nics, keys, headers, ['parent_interface', 'pci_address'])

    print("")
    # Try to load in settings from file
    if(not install_vfnet.is_installed()):
        print("vfnet is not installed. Run 'vfnet install' then 'vfnet persist' to persist configured VF network devices.")
    