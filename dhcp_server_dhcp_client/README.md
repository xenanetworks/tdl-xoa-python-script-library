# DHCP IPv4 Script Using XOA Python API

This project contains two main scripts ``dhcp_client_main.py`` and ``dhcp_server_main.py``. As their name indicates, they leverage ``tdl-xoa-driver`` to run DHCP server and client services over Teledyne Lecroy Xena's products.

## Quick Start

### Installing requirements
```sh
pip install -r requirements.txt
```

### Run DHCP Server
* First, you need to configure on which chassis, module and port you want to run the DHCP server. To configure that locate the following global variables from the ``dhcp_server_main.py`` file and change them based on your needs.

```python
global_chassis_addr = "10.20.1.252"
global_chassis_pass = "xena"
global_hostname     = "xena-dhcp-server"
global_module_id    = 2
global_port_id      = 4
```
* Then you need to configure the DHCP itself. To achieve it, locate the ``dhcp_config`` function and change the following parameters based on your scenario.

```python
configuration = DHCPServerConfiguration()
configuration.debug = print
configuration.network = '192.168.0.0'
configuration.broadcast_address = '192.168.255.255'
configuration.subnet_mask = '255.255.0.0'
configuration.server_identifier = "192.168.10.1"
configuration.ip_address_lease_time = 600
# configuration.router = ["192.168.0.1"]
# configuration.domain_name_server = ["8.8.8.8", "4.2.2.4"]
```

### Run DHCP Client
* First, you need to configure on which chassis, module, and port you want to run the DHCP client process. To configure that locate the following global variables from the ``dhcp_client_main.py`` file and change them based on your needs.

```python
global_chassis_addr = "10.20.1.252"
global_chassis_pass = "xena"
global_hostname     = "xena-dhcp-client"
global_module_id    = 2
global_port_id      = 5
```

* Then look for ``get_dhcp_addresses("04:F4:BF:00:00:00", 100, 3, 3000)`` function and configure it based on your scenario. This function takes four arguments.
1. Base MAC address: For each request, it uses the first 3 bytes of the MAC address as the base(fixed) part and generates the last 3 bytes randomly.
2. Number of Requests: The number of DHCP requests that will be sent to the DHCP server.
3. Number of retries: For each request, how many times it should retry if no response comes from the server before the timeout happens.
4. Timeout: How much in milliseconds it should wait for a response to consider it a failure.


At the end, this function returns: four parameters Error code, Dictionary of [MAC Address, DhcpSession], Number of Success, Number of Failure
For instance, the following code is an easy example that uses 04:F4:BF as the base MAC address to generate 100 DHCP requests to acquire 100 IP addresses.\
For each request, there is a corresponding DhcpSession which contains the DHCP information including the obtained IP address, Broadcast address, Netmask address, Router address and lease timeout.  

```python
dhcp_handler = DhcpClient(chassis_handler=chassis_1_handler, module_id=global_module_id, port_id=global_port_id)
ret_error, address_dict, num_success, num_faliure = await dhcp_handler.get_dhcp_addresses("04:F4:BF:00:00:00", 100, 3, 3000)
if ret_error == DhcpClient.Error.Success:
    print("The DHCP process ran Successfully")
    print(f"Number of Success: {num_success}, Number of Failure: {num_faliure}")
else:
    print("Failed to run the DHCP process")

for src_mac, dhcp_session in address_dict.items():
    print(f"{src_mac} -> {dhcp_session.offered_ip_addr}")
```