import asyncio

from xoa_driver import utils
from xoa_driver.lli import commands as cmd
from xoa_driver.lli import TransportationHandler
from xoa_driver.lli import establish_connection

from dhcp_core.dhcp_server import DHCPServerConfiguration, DHCPServer

global_chassis_addr = "10.165.136.70"
global_chassis_pass = "xena"
global_hostname     = "xena-dhcp-server"
global_module_id    = 3
global_port_id      = 4

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
    global chassis_1_handler
    global global_module_id
    global global_port_id
    await common_config()
    
    dhcp_configuration = dhcp_config()
    
    server = DHCPServer(chassis_1_handler, global_module_id, global_port_id, dhcp_configuration)
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