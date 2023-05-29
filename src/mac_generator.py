# Deterministicly and securely generates the MAC address for a vf of a given device

# Not needed right now as it looks as though most drivers deterministically generate the MAC address

import bcrypt
import hashlib
import base64

def generate_mac(pf_mac_address: str, vf_index: int, pf_devcie_name: str) -> str:
    """
    Generates a deterministic and secure MAC address for a VF of a given device.

    Args:
        pf_mac_address (str): The MAC address of the physical function (PF) of the device.
        vf_index (int): The zero-index of the virtual function (VF) for which to generate the MAC address.
        pf_devcie_name (str): The name of the device.

    Returns:
        str: The generated MAC address in the format "xx:xx:xx:xx:xx:xx".
    """
    
    # Calculate deterministic salt based on device name
    salt = base64.urlsafe_b64encode(hashlib.sha256(pf_devcie_name.encode()).digest()).decode()[:23].replace('-', 'a').replace('_', 'b')
    salt_str = '$2b${}${}'.format("12",salt)
    # calculate bcrypted mac address
    vf_mac_bcrypted = bcrypt.hashpw(f"${pf_mac_address}v{vf_index}".encode(), salt_str.encode()).decode()
    # calc the sha256 of the bcrypted mac address and show it in hex
    vf_mac = (hashlib.sha256(vf_mac_bcrypted.encode()).hexdigest())[:12]
    
    # Force to LAA Unicast MAC Address
    vf_mac_bytes = bytes.fromhex(vf_mac)
    vf_mac_bytes = bytearray(vf_mac_bytes)
    vf_mac_bytes[0] = (vf_mac_bytes[0] | 0b00000010) & 0b11111110
    vf_mac_laa = vf_mac_bytes.hex()
    vf_mac_formatted = ':'.join([vf_mac_laa[i:i+2] for i in range(0, len(vf_mac_laa), 2)])

    return vf_mac_formatted