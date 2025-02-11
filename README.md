# Xena OpenAutomation Script Example Library

## Introduction

This repository includes examples of using [XOA Python API](https://docs.xenanetworks.com/projects/xoa-python-api), aka. [xoa-driver](https://pypi.org/project/xoa-driver/)

## Script Description

### Quick Start

* [Quick Start](https://github.com/xenanetworks/open-automation-script-library/tree/main/quick_start): basics for you get started. 

---

### Async Wrapper for Non-Async Python

* [async_wrapper](https://github.com/xenanetworks/open-automation-script-library/tree/main/async_wrapper): The APIs provided by xoa-driver are **async** functions. This means any function that uses the xoa-driver must be declared as **async**. This might be a problem for you if your existing framework doesn't support async functions. To solve this "incompatibility" issue, we have made an async wrapper class **XenaAsyncWrapper** for you to wrap xoa-driver's async function inside and use it as a regular Python function.

  **With XenaAsyncWrapper, you can develop your own Robot Framework library using APIs from the xoa-driver**.

---

### Robot Framework Library Example

* [robot_framework](https://github.com/xenanetworks/open-automation-script-library/tree/main/robot_framework): You can develop your own Robot Framework library using APIs from xoa-driver to communicate with the test equipment. In this example, we are **demonstrating how you can use xoa-driver and XenaAsyncWrapper to develop a simple library for Robot**.

---

### Automated Test Suite

* [rfc_tests](https://github.com/xenanetworks/open-automation-script-library/tree/main/rfc_tests): how to run Xena2544/Xena2889/Xena3918 configuration using XOA Python for GUI-less test suite automation.
* [anlt_test_methodology](https://github.com/xenanetworks/open-automation-script-library/tree/main/anlt_test_methodology): auto-negotiation and link training test methodology.
* [cable_perf_optimization](https://github.com/xenanetworks/open-automation-script-library/tree/main/cable_perf_optimization): measures PRBS BER while adjusting transceiver cursor values.
* [chimera_automation](https://github.com/xenanetworks/open-automation-script-library/tree/main/chimera_automation): uses Chimera core ([chimera-core](https://pypi.org/project/chimera-core/)) for impairment automation.

---

### Port Configuration and CLI

* [xpc_cli_integration](https://github.com/xenanetworks/open-automation-script-library/tree/main/xpc_cli_integration): XenaManager's port configuration (.xpc) and CLI integration with XOA Python API. Demonstrates how to load ``.xpc`` file or send CLI commands via XOA Python API.
* [cli_wrappers](https://github.com/xenanetworks/open-automation-script-library/tree/main/cli_wrappers): different language wrapper for CLI commands, e.g. Java, Tcl, Perl, etc.

---

### Various Statistics

* [collect_live_statistics](https://github.com/xenanetworks/open-automation-script-library/tree/main/collect_live_statistics): how to query real-time statistics in different async task.
* [fec_error_dist_plot](https://github.com/xenanetworks/open-automation-script-library/tree/main/fec_error_dist_plot): query FEC error counters and generate FEC error distribution plot.
* [fec_stats_csv](https://github.com/xenanetworks/open-automation-script-library/tree/main/fec_stats_csv): query FEC error counters and save the data in csv file.
* [l1_bit_rate](https://github.com/xenanetworks/open-automation-script-library/tree/main/l1_bit_rate): how to convert traffic L2 bit rate into L1 bit rate.
* [prbs_ber_stats](https://github.com/xenanetworks/open-automation-script-library/tree/main/prbs_ber_stats): how to start PRBS and read PRBS BER statistics.
* [signal_integrity_hist_plot](https://github.com/xenanetworks/open-automation-script-library/tree/main/signal_integrity_hist_plot): how to read signal integrity view on Z800 Freya port and plot the values in histograms.

---

### Port and Stream Configuration

* [modifier](https://github.com/xenanetworks/open-automation-script-library/tree/main/modifier): how to add modifiers on a stream.
* [filter](https://github.com/xenanetworks/open-automation-script-library/tree/main/filter): how to add filters on a port.
* [freya_tx_tap_tuning](https://github.com/xenanetworks/open-automation-script-library/tree/main/freya_tx_tap_tuning): set and get the port TX taps in three different format, applicable to Z800 Freya only.
* [header_builder](https://github.com/xenanetworks/open-automation-script-library/tree/main/header_builder): use the headers module to build packet headers.
* [ip_streams_arp_ndp_table](https://github.com/xenanetworks/open-automation-script-library/tree/main/ip_streams_arp_ndp_table): configure port's ARP/NDP table based on the IP streams configured on it.
* [simple_arp](https://github.com/xenanetworks/open-automation-script-library/tree/main/simple_arp): simple ARP example to resolve the MAC address of a port.
* [pcap_replay_capture](https://github.com/xenanetworks/open-automation-script-library/tree/main/pcap_replay_capture): how to replay frames from a pcap and capture traffic into another pcap file.
* [thor_ppm_anlt_stream](https://github.com/xenanetworks/open-automation-script-library/tree/main/thor_ppm_anlt_stream): demonstrates how to change media configuration, perform PPM sweep and AN&LT on Thor modules.
* [stream_sync](https://github.com/xenanetworks/open-automation-script-library/tree/main/stream_sync): how to synchronize the streams on a port to the script client cache.
* [chassis_uptime](https://github.com/xenanetworks/open-automation-script-library/tree/main/chassis_uptime): read system uptime.

---

### Schedule Traffic based on ToD
* [gps_tod](https://github.com/xenanetworks/open-automation-script-library/tree/main/gps_tod): schedule traffic based on Time of Day (ToD).

---

### PFC Configuration
* [pfc](https://github.com/xenanetworks/open-automation-script-library/tree/main/pfc): create a PFC stream on the port to suppress a specific traffic class of the TX port traffic to a target fraction of the port speed.

---

### Emulate Various Scenarios
* [dhcp](https://github.com/xenanetworks/open-automation-script-library/tree/main/dhcp): how to create a DHCP stream
* [ip_fragmented](https://github.com/xenanetworks/open-automation-script-library/tree/main/ip_fragmented): emulate IP fragmentation.
* [tcp_handshake](https://github.com/xenanetworks/open-automation-script-library/tree/main/tcp_handshake): how to emulate a TCP 3-way handshake.
* [oran_dos](https://github.com/xenanetworks/open-automation-script-library/tree/main/oran_dos): DoS attack emulation for ORAN.
* [rocev2](https://github.com/xenanetworks/open-automation-script-library/tree/main/rocev2): emulate RoCEv2 flow for AI performance test.

---

### Transceiver Access
* [thor_xcvr_seq_access](https://github.com/xenanetworks/open-automation-script-library/tree/main/thor_xcvr_seq_access): transceiver sequential access on Z400 Thor module.
* [xcvr_access](https://github.com/xenanetworks/open-automation-script-library/tree/main/xcvr_access): transceiver read and write access.

---

### Misc.
* [port_capabilities](https://github.com/xenanetworks/open-automation-script-library/tree/main/port_capabilities): read port capabilities to understand what a port can do.
* [low_level_api](https://github.com/xenanetworks/open-automation-script-library/tree/main/low_level_api): how to use XOA's Low-Level API
* [push_notification](https://github.com/xenanetworks/open-automation-script-library/tree/main/push_notification): how to utilize push notification.
* [exception_handling](https://github.com/xenanetworks/open-automation-script-library/tree/main/exception_handling): how to handle bad status response from chassis server.

## What Example Folder Contains

Each folder contains at least three files:

* Python script file - this is where the example code locates
* requirements.txt - dependencies to run the code. You should `pip install -r requirements.txt` to update your Python environment (either global or virtual) to have the necessary dependencies.

## Installing XOA Driver

This section details how to install `xoa-driver`. Installation is necessary to execute scripts that use XOA Python API.

Before installing `xoa-driver`, please make sure your environment has installed `python>=3.10` and `pip`.

You can install the `xoa-driver` to your global or virtual environment for Windows, macOS, and Linux using the commands below. 
```
pip install xoa-driver -U            # latest version
```

Once the `xoa-driver` is installed, you can execute your script.

For the most detailed instructions on how to install the XOA driver, visit our **Getting Started** section of our official XOA documentation here: https://docs.xenanetworks.com/projects/xoa-python-api/en/latest/getting_started/installation.html