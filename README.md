# vfnet ![nvm version](https://img.shields.io/badge/version-v0.1.0-blue.svg)

vfnet is a command-line tool for managing virtual functions (VFs) on network devices in Linux. It provides functionalities to list network devices, set the number of VFs for specific network devices, and persist the number of VFs across reboots. This allows you to use your network card as a hardware switch for your virtual machines and containers.

Most virtualization and container systems use software emulated network devices to provide network connectivity to VMs. This limits the network speed of the VM to the quality of the emulation and the power of your CPU. Currently, on modern CPUs (~AMD Zen 3 or Intel 12th Gen) the maximum theoretical speed is ~25Gbps (macvlan, macvtap or OVS). Using VFs allow you to offload all network functions from your CPU to a network card and achieve the same performance as if you had used PCI passthrough to give the VM complete access to your network card. Using a Mellanox ConnectX-3 dual-port 40G card, a $30 USD, 10 year-old card is able to create 7 VFs per 40G port and each VF is capable of saturating the 40G link. The only downside is that your BIOS needs to support SR-IOV, and your network device needs to support VFIO; most modern systems do have this support, but you can check the compatibility list below if unsure.

## Features

- Listing network device information
- Setting the number of VFs for specific network devices
- Persisting the number of VFs for network devices across reboots

## Quickstart

You can use the `vfnet` command-line tool to manage virtual functions on network devices. Here are some examples of how to use `vfnet`:

- List network devices and their information:
  ```
  ./vfnet
  ```
  
- Create 4 VFs for a specific network device:
  ```
  ./vfnet set eth0 4
  ```

- List network devices again to see new VFs and their information: 
  ```
  ./vfnet
  ```

- Attach the new VF network devices to your VMs

If you install vfnet on your system, you can persist your vf configuration across reboots. Without this persistance, all VFs and their configurations will be lost on reboot

- Install vfnet into $PATH and install boot-time service
  ```
  ./vfnet install
  ```

- Persist the current configuration of VFs for all devices
  ```
  vfnet persist
  ```

- Persist a specific number of VFs for a specific network device:
  ```
  vfnet persist eth0 4
  ```

Calling `vfnet persist` will not change the current VF configuration until a reboot; conversely `vfnet set` will change the VF configuration, but will not persist the configuration across reboots.

For more detailed information on the usage and command options, please run `vfnet -h [COMMAND]`

**Notes:**
* _Currently VFs are created with a random MAC every time._
* _VFs do not automatically activate their links on boot as it is assumed you are going to use them to pass-through to a VM. To give your VM high-speed connectivity to the host, you can configure one of the VFs to come up on boot with the stock Linux network stack, just like any other network interface. VFs boot-time creation service is configured to enable VFs before the Linux network stack attempts to raise network interfaces._

## Usage

### Enable VFIO in the linux kernel

If you have not done so already, you will have to modify the bootloader to pass the following kernel options on boot:
```
amd_iommu=on intel_iommu=on iommu=pt
```

This can be confirmed by running `cat /proc/cmdline`

### Listing PFs and VFs

You should always start by listing your hardware using `vfnet` (aliased to `vfnet list`) without any arguments. The tool will output a list of physical functions (PF) which are usually synonymous with ports on your network card.

