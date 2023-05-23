############################################################
# 
# VFnet installation script
#
# Author: Bryan Vaz <bryan@bryanvaz.com>
# Date Created: 2020-05-20
# Last Modified: 2020-05-20
#
# This script installs the VFnet scripts and configuration
# files for use in a server to the server's manage VFs.
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
import shutil
import subprocess
import sys
import pkgutil

_VFNET_INSTALL_DIR = '/etc/vfnet'
_VFNET_VFUP_FILE_NAME = 'vfup'
_VFNET_VFUP_PATH = os.path.join(_VFNET_INSTALL_DIR, _VFNET_VFUP_FILE_NAME)
_VFNET_CONFIG_FILE_NAME = 'vf.config'
_VFNET_CONFIG_FILE_PATH = os.path.join(_VFNET_INSTALL_DIR, _VFNET_CONFIG_FILE_NAME)
_VFNET_SERVICE_NAME = 'vfnet-create'
_VFNET_SERVICE_FILE_NAME = _VFNET_SERVICE_NAME + '.service'

vfnet_create_service_file_text = '''
[Unit]
Description=Create VF Network Interfaces on boot
# Requires=ifupdown-pre.service
Wants=network.target
After=local-fs.target network-pre.target network.target systemd-sysctl.service systemd-modules-load.service ifupdown-pre.service
Before=shutdown.target network-online.target
Conflicts=shutdown.target

[Install]
WantedBy=multi-user.target
WantedBy=network-online.target

[Service]
Type=oneshot
# EnvironmentFile=-/etc/default/networking
ExecStart=/bin/sh -c /sbin/vfup -a
# ExecStart=/sbin/vfup -a --read-environment
# ExecStop=/sbin/vfdown -a --read-environment
RemainAfterExit=true
TimeoutStartSec=5min

'''
vf_config_example_file_text = '''
# Settings for VF network interfaces
# This file is autogenerated by the vf manager
# 
# The structure defines the number of VF network devices to create for each PF devices.
# For example, the following creates 4 VF devices for the eth1 PF:
# eth1:4

'''

def get_config_file_location():
    """
    Get the location of the VFNET_CONFIG file.
    If the file does not exist then return None which means the user should install vfnet first
    """
    if os.path.exists(_VFNET_CONFIG_FILE_PATH):
        return _VFNET_CONFIG_FILE_PATH
    else:
        return None
    
def is_installed():
    """
    Checks if vfnet is installed.
    Checks for:
    * vfup file in /sbin
    * checks for vf.config file in /etc/vfnet
    
    Does not check if service is running
    """
    # Check if vfup is present in the /sbin directory
    if not os.path.exists(_VFNET_VFUP_PATH):
        return False
    # Check if vf.config is present in the /etc/vfnet directory
    if not os.path.exists(_VFNET_CONFIG_FILE_PATH):
        return False
    # If all checks pass then return True
    return True

def is_service_enabled():
    """
    Check if the vfnet-create service is enabled.
    (Also checks if vfup is installed - which is required
    for the service to work properly)
    """
    # Check if installed
    if not is_installed():
        return False
    # Check if service is enabled
    return _is_service_enabled()

def _verify_permissions():
    # Verify if the user has write permissions for /etc and /sbin directories
    if not os.access('/etc', os.W_OK) or not os.access('/sbin', os.W_OK):
        print("You need superuser permissions to run this script.")
        sys.exit(1)

def _create_directory(directory):
    # Create the specified directory if it does not already exist
    if not os.path.exists(directory):
        os.makedirs(directory)

