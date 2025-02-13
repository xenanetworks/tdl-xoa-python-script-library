import asyncio

from xoa_driver import utils
from xoa_driver.lli import commands as cmd
from xoa_driver.lli import TransportationHandler
from xoa_driver.lli import establish_connection

from dhcp_core.dhcp_client import DhcpClient

global_chassis_addr = "10.165.136.70"
global_chassis_pass = "xena"
global_hostname     = "xena-dhcp-client"
global_module_id = 2
global_port_id = 4

chassis_1_handler = TransportationHandler()

async def common_config():
    global global_chassis_addr
    global global_chassis_pass
    global global_hostname
    global chassis_1_handler
    global global_module_id
    global global_port_id
    await establish_connection(chassis_1_handler, global_chassis_addr)
    await utils.apply(
        cmd.C_LOGON(chassis_1_handler).set(global_chassis_pass),
        cmd.C_OWNER(chassis_1_handler).set(global_hostname),
    ) # connecting to chassis
    
    reserved = await cmd.P_RESERVATION(chassis_1_handler, global_module_id, global_port_id).get()
    if reserved.status == cmd.ReservedStatus.RESERVED_BY_OTHER:
        print(f"Failed to reserve the port. It's already reserved by someone else. Release the port and try again.")
        exit(-1)
    
    await cmd.P_RESERVATION(chassis_1_handler, global_module_id, global_port_id).set(operation=cmd.ReservedAction.RESERVE)
    
async def run_dhcp_client_sample():
    global global_chassis_addr
    global chassis_1_handler
    global global_module_id
    global global_port_id
    await common_config()
    
    dhcp_handler = DhcpClient(chassis_handler=chassis_1_handler, module_id=global_module_id, port_id=global_port_id)
    ret_error, address_dict, num_success, num_faliure = await dhcp_handler.get_dhcp_addresses("04:F4:BF:00:00:00", 100, 3, 3000)
    if ret_error == DhcpClient.Error.Success:
        print("The DHCP process ran Successfully")
        print(f"Number of Success: {num_success}, Number of Failure: {num_faliure}")
    else:
        print("Failed to run the DHCP process")
    
    for src_mac, dhcp_session in address_dict.items():
        print(f"{src_mac} -> {dhcp_session.offered_ip_addr}")
    
    # release the port
    await cmd.P_RESERVATION(chassis_1_handler, global_module_id, global_port_id).set(operation=cmd.ReservedAction.RELEASE)
    
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