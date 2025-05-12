# TDL XOA Python Script Example Library

> [!IMPORTANT]  
> ``xoa-driver`` package has been discontinued and is replaced by ``tdl-xoa-driver``. 
> Please ``pip uninstall  xoa-driver`` from your environment and ``pip install tdl-xoa-driver``. The functions and imports remain the same so you don't need to change your script souce code.

## Introduction

This repository includes examples of using [tdl-xoa-driver](https://pypi.org/project/tdl-xoa-driver/)

Read [TDL XOA Driver User Doc](https://docs.xenanetworks.com/projects/tdl-xoa-driver/)

### Python Requirement

**Python>=3.11**

### What Example Folder Contains

Each folder contains at least three files:

* Python3 script file - this is where the example code locates
* requirements.txt - dependencies to run the code. You should `pip install -r requirements.txt` (for Windows) or `pip3 install -r requirements.txt` (for Linux/macOS) to update your Python3 environment (either global or virtual) to have the necessary dependencies.

## Script Descriptions

### Quick Start

* [Quick Start](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/quick_start): Basics for you to get started. 

---

### Async Wrapper for Non-Async Python

* [async_wrapper](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/async_wrapper): The APIs provided by tdl-xoa-driver are **async** functions. This means any function that uses the tdl-xoa-driver must be declared as **async**. This might be a problem for you if your existing framework doesn't support async functions. To solve this "incompatibility" issue, we have made an async wrapper class **XenaAsyncWrapper** for you to wrap tdl-xoa-driver's async function inside and use it as a regular Python function.

  **With XenaAsyncWrapper, you can develop your own Robot Framework library using APIs from the tdl-xoa-driver**.

---

### Port Configuration and CLI

* [xpc_cli_integration](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/xpc_cli_integration): XenaManager's port configuration (.xpc) and CLI integration with XOA Python API. Demonstrates How to load ``.xpc`` file or send CLI commands via XOA Python API.

### CLI Python3 Wrapper
* [cli_py3_wrapper](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/cli_py3_wrapper): CLI wrapper for **Python>=3.11** and a script example.
* [cli_wrappers](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/cli_wrappers): different language wrapper for CLI commands, e.g. Java, Tcl, Perl, etc.

---

### Robot Framework Library Example

* [robot_framework](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/robot_framework): You can develop your own Robot Framework library using APIs from tdl-xoa-driver to communicate with the test equipment. In this example, we are **demonstrating How you can use tdl-xoa-driver and XenaAsyncWrapper to develop a simple library for Robot**.

---

### Automated Test Suite

* [rfc_tests](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/rfc_tests): How to run Xena2544/Xena2889/Xena3918 configuration using XOA Python for GUI-less test suite automation.
* [anlt_test_methodology](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/anlt_test_methodology): Auto-negotiation and link training test methodology.
* [cable_perf_optimization](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/cpom): Provides an automated optimization framework that uses PRBS-based BER testing to dial in RX Output Equalization and TX Input Equalization for the best possible signal integrity, aligning with IEEE 802.3ck and CMIS standards.

---

### Various Statistics

* [collect_live_statistics](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/collect_live_statistics): How to query real-time statistics in different async task.
* [fec_error_dist_plot](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/fec_error_dist_plot): Query FEC error counters and generate FEC error distribution plot.
* [fec_stats_csv](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/fec_stats_csv): Query FEC error counters and save the data in csv file.
* [l1_bit_rate](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/l1_bit_rate): How to convert traffic L2 bit rate into L1 bit rate.
* [prbs_ber_stats](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/prbs_ber_stats): How to start PRBS and read PRBS BER statistics.
* [signal_integrity_hist_plot](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/signal_integrity_hist_plot): How to read signal integrity view on Z800 Freya port and plot the values in histograms.

---

### Port and Stream Configuration

* [modifier](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/modifier): How to add modifiers on a stream.
* [filter](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/filter): How to add filters on a port.
* [freya_tx_tap_tuning](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/freya_tx_tap_tuning): Set and get the port TX taps in three different format, applicable to Z800 Freya only.
* [header_builder](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/header_builder): Use the headers module to build packet headers.
* [ip_streams_arp_ndp_table](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/ip_streams_arp_ndp_table): Configure port's ARP/NDP table based on the IP streams configured on it.
* [simple_arp](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/simple_arp): Simple ARP example to resolve the MAC address of a port.
* [pcap_replay_capture](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/pcap_replay_capture): How to replay frames from a pcap and capture traffic into another pcap file.
* [thor_ppm_anlt_stream](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/thor_ppm_anlt_stream): Demonstrates How to change media configuration, perform PPM sweep and AN&LT on Thor modules.
* [stream_sync](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/stream_sync): How to synchronize the streams on a port to the script client cache.
* [chassis_uptime](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/chassis_uptime): Read system uptime.

---

### Schedule Traffic based on ToD
* [gps_tod](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/gps_tod): Schedule traffic based on Time of Day (ToD).

---

### PFC Configuration
* [pfc](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/pfc): Create a PFC stream on the port to suppress a specific traffic class of the TX port traffic to a target fraction of the port speed.

---

### DHCP Server & Client IPv4 
* [dhcp_server_dhcp_client](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/dhcp_server_dhcp_client): This project contains two main scripts dhcp_client_main.py and dhcp_server_main.py. As their name indicates, they leverage tdl-xoa-driver to run DHCP server and client services over Teledyne Lecroy Xena's testers.

---

### Emulate Various Scenarios
* [dhcp_stream](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/dhcp_stream): How to create a DHCP stream
* [ip_fragmented](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/ip_fragmented): Emulate IP fragmentation.
* [tcp_handshake](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/tcp_handshake): How to emulate a TCP 3-way handshake.
* [oran_dos](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/oran_dos): DoS attack emulation for ORAN.
* [rocev2](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/rocev2): Emulate RoCEv2 flow for AI performance test.

---

### Transceiver Access
* [thor_xcvr_seq_access](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/thor_xcvr_seq_access): Transceiver sequential access on Z400 Thor module.
* [xcvr_access](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/xcvr_access): Transceiver read and write access.

---

### Misc.
* [port_capabilities](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/port_capabilities): Read port capabilities to understand what a port can do.
* [low_level_api](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/low_level_api): How to use XOA's Low-Level API
* [push_notification](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/push_notification): How to utilize push notification.
* [exception_handling](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/exception_handling): How to handle bad status response from chassis server.
* [chimera_automation](https://github.com/xenanetworks/tdl-xoa-python-script-library/tree/main/chimera_automation): uses Chimera core ([chimera-core](https://pypi.org/project/chimera-core/)) for impairment automation.