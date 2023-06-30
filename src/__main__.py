############################################################
# 
# VFnet. A Virtual Function manager for network devices
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Version: 0.1
# Date Created: 2020-05-20
# Last Modified: 2020-05-20
#
# This program is designed to help setup and manage virtual 
# network devices for SR-IOV capable network devices and
# server.
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

import install_vfnet 
import set_vfs
import persist_vfs
import list_vfs
import text_help
import sys
import importlib

MODULE_DEPS = ['bcrypt']

version_number = "0.1.5-develop"

def print_help():
    """Prints the help information for vfnet"""
    print("Usage: vfnet [OPTIONS] COMMAND [ARGS]...")
    print("")
    print("A Virtual Function manager for network devices")
    print_version()
    print("\nOptions:")
    option_help = [
        ['-h, --help', 'Print help information'],
        ['-v, --version', 'Print version information']
    ]
    for option in option_help:
        option_name = option[0]
        option_description = option[1]
        wrapped_description = text_help.wrap_text(option_description, 73)
        for i, description_line in enumerate(wrapped_description):
            print("  {:<14}{}".format(option_name if i == 0 else "", description_line))

    print("\nCommands:")
    command_help = [
        ['install', 'Install vfnet'],
        ['create', 'Create virtual functions for a network device. Alias for "set". Will throw errors if VFs already exist.'],
        ['set', 'Modifies the number of virtual functions for a network device'],
        ['persist', 'Persists the number of virtual functions for a network device across reboots'],
        ['list', 'List detected network devices']
    ]
    for command in command_help:
        command_name = command[0]
        command_description = command[1]
        wrapped_description = text_help.wrap_text(command_description, 73)
        for i, description_line in enumerate(wrapped_description):  
            print("  {:<14}{}".format(command_name if i == 0 else "", description_line))

def print_version():
    """Prints the version of vfnet"""
    print("{}".format(version_number))

def check_module_dependencies():
    missing_modules = []
    for module_name in MODULE_DEPS:
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing_modules.append(module_name)

    if missing_modules:
        print("The following python modules are missing. Please install them with pip before continuing:")
        for module_name in missing_modules:
            print(module_name)
        sys.exit()
    #else:
        #print("All modules are installed.")

def main():
    # The first parameter that is not a switch is the command
    command = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            command = arg
            break

    # Check if -h or --help is passed, print help
    if "-h" in sys.argv or "--help" in sys.argv:
        # If persist command is passed, defer to the persist command help
        if command == "persist":
            persist_vfs.print_help()
        if command == "set" or command == "create":
            set_vfs.print_help()
        else:
            print_help()
        sys.exit()

    # Check if -v or --version is passed, print version
    if "-v" in sys.argv or "--version" in sys.argv:
        print_version()
        sys.exit()



    # If no arguments are passed or -l or --list is passed, detect network devices
    if len(sys.argv) == 1 or command == "list":
        check_module_dependencies()
        # Run the 'install' function from the `install_vfnet` module
        list_vfs.list_network_devices()
        sys.exit()

    if command == "install":
        check_module_dependencies()
        # Run the 'install' function from the `install_vfnet` module
        install_vfnet.install()
        sys.exit()

    elif command == "create" or command == "set":
        check_module_dependencies()
        set_vfs.set_command(sys.argv[2:])

    elif command == "persist":
        check_module_dependencies()
        persist_vfs.persist_command(sys.argv[2:])

    else:
        print("Error: Invalid command. Use '-h' or '--help' to see the available commands.")

    sys.exit()

if __name__ == '__main__':
  main()
  
