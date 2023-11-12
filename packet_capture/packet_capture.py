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
MODULE_IDX = 3
PORT_IDX = 0

#---------------------------
# thor_ppm_anlt_eth
#---------------------------
async def capture_example_func(stop_event: asyncio.Event):
    # create tester instance and establish connection
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:
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

        # configure capture trigger criteria
        await port.capturer.trigger.set(start_criteria=enums.StartTrigger.ON,
                                        start_criteria_filter=0,
                                        stop_criteria=enums.StopTrigger.FULL,
                                        stop_criteria_filter=0)
        
        # configure packets to keep
        await port.capturer.keep.set(kind=enums.PacketType.ALL, index=0, byte_count=-1)

        # start capture
        await port.capturer.state.set(on_off=enums.StartOrStop.START)
        # await port.capturer.state.set_start() # this is a shortcut func
        
        # wait a while
        # you should make sure your traffic is started during this period
        await asyncio.sleep(5)
        
        # stop capture
        await port.capturer.state.set(on_off=enums.StartOrStop.STOP)
        # await port.capturer.state.set_stop()  # this is a shortcut func
        
        # check capture status
        resp = await port.capturer.stats.get()
        print(f"Capture status: {'running' if resp.status == 0 else 'stopped'}")
        print(f"Number of captured packets: {resp.packets}")

        # read captures packets from the buffer and show them one by one
        pkts = await port.capturer.obtain_captured()
        for i in range(len(pkts)):
            resp = await pkts[i].packet.get()
            print(f"Packet content # {i}: {resp.hex_data}")


async def main():
    stop_event = asyncio.Event()
    try:
        await capture_example_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())