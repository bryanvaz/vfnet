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

import detection as detection


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
    detection.print_physical_nics()
    detection.print_vf_nics()