```
bryan@vfio-bench[~]$ vfnet
------ Detecting network devices... ------
 - Detection Complete.
 - 2 physical NICs detected.
 - 4 VF network devices detected.

PF Network Devices:
PCI BDF        Interface   Subsystem   Description                     Driver   Can VF?   Active VFs   Config VFs   IOMMU Grp   Device Path
=============  ==========  ==========  ==============================  =======  ========  ===========  ===========  ==========  ========================
0000:01:00.0   enp1s0f0    pci         Ethernet Controller 10G X550T   ixgbe    Yes       4/63         4/63         15          /sys/class/net/enp1s0f0
0000:01:00.1   enp1s0f1    pci         Ethernet Controller 10G X550T   ixgbe    Yes       0/63         N/A          16          /sys/class/net/enp1s0f1

VF Network Devices:
PCI BDF        Interface    Parent     Parent BDF     Device Path
=============  ===========  =========  =============  ==========================
0000:02:10.0   enp1s0f0v0   enp1s0f0   0000:01:00.0   /sys/class/net/enp1s0f0v0
0000:02:10.2   enp1s0f0v1   enp1s0f0   0000:01:00.0   /sys/class/net/enp1s0f0v1
0000:02:10.4   enp1s0f0v2   enp1s0f0   0000:01:00.0   /sys/class/net/enp1s0f0v2
0000:02:10.6   enp1s0f0v3   enp1s0f0   0000:01:00.0   /sys/class/net/enp1s0f0v3
```

Columns:
* PF Network Devices:
  * PCI BDF: This is the PCI address of the device. This is the address you will use to pass the device through to a VM.
  * Interface: This is the name of the interface as it appears in the Linux network stack.
  * Subsystem: This is the subsystem name of the device. (For informational purposes, current vfnet filters out any nic that does not have a subsystem name of "pci")
  * Description: This is the description of the device as reported by the kernel. Usually this is the name of the device as reported by the manufacturer.
  * Driver: This is the driver that is currently bound to the device.
  * Can VF?: This is a boolean value that indicates whether or not the device supports VFs based on `vfnet`'s detection results.
  * Active VFs: This is the number of VFs that are currently configured for the device out of the max capable VFs.
  * Config VFs: This is the number of VFs that are configured to be created on boot. If `N/A` is shown, then the PF has no VF configuration yet for boot time.
  * IOMMU Grp: This is the IOMMU group that the device is in. This is useful for determining which devices can be passed through to a VM together.
  * Device Path: This is the path to the device in sysfs. This is useful for debugging purposes.
* VF Network Devices:
  * Parent: This is the parent device of the VF.
  * Parent BDF: This is the PCI address of the parent device.

### Creating VFs

To create VFs, you can use the `vfnet set` command. This command takes a single PF interface name, and the number of VFs you want to create for that PF. For example, to create 4 VFs for the PF `enp1s0f0` you would run:
``` 
vfnet set enp1s0f0 4
```
**WARNING:** If the device already has VFs configured, this command will delete all existing VFs and create the new number of VFs specified. This is because the Linux network stack does not support dynamically changing the number of VFs on a PF.


## Compatibility

The following hardware has been tested for VF support. If you have a working system that is not on the list below, please consider opening a PR to add the additional hardware to this list, and attach a few screens showing the VFs configured.

**Network Cards**

* Mellanox CX-3 and CX-3 Pro series (@bryanvaz)
* Intel X550 series controllers (@bryanvaz)
* Intel X700 and XL700 series controllers - (confirmed by Intel research papers, however do not have first hand test results to confirm stack compatibility)

**Motherboards**

* ASRock Rack X470DU4(-T2) (@bryanvaz)

**Operating System**

* Most Debian-based distros
* TrueNAS 22.12 or greater

**Known Issues**
* Certain consumer and business prebuilds do not support a portion of the Resizable BAR(ReBAR) spec at the BIOS level that is required by Linux to create VFs. As a result, even though the BIOS states explicit support for SR-IOV and VT-d, the NIC supports VFIO, and Linux reports VF support, when you try to create a VF, the system will report an error in changing the BAR space.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please submit an issue or a pull request. Make sure to follow the [contribution guidelines](CONTRIBUTING.md) when contributing to this project.

## License

vfnet is released under the [GNU Lesser General Public License v3.0](COPYING.LESSER) (LGPLv3). See the [LICENSE](COPYING.LESSER) file for more details.

## Author

Created by Bryan Vaz.

&copy; 2023 Bryan Vaz. All rights reserved.
