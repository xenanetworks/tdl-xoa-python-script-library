# XOA Script Documentation - Thor Module and Stream

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
 
* Enter the IP of the chassis in the quotations.
* Enter the desired username. This will appear under the “Owner” column of the GUI.
* Enter the module indices you would like to apply the script.
* Enter the port indices you would like to apply the script.
* Choose the module type and the script will only work with that type.

```python
#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
MODULE_IDXS = [4,8]
PORT_IDXS = [0]

MODULE_TYPE = modules.MThor400G7S1P
# MODULE_TYPE = modules.MThor400G7S1P_b
# MODULE_TYPE = modules.MThor400G7S1P_c
# MODULE_TYPE = modules.MThor400G7S1P_d
```

### Module media configuration

* Enable the module media and port configuration you want to use.

```python
MODULE_MEDIA = enums.MediaConfigurationType.QSFP56_PAM4
PORT_COUNT = 2
PORT_SPEED = 200000
```

### Stream parameters
 
IP/MAC base defines the address range you will increment from. If you change the IP/MAC base, you will change the starting point for incrementing. 

```python
#---------------------------
# STREAM PARAM
#---------------------------

SRC_IPV4 = "10.0.0.2"
SRC_MAC = "AAAAAAAAAA00"
DST_IPV4 = "10.1.0.2"
DST_MAC = "BBBBBBBBBB00"

FRAME_SIZE_BYTES = 128      # frame size including FCS field
STREAM_RATE = 100.0         # this means 100.0%
TRAFFIC_DURATION = 10       # 10 seconds

# ETHERNET HEADER
ETHERNET_TYPE =     "0800"

# IPV4
VERSION = "4"
HEADER_LENGTH = "5"
DSCP_ECN = "00"
TOTAL_LENGTH = '{:04X}'.format(FRAME_SIZE_BYTES - 14 - 4)
IDENTIFICATION = "0000"
FLAGS_OFFSET = "0000"
TTL = "7F"
PROTOCOL = "11"
HEADER_CHECKSUM = "0000"

# PAYLOAD PATTER
PAYLOAD_PATTERN = "FFFF0000"
```

## Run and Verify
Simply `python <script_name.py>` to run the script. You should then see the below in your console. (For Linux and macOS users, use `python3 <script_name.py>`)
```
============================
MODULE MEDIA CONFIG
============================
Reserve module 4
Change module 4 media to QSFP56
Change port config to 2x200G
Reserve module 8
Change module 8 media to QSFP56
Change port config to 2x200G
============================
PORT & STREAM CONFIG
============================
Set port 4/0 to RS-FEC
Create a stream on port 4/0
Stream DMAC:        BBBBBBBBBB00
Stream SMAC:        AAAAAAAAAA00
Stream SRC IPv4:    10.0.0.2
Stream DST IPv4:    10.1.0.2
Stream Rate:        100.0%
Stream Frame Size:  128 bytes
Traffic Duration:   10 seconds
Set port 8/0 to RS-FEC
Create a stream on port 8/0
Stream DMAC:        BBBBBBBBBB00
Stream SMAC:        AAAAAAAAAA00
Stream SRC IPv4:    10.0.0.2
Stream DST IPv4:    10.1.0.2
Stream Rate:        100.0%
Stream Frame Size:  128 bytes
Traffic Duration:   10 seconds
============================
TRAFFIC CONTROL
============================
Clear port 4/0 RX & TX counters
Clear port 8/0 RX & TX counters
Start traffic on port 4/0
Start traffic on port 8/0
Stop traffic on port 4/0
Stop traffic on port 8/0
Read port 4/0 RX & TX counters
============================
TRAFFIC STATS
============================
TX FRAMES:          1794515520
RX FRAMES:          1794515520
TX BYTES:           229697986560
RX BYTES:           229697986560
Read port 8/0 RX & TX counters
============================
TRAFFIC STATS
============================
TX FRAMES:          1706887392
RX FRAMES:          0
TX BYTES:           218481586176
RX BYTES:           0
============================
DONE
============================
```

## Other Documentation
XOA Driver (Python API Reference) Official Documentation
https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/ 


