#!/usr/bin/env python3

import asyncio
from dhcp_core.server import DHCPServerConfiguration, DHCPServer
from xoa_driver import testers, ports
from xoa_driver.hlfuncs import mgmt

global_chassis_addr = "10.165.136.70"
global_chassis_pass = "xena"
global_username     = "xena-dhcp-server"
global_module_id    = 1
global_port_id      = 3
        
def dhcp_config() -> DHCPServerConfiguration:
    configuration = DHCPServerConfiguration()
    configuration.debug = print
    configuration.network = '192.168.0.0'
    configuration.broadcast_address = '192.168.255.255'
    configuration.subnet_mask = '255.255.0.0'
    configuration.server_identifier = "192.168.10.1"
    configuration.ip_address_lease_time = 600
    # configuration.router = ["192.168.0.1"]
    # configuration.domain_name_server = ["8.8.8.8", "4.2.2.4"]
    return configuration
    
async def run_dhcp_server_service():
    global global_chassis_addr
    global global_chassis_pass
    global global_username
    global global_module_id
    global global_port_id
    
    # connecting to chassis
    async with testers.L23Tester(host=global_chassis_addr, username=global_username, password=global_chassis_pass) as tester:
    
        module_obj = tester.modules.obtain(global_module_id)
        port_obj = module_obj.ports.obtain(global_port_id)

        # reserve the port
        await mgmt.reserve_port(port_obj)

        if isinstance(port_obj, ports.E100ChimeraPort):
            raise TypeError(f"Expected a GenericL23Port, got {type(port_obj)}")
    
        dhcp_configuration = dhcp_config()
        
        server = DHCPServer(port_obj, dhcp_configuration)
        for ip in server.configuration.all_ip_addresses():
            assert ip == server.configuration.network_filter()
        await server.run()
    
async def main():
    task = asyncio.create_task(run_dhcp_server_service())
    try:
        await task
    except asyncio.CancelledError:
        pass  # Handle task cancellation if necessary
    finally:
        loop.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())