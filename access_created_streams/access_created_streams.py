import asyncio
from xoa_driver import (
    testers,
    modules,
    ports,
    utils,
    enums,
    exceptions
)
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex


#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.170"
USERNAME = "XOA"
MODULE_IDX = 2
PORT_IDX = 2

#---------------------------
# thor_ppm_anlt_eth
#---------------------------
async def capture_example_func(stop_event: asyncio.Event):
    # create tester instance and establish connection
    async with testers.L23Tester(CHASSIS_IP, USERNAME) as tester:
        print(f"{'Connect to chassis:':<20}{CHASSIS_IP}")
        print(f"{'Username:':<20}{CHASSIS_IP}")

        # access the module object
        module = tester.modules.obtain(MODULE_IDX)

        if isinstance(module, modules.ModuleChimera):
            return None
        
        # access the port object
        port = module.ports.obtain(PORT_IDX)

        # reserve the port by force
        await mgmt.reserve_port(port=port, force=True)

        # synchronize the streams on the physical port and the stream indices on the port object
        await port.streams.server_sync()

        print(f"Number of streams on the port: {len(port.streams)}")
        for i in range(len(port.streams)):
            stream = port.streams.obtain(i)
            resp = await stream.comment.get()
            print(f"Stream [{i}] : {resp.comment}")

        await mgmt.free_port(port)



async def main():
    stop_event = asyncio.Event()
    try:
        await capture_example_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())