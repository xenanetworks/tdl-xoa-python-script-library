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
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
MODULE_IDX = 0
PORT_IDX = 0

_THOR_MODULES = (modules.MThor400G7S1P, modules.MThor400G7S1P_b, modules.MThor400G7S1P_c, modules.MThor400G7S1P_d)

PAGE_ADDRESS = 1
REGISTER_ADDRESS = 2
BYTE_COUNT = 2
VALUE_HEX_STRING = "ffff"
#---------------------------
# thor_seq_access
#---------------------------
async def thor_seq_access(stop_event: asyncio.Event):
    # create tester instance and establish connection
    async with testers.L23Tester(CHASSIS_IP, USERNAME) as tester:
        print(f"{'Connect to chassis:':<20}{CHASSIS_IP}")
        print(f"{'Username:':<20}{CHASSIS_IP}")

        module = tester.modules.obtain(MODULE_IDX)
        if not isinstance(module, _THOR_MODULES):
            return None

        port = module.ports.obtain(PORT_IDX)

        print(f"Reserve Port {MODULE_IDX}/{PORT_IDX}")
        await mgmt.free_module(module=module)
        await mgmt.reserve_port(port=port)

        if len(VALUE_HEX_STRING)/2 != BYTE_COUNT:
            print(f"Byte count ({BYTE_COUNT}) doesn't match value length ({len(VALUE_HEX_STRING)/2})")
            return None
        else:
            await port.transceiver.access_rw_seq(
                page_address=PAGE_ADDRESS,
                register_address=REGISTER_ADDRESS,
                byte_count=BYTE_COUNT).set(value=Hex(VALUE_HEX_STRING))
            print(f"Write {VALUE_HEX_STRING} into Page {PAGE_ADDRESS}, Reg {REGISTER_ADDRESS}")

            resp = await port.transceiver.access_rw_seq(
                page_address=PAGE_ADDRESS,
                register_address=REGISTER_ADDRESS,
                byte_count=BYTE_COUNT).get()
            print(f"Read from Page {PAGE_ADDRESS}, Reg {REGISTER_ADDRESS}: {resp.value}")


async def main():
    stop_event = asyncio.Event()
    try:
        await thor_seq_access(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())