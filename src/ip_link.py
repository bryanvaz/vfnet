# library to interact with the ip link command

import json
import subprocess

def set_vf_mac_address(pf_device_name: str, vf_index: int, mac_address: str) -> None:
    """
    Sets the MAC address of a virtual function (VF) of a given network device.
    * THIS DOES NOT CHECK IF THE ARGUMENTS ARE VALID.

    Args:
        pf_device_name (str): Name of the parent network device to manage.
        vf_index (int): The zero-index of the VF for which to set the MAC address.
        mac_address (str): The MAC address to set for the VF.
    """
    # set the mac address using ip link at th pf level
    # this will set the mac address for the vf as well
    subprocess.run(["ip", "link", "set", pf_device_name, "vf", str(vf_index), "mac", mac_address])
    
def get_ip_link() -> dict[str,dict]:
    """
    Returns the output of the `ip link` command.

    formatt:
    ```
    'enp1s0f1': {
        'ifindex': 3,
        'ifname': 'enp1s0f1',
        'flags': ['NO-CARRIER', 'BROADCAST', 'MULTICAST', 'UP'],
        'mtu': 1500,
        'qdisc': 'mq',
        'operstate': 'DOWN',
        'linkmode': 'DEFAULT',
        'group': 'default',
        'txqlen': 1000,
        'link_type': 'ether',
        'address': 'd0:23:23:23:45:a8',
        'broadcast': 'ff:ff:ff:ff:ff:ff',
        'vfinfo_list': [
            {
                'vf': 0,
                'link_type': 'ether',
                'address': 'fe:c5:8e:32:23:f0',
                'broadcast': 'ff:ff:ff:ff:ff:ff',
                'vlan_list': [{}],
                'rate': {'max_tx': 0, 'min_tx': 0},
                'spoofchk': True,
                'link_state': 'auto',
                'trust': False,
                'query_rss_en': False
            },
        ]
    }
    ```
    """
    ip_link_output = subprocess.run(["ip", "-j", "link", "show"], capture_output=True, text=True)
    # parse the json output of ip_link_output
    ip_link_json = json.loads(ip_link_output.stdout)
    # convert the json output dictionary of dictionaries
    # to a list of dictionaries

    ip_link_dict = {}
    for link in ip_link_json:
        ip_link_dict[link['ifname']] = link

    # print(f"ip_link_json: {ip_link_dict}")

    return ip_link_dict
