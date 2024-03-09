import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import ipaddress
import csv
import time

CHASSIS_IP = "10.20.1.166"
USERNAME = "xoa"
MODULE_IDX = 4
PORT_IDX = 0
_FREYA_THOR_LOKI_MODULES = (modules.MFreya800G4S1P_a, modules.MFreya800G4S1P_b, modules.MFreya800G4S1POSFP_a, modules.MFreya800G4S1POSFP_b, modules.MThor400G7S1P, modules.MThor400G7S1P_b, modules.MThor400G7S1P_c, modules.MThor400G7S1P_d, modules.MLoki100G5S1P, modules.MLoki100G5S2P)
        

async def my_awesome_func(stop_event: asyncio.Event):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:
        
        # Access module index 0 on the tester
        module = tester.modules.obtain(MODULE_IDX)

        if not isinstance(module, _FREYA_THOR_LOKI_MODULES):
            print(f"Not Freya or Thor or Loki module")
            return None 

        # Get the port 0 on module 0 as TX port
        port = module.ports.obtain(PORT_IDX)

        # Forcibly reserve the port and reset it.
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        await asyncio.sleep(5)

        # Check how many serdes are there
        _p_capability = await port.capabilities.get()
        _serdes_count = _p_capability.serdes_count
        print(f"Port {MODULE_IDX}/{PORT_IDX} Serdes Count: {_serdes_count}")

        # Set PRBS TX Config
        await port.pcs_pma.prbs_config.tx_type.set(
            prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE,
            prbs_pattern=enums.PRBSPattern.PRBS31,
            invert=enums.PRBSInvertState.NON_INVERTED)

        await port.serdes[0].prbs.tx_config.set(prbs_seed=0, prbs_on_off=enums.PRBSOnOff.PRBSON)

async def main():
    stop_event = asyncio.Event()
    try:
        await my_awesome_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
