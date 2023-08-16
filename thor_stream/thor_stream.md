# XOA Script Documentation - Thor Module and Stream

## Introduction
What this script example does:
1. Connect to a tester
2. Change the module media type and port speed config on the specified modules
3. Create streams on specified ports on the modules
4. Start & stop traffic on the ports
5. Collect port-level TX & RX counters
6. Free the modules and ports
7. Disconnect from the tester

## How to Use
1. variable `module_port_traffic_config` is where you specify the configuration of modules, ports, and streams
2. function `eth_ipv4_header_generator` is a simple ETH-IPV4 header generator

## Output Example
```
==================================
START
==================================
Connect to chassis: 10.20.1.166
Username:           10.20.1.166
==================================
MODULE MEDIA CONFIG
==================================
Reserve Module 4
Module 4's current media: QSFP56
Module 4's media: no change
Module 4's current port count x speed: [2, 200000, 200000]
Module 4's port count x speed: no change
Reserve Module 8
Module 8's current media: QSFP56
Module 8's media: no change
Module 8's current port count x speed: [2, 200000, 200000]
Module 8's port count x speed: no change
==================================
PORT & STREAM CONFIG
==================================
Set Port 4/0 to RS_FEC
Create a stream on port 4/0
  Index:            0
  DMAC:             00000A010002
  SMAC:             00000A010002
  SRC IPv4:         10.0.0.2
  DST IPv4:         10.1.0.2
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 128 bytes
  Frame Size (max): 128 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          0
Create a stream on port 4/0
  Index:            1
  DMAC:             00000A010003
  SMAC:             00000A010003
  SRC IPv4:         10.0.0.3
  DST IPv4:         10.1.0.3
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 256 bytes
  Frame Size (max): 256 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          1
Set Port 4/1 to RS_FEC
Create a stream on port 4/1
  Index:            0
  DMAC:             00000B010002
  SMAC:             00000B010002
  SRC IPv4:         11.0.0.2
  DST IPv4:         11.1.0.2
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 128 bytes
  Frame Size (max): 128 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          2
Create a stream on port 4/1
  Index:            1
  DMAC:             00000B010003
  SMAC:             00000B010003
  SRC IPv4:         11.0.0.3
  DST IPv4:         11.1.0.3
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 256 bytes
  Frame Size (max): 256 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          3
Create a stream on port 4/1
  Index:            2
  DMAC:             00000B010004
  SMAC:             00000B010004
  SRC IPv4:         11.0.0.4
  DST IPv4:         11.1.0.4
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 512 bytes
  Frame Size (max): 512 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          4
Set Port 8/0 to RS_FEC
Create a stream on port 8/0
  Index:            0
  DMAC:             00000A010002
  SMAC:             00000A010002
  SRC IPv4:         10.0.0.2
  DST IPv4:         10.1.0.2
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 128 bytes
  Frame Size (max): 128 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          5
Create a stream on port 8/0
  Index:            1
  DMAC:             00000A010003
  SMAC:             00000A010003
  SRC IPv4:         10.0.0.3
  DST IPv4:         10.1.0.3
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 256 bytes
  Frame Size (max): 256 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          6
Set Port 8/1 to RS_FEC
Create a stream on port 8/1
  Index:            0
  DMAC:             00000B010002
  SMAC:             00000B010002
  SRC IPv4:         11.0.0.2
  DST IPv4:         11.1.0.2
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 128 bytes
  Frame Size (max): 128 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          7
Create a stream on port 8/1
  Index:            1
  DMAC:             00000B010003
  SMAC:             00000B010003
  SRC IPv4:         11.0.0.3
  DST IPv4:         11.1.0.3
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 256 bytes
  Frame Size (max): 256 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          8
Create a stream on port 8/1
  Index:            2
  DMAC:             00000B010004
  SMAC:             00000B010004
  SRC IPv4:         11.0.0.4
  DST IPv4:         11.1.0.4
  Rate:             10.0%
  Frame Size Type:  FIXED bytes
  Frame Size (min): 512 bytes
  Frame Size (max): 512 bytes
  Payload Pattern:  FFFF0000
  TPLD ID:          9
==================================
TRAFFIC CONTROL
==================================
Clear port 4/0 RX & TX counters
Clear port 4/1 RX & TX counters
Clear port 8/0 RX & TX counters
Clear port 8/1 RX & TX counters
Traffic duration: 10 seconds
Start traffic on Port 4/0
Start traffic on Port 4/1
Start traffic on Port 8/0
Start traffic on Port 8/1
Stop traffic on Port 4/0
Stop traffic on Port 4/1
Stop traffic on Port 8/0
Stop traffic on Port 8/1
Cooling down: 2 seconds
Read port 4/0 RX & TX counters
==================================
TRAFFIC STATS
==================================
TX FRAMES:          308063469
RX FRAMES:          308063469
TX BYTES:           53196134912
RX BYTES:           53196134912
Read port 4/1 RX & TX counters
==================================
TRAFFIC STATS
==================================
TX FRAMES:          345297338
RX FRAMES:          345297338
TX BYTES:           77590128256
RX BYTES:           77590128256
Read port 8/0 RX & TX counters
==================================
TRAFFIC STATS
==================================
TX FRAMES:          276576368
RX FRAMES:          307735552
TX BYTES:           47758969344
RX BYTES:           69149797248
Read port 8/1 RX & TX counters
==================================
TRAFFIC STATS
==================================
TX FRAMES:          307735552
RX FRAMES:          276576368
TX BYTES:           69149797248
RX BYTES:           47758969344
==================================
DONE
==================================
```


## Other Documentation
XOA Driver (Python API Reference) Official Documentation
https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/ 