def _copy_vfnet_files():
    # Get the current directory of the script
    src_dir = os.path.dirname(os.path.abspath(__file__))

    # Check if the current directory is the same as the install directory
    # if so then do not copy the files
    if src_dir == _VFNET_INSTALL_DIR:
        # TODO: Only print on verbose setting
        print("The current directory is the same as the install directory.")
        print("The files have not been copied.")
        return

    # Define the source paths of the vfup and vf.config.example files
    vfup_file = os.path.join(src_dir, 'vfup')
    print('script: ' + __file__)
    current_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    print('current_dir: ' + current_dir)

    executable_path = sys.executable
    executable_name = os.path.basename(executable_path)
    executable_dir = os.path.dirname(executable_path)
    print('executable_path: ' + executable_path)
    print('executable_dir: ' + executable_dir)
    # TODO: Install the vfnet release script to the directory as well?
    is_binary = False
    is_zip_bundle = False
    if (executable_name != 'python3' and executable_name != 'python' and __file__.endswith('.pyc') ):
            is_binary = True
    else:
        # check if current_dir is not a directory and actually a file
        if os.path.isfile(current_dir):
            # check if the current_dir starts with the shebang '#!/usr/bin/env python3'
            with open(current_dir, 'rb') as f:
                first_line = f.readline().decode('utf-8', errors='ignore')
                if first_line.startswith('#!/usr/bin/env python3'):
                    # this means it's a python script in zip format
                    is_zip_bundle = True
                    
    if (is_binary and executable_dir == _VFNET_INSTALL_DIR) or (is_zip_bundle and os.path.dirname(current_dir) == _VFNET_INSTALL_DIR):
        print("The executable file is already in the install directory.")
    else:
        if(is_binary):
            # Copy the executable file to the _VFNET_INSTALL_DIR directory
            shutil.copy(executable_path, _VFNET_INSTALL_DIR)
            # remove the symlink if it exists
            if os.path.exists(os.path.join('/usr/bin', 'vfnet')):
                os.remove(os.path.join('/usr/bin', 'vfnet'))
            # symlink the executable file to the /usr/bin directory
            os.symlink(os.path.join(_VFNET_INSTALL_DIR, executable_name), os.path.join('/usr/bin', 'vfnet'))
        elif(is_zip_bundle):
            shutil.copy(current_dir, _VFNET_INSTALL_DIR)
            # remove the symlink if it exists
            if os.path.exists(os.path.join('/usr/bin', 'vfnet')):
                os.remove(os.path.join('/usr/bin', 'vfnet'))
            # symlink the executable file to the /usr/bin directory
            os.symlink(os.path.join(_VFNET_INSTALL_DIR, os.path.basename(current_dir)), os.path.join('/usr/bin', 'vfnet'))
        else:
            print("The current python script is not compiled for independent execution.")

    if(is_zip_bundle):
        # Read the contents of the file from the zip bundle
        file_contents = pkgutil.get_data('__main__', 'vfup')
        if file_contents is not None:
            content = file_contents.decode('utf-8')
            # print(content)
            with open(_VFNET_VFUP_PATH, 'w') as f:
                f.write(content)
    else:
        # read in contents of vfup_file then write to _VFNET_VFUP_PATH
        # shutil.copy(vfup_file, _VFNET_VFUP_PATH)
        with open(vfup_file, 'r') as f:
            vfup_file_text = f.read()
        with open(_VFNET_VFUP_PATH, 'w') as f:
            f.write(vfup_file_text)

    # Check if vf.config already exists
    if os.path.exists(_VFNET_CONFIG_FILE_PATH):
        print("A vf.config file already exists in the destination directory.")
        print("The existing file has not been modified.")
    else:
        # write the vf_config_example_file_text file to the /etc/vfnet directory
        with open(_VFNET_CONFIG_FILE_PATH, 'w') as f:
            f.write(vf_config_example_file_text)

    # write the vf_config_example_file_text file to the /etc/vfnet directory
    config_example_dest = os.path.join(_VFNET_INSTALL_DIR, '{}.example'.format(_VFNET_CONFIG_FILE_NAME))
    with open(config_example_dest, 'w') as f:
        f.write(vf_config_example_file_text)

def _install_service_unit():
    """
    Writes the vfnet_create_service_file_text
    to the vfnet-create.service file in the 
    /lib/systemd/system directory. Then symlinks the file to
    the /etc/systemd/system directory.

    Does not enable the service.
    Assumes you have permissions to write to the /lib/systemd/system
    """
    # Define the paths for the service file and the symlink
    service_dest = os.path.join('/lib/systemd/system', _VFNET_SERVICE_FILE_NAME)
    service_symlink = os.path.join('/etc/systemd/system', _VFNET_SERVICE_FILE_NAME)

    # Write the service file to the /lib/systemd/system directory
    with open(service_dest, 'w') as f:
        f.write(vfnet_create_service_file_text)

    # check if the symlink already exists and is a file or is a symlink to another location
    # meaning the user has overridden the default service file
    if os.path.lexists(service_symlink):
        if os.path.realpath(service_symlink) != os.path.realpath(service_dest):
            print("The vfnet-create service file has been overridden by user in {}. Does not point to expected location {}".format(service_symlink, service_dest))
            print("The overridden vfnet-create service file has not been changed.")
            return

    # Create a symlink to the service file in the /etc/systemd/system directory
    if not os.path.lexists(service_symlink):
        os.symlink(service_dest, service_symlink)

def _is_service_enabled():
    # Check if the service is already enabled
    result = subprocess.run(['systemctl', 'is-enabled', _VFNET_SERVICE_NAME], capture_output=True, text=True)
    return result.stdout.strip() == 'enabled'

def _disable_service():
    # Check if the service is already enabled
    if _is_service_enabled():
        os.system('systemctl enable {}'.format(_VFNET_SERVICE_NAME))
        return

def _enable_service():
    if _is_service_enabled():
        print("The vfnet-create service is already enabled.")
        return
    
    # Enable the vf-network-create service
    os.system('systemctl enable {}'.format(_VFNET_SERVICE_NAME))

def _set_permissions():
    # Set the execute permissions for the vfup file
    vfup_file = '/etc/vfnet/vfup'
    os.chmod(vfup_file, 0o755)

def _create_symlink():
    # Define the paths for the vfup file and the symlink
    vfup_file = '/etc/vfnet/vfup'
    symlink_path = '/sbin/vfup'

    # Create a symlink in the /sbin directory pointing to the vfup file
    if not os.path.lexists(symlink_path):
        os.symlink(vfup_file, symlink_path)

def install():
    # Step 1: Verify user permissions
    _verify_permissions()

    # Step 2: Create the /etc/vfnet directory if it does not exist
    _create_directory('/etc/vfnet')

    # Step 3: Copy the vfup and vf.config.example files to /etc/vfnet
    _copy_vfnet_files()

    # Step 4: Set execute permissions for the vfup file
    _set_permissions()

    # Step 5: Create a symlink in /sbin to the vfup file
    _create_symlink()

    # Check if installation was successful
    config_dest = '/etc/vfnet/vf.config'
    if os.path.exists(config_dest):
        print("Core installation successful.")
    else:
        print("Core installation failed.")

    # Step 6: Enable the vf-network-create service
    _disable_service()

    # Step 7: Install the vf-network-create service
    _install_service_unit()

    # Step 8: Enable the vf-network-create service
    _enable_service()

    # Check if service was installed successfully
    service_symlink = os.path.join('/etc/systemd/system', _VFNET_SERVICE_FILE_NAME)
    if _is_service_enabled():
            print("Service installation successful.")
    else:
        print("Service installation failed.")



