# XOA Script Documentation - XPC Integration

In ValkyrieManager, port configurations are saved into files with extension **.xpc** in the same command format as used by [XOA CLI](https://docs.xenanetworks.com/projects/xoa-cli/). This makes it very easy to go back and forth between a ValkyrieManager environment and a XOA CLI environment. For example, exporting a port configuration from ValkyrieCLIManager generates a configuration file in a simple text format that can be edited using a text editing tool such as Microsoft Notepad. It can then be imported back into ValkyrieManager.

## Introduction
What this script example does:
1. Connect to a tester
2. Reserve port
3. Load a .xpc file to the port
