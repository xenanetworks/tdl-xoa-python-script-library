#!/usr/bin/env python3

import asyncio
from xoa_driver import testers, ports
from xoa_driver.hlfuncs import mgmt
from dhcp_core.client import DhcpClient

global_chassis_addr = "10.165.136.70"
global_chassis_pass = "xena"
global_username     = "xena-dhcp-client"
global_module_id = 1
global_port_id = 2

        
async def run_dhcp_client_sample():
    global global_chassis_addr
    global global_username
    global global_chassis_pass
    global global_module_id
    global global_port_id
    
    # connecting to chassis
    async with testers.L23Tester(host=global_chassis_addr, username=global_username, password=global_chassis_pass) as tester:
    
        module_obj = tester.modules.obtain(global_module_id)
        port_obj = module_obj.ports.obtain(global_port_id)

        if isinstance(port_obj, ports.E100ChimeraPort):
            raise TypeError(f"Expected a GenericL23Port, got {type(port_obj)}")

        # reserve the port
        await mgmt.reserve_port(port_obj)
    
        dhcp_handler = DhcpClient(port_obj)
        ret_error, address_dict, num_success, num_faliure = await dhcp_handler.get_dhcp_addresses("04:F4:BF:00:00:00", 100, 3, 3000)

        if ret_error == DhcpClient.Error.Success:
            print("The DHCP process ran Successfully")
            print(f"Number of Success: {num_success}, Number of Failure: {num_faliure}")
        else:
            print("Failed to run the DHCP process")
        
        for src_mac, dhcp_session in address_dict.items():
            print(f"{src_mac} -> {dhcp_session.offered_ip_addr}")
        
        # release the port
        await mgmt.release_port(port_obj)
    
async def main():
    task = asyncio.create_task(run_dhcp_client_sample())
    try:
        await task
    except asyncio.CancelledError:
        pass  # Handle task cancellation if necessary
    finally:
        loop.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())