# XOA Script Documentation - IP Stream Pairs & ARP Table 

## Introduction
This document explains which commands can be edited to alter the configuration as desired. 

### What’s Included

* How to install XOA drivers
* Connect to Chassis IP & Specify which module/Ports to configure.
* Choose which IP address to increment up from.
* Specify how many IP addresses you would like to create.
* Configure Packet Content (# of bytes, PPS, packet limit)

## Installing XOA Driver

This section details how to install XOA drivers. Installation is necessary to execute XOA commands.
Before installing XOA Python API, please make sure your environment has installed `Python >=3.8` and `PIP`.

### Installing Python

XOA Python API requires that you install Python on your system.
There are three installation methods on Windows: The Microsoft Store, The full installer, Or Windows Subsystem for Linux

### Installing PIP
The minimum Python version required for XOA is Python >=3.8.

If `PIP` is not installed for some reason, visit the link below for further instructions on how to install PIP:
https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/getting_started/installation.html

### Installing XOA Driver
For the most detailed instructions on how to install the XOA driver, visit our **Getting Started** section of our official XOA documentation here: https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/getting_started/installation.html

You can install the XOA driver to your Global Namespace for Windows, macOS, and Linux using the commands below. We suggest the first one to receive the latest version. 
```
pip install xoa-driver            # latest version
```

Once the XOA driver is installed, you can execute your script.

> Please note that the scripts requires xoa-driver >= 2.0.1. To verify your xoa-driver version, use `pip show xoa-driver`

## Basic Configuration
This section details the commands that are necessary for you to specify. This section will include the commands of most interest like “Port IP base”, “IP Count”, “Frame Size Bytes”, etc.

### Connecting to the Chassis/Module/Ports
 
* Line 19: Enter the IP of the chassis in the quotations.
* Line 20: Enter the desired username. This will appear under the “Owner” column of the GUI.
* Line 21: Enter the module number you would like to apply the script to as it appears in the GUI.
* Line 22: Enter the first port number you would like to apply the script to as it appears in the GUI. This will correspond to ARP list “a”, MAC list “a”, IP/MAC base “a”, and all modifiers applied for port “a.”
* Line 23: Enter the second port number you would like to apply the script to as it appears in the GUI. This will correspond to ARP list “b”, MAC list “b”, IP/MAC base “b”, and all modifiers applied for port “b.”

```python
#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
MODULE_INDEX = 0
PORT_INDEX_A = 0
PORT_INDEX_B = 4
```

### Base IP/MAC address
 
IP/MAC base defines the address range you will increment from. If you change the IP/MAC base, you will change the starting point for incrementing. 

```python
#---------------------------
# STREAM ADDR
#---------------------------
PORT_A_IP_BASE = "10.0.0.2"
PORT_A_MAC_BASE = "AAAAAAAAAA00"
PORT_B_IP_BASE = "10.1.0.2"
PORT_B_MAC_BASE = "BBBBBBBBBB00"
```

### IP Count/Packet Content
 
* Line 36: The number entered in this line will determine how many IP addresses will be created. “1500” results in 1500 IP addresses.
* Line 37: Specifies the number of bytes for each frame. It includes the Ethernet FCS field.
* Line 38: Specifies the packets per second for the streams.
* Line 39: Specifies the limit for how many packets will be transmitted.

```python
#---------------------------
# STREAM PROPERTIES
#---------------------------
IP_PAIRS = 1500
FRAME_SIZE_BYTES = 128
STREAM_PPS = 100
TX_PKT_LIMIT = 1000
```

### Protocol Segments 
This section displays where you can configure your IP/UDP/TCP header.

Please note that to correctly configure the protocol segments, the script first describes the protocols (skeleton) as shown between Line 180-184:
```python
    stream_a.packet.header.protocol.set(segments=[
        enums.ProtocolOption.ETHERNET,
        enums.ProtocolOption.IP,
        enums.ProtocolOption.TCP
        ]),
```
and then write the content of the header as in Line 185.
```python
stream_a.packet.header.data.set(hex_data=Hex(HEADER)),
```

#### IPV4 Header
 
Lines 48-56 are fields of the IPV4 Header. Each of these fields can be configured as desired.

```python
# IPV4
VERSION = "4"
HEADER_LENGTH = "5"
DSCP_ECN = "00"
TOTAL_LENGTH = '{:04X}'.format(FRAME_SIZE_BYTES - 14 - 4)
IDENTIFICATION = "0000"
FLAGS_OFFSET = "0000"
TTL = "7F"
PROTOCOL = "06"
HEADER_CHECKSUM = "0000"
```

#### TCP/UDP Header
 
Lines 59-66 (59-62) are fields of the TCP (UDP) header. Each of these fields can be configured as desired. 

```python
# TCP
TCP_SRC_PORT = "0000"
TCP_DEST_PORT = "0000"
TCP_SEQ = "00000000"
TCP_ACK = "00000000"
TCP_DF = "5000"
TCP_WIN_SIZE = "0000"
TCP_CHK = "0000"
TCP_URGENT = "0000"
```

```python
# UDP
UDP_SRC_PORT = "0000"
UDP_DEST_PORT = "0000"
UDP_LEN = FRAME_SIZE_BYTES - 14 - 20 - 4
UDP_CHK = "0000"
```

### Modifiers
The two scripts use 16-bit modifiers to emulate 1500 IP pairs. The MAC addresses, IP addresses and TCP/UDP source/destination port numbers increment in a synchronized fashion.

For example, Line 198-200. This code snippet obtains a modifier object, places it at packet header position 4 (the lowest two bytes of DMAC), increments the value, from 0 to IP_PAIRS-1 in steps of 1.
```python
    # Modifier on DMAC lowest two bytes (pos=4), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. BB:BB:BB:BB:00:00, BB:BB:BB:BB:00:01 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(0)
    await modifier_dmac.specification.set(position=4, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=IP_PAIRS-1)
```

The other modifier code snippets work in the same way: placing a modifier at a position of the packet header, increment the value from min to min in step of 1.

### Run and Verify
Simply `python <script_name.py>` to run the script. You should then see the below in your console. (For Linux and macOS users, use `python3 <script_name.py>`)
```
Making 1500 TCP stream pairs
Reset Port A
Configure Port A
Configure TCP streams A to B
Reset Port B
Configure Port B
Configure TCP streams B to A
Done
```

Then you can use ValkyrieManager to verify the stream by:
1. Reserve the ports
2. Right-click on the stream
3. Select Preview Stream
4. Wait for Wireshark to open a PCAP file containing the packets generated by the stream.

To verify the ARP table:
1. Reserve the ports
2. Click on a port
3. Go to the panel on the right:
   Resource Properties > Main Port Config > IPv4/IPv6 Properties > ARP/NDP Address Table > ARP Table: Edit ARP Table

## Other Documentation
XOA Driver (Python API Reference) Official Documentation
https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/ 


