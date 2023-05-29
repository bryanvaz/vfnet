############################################################
#
# Tlist_network_devices.py. A module for listing network devices.
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Date Created: 2020-05-24
# Last Modified: 2020-05-24
#
# Formats the output of a table to be printed 
# to the console.
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

import copy
import tables as tables
import detection as detection
import install_vfnet as install_vfnet
import vfup as vfup

def list_network_devices():
    """
    List the detected network devices.
    Calls print_network_devices with no arguments
    """

    print_network_devices()


def print_network_devices(devices = None):
    """
    Print the list of network devices.

    Args:
        devices (list): List of network devices to print.
    """\
    
    print("------ Detecting network devices... ------")
    detection.detect_network_devices()
    print(" - Detection Complete.")
    detection.print_detection_results()
    print_physical_nics()
    print_vf_nics()



# TODO: Move to list library
def print_physical_nics():

    _physical_nics = detection.physical_nics()

    vf_config = {}

    # Try to load in settings from file
    if(install_vfnet.is_installed()):
        vf_config = vfup.read_vf_config()
    nics = list(_physical_nics.values())
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
    _physical_nics = detection.physical_nics()

    vf_nics = list(detection.vf_nics().values())

    for nic in vf_nics:
        parent = _physical_nics[nic['parent_pci_address']]
        # Detect if parent was found
        if parent:
            nic['parent_interface'] = parent['interface']
        else:
            nic['parent_interface'] = 'Unknown'
        

    # Define the keys and headers for the VF network devices table
    keys = ['pci_address', 'interface', 'mac_address', 'parent_interface', 'vf_num', 'driver', 'device_name', 'parent_pci_address', 'device_path']
    headers = ['PCI BDF', 'Interface', 'MAC Address', 'Parent', 'VF #','Driver', 'Description', 'Parent BDF', 'Device Path']

    # Print the VF network devices table
    print("\nVF Network Devices:")
    tables.print_table(vf_nics, keys, headers, ['parent_interface', 'pci_address'])

    print("")
    # Try to load in settings from file
    if(not install_vfnet.is_installed()):
        print("vfnet is not installed. Run 'vfnet install' then 'vfnet persist' to persist configured VF network devices.")
    