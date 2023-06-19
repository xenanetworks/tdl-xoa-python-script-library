import asyncio
from contextlib import suppress
from xoa_driver import (
    testers,
    modules,
    ports,
    enums,
    utils,
    exceptions
)
from xoa_driver.hlfuncs import (
    mgmt,
    config_cli_convert
)
import ipaddress

CHASSIS_IP = "10.20.1.170"
USERNAME = "xoa"
MODULE_IDX = 1
PORT_IDX = 4

async def my_awesome_func(stop_event: asyncio.Event):
    # create tester instance and establish connection
    async with testers.L23Tester(CHASSIS_IP, USERNAME) as tester:

        # access module 0 on the tester
        module = tester.modules.obtain(MODULE_IDX)
        if isinstance(module, modules.ModuleChimera):
            return None
        
        # access port 0 on the module as the TX port
        port = module.ports.obtain(PORT_IDX) #!Change to your port number!#

        await mgmt.reserve_port(port=port)

        await config_cli_convert.upload_port_config_from_file(port=port, path="port_config.xpc")

async def main():
    stop_event = asyncio.Event()
    try:
        await my_awesome_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())