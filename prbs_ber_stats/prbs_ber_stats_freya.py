################################################################
#
#                   PRBS BER STATISTICS
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. Must be Freya
# 3. Reset the port
# 4. Set the port PRBS mode on
# 5. Collect per-second statistics
#
################################################################

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
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "XOA"
PORT1 = "3/0"       
PORT2 = "6/0"
DURATION = 20

#---------------------------
# prbs_ber_stats
#---------------------------
async def prbs_ber_stats(chassis: str, username: str, port_str1: str, port_str2: str, duration: int):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        
        # Access module on the tester
        _mid1 = int(port_str1.split("/")[0])
        _pid1 = int(port_str1.split("/")[1])
        _mid2 = int(port_str2.split("/")[0])
        _pid2 = int(port_str2.split("/")[1])
        module_obj1 = tester.modules.obtain(_mid1)
        module_obj2 = tester.modules.obtain(_mid2)

        if not isinstance(module_obj1, modules.Z800FreyaModule):
            logging.info(f"Not Freya or Thor or Loki module")
            return None
        if not isinstance(module_obj2, modules.Z800FreyaModule):
            logging.info(f"Not Freya or Thor or Loki module")
            return None 

        # Get the port objects
        port_obj1 = module_obj1.ports.obtain(_pid1)
        port_obj2 = module_obj2.ports.obtain(_pid2)

        # Forcibly reserve the port and reset it.
        await mgmt.reserve_port(port_obj1, reset=True)
        
        await mgmt.reserve_port(port_obj2, reset=True)
        

        await asyncio.sleep(5)

        # Check how many serdes are there
        _p_capability1 = await port_obj1.capabilities.get()
        _serdes_count1 = _p_capability1.serdes_count
        logging.info(f"Port {_mid1}/{_pid1} Serdes Count: {_serdes_count1}")
        _p_capability2 = await port_obj2.capabilities.get()
        _serdes_count2 = _p_capability2.serdes_count
        logging.info(f"Port {_mid2}/{_pid2} Serdes Count: {_serdes_count2}")

        # Set PRBS Config on the TX port
        await port_obj1.l1.prbs_config.set(
            prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE,
            polynomial=enums.PRBSPolynomial.PRBS13,
            invert=enums.PRBSInvertState.INVERTED,
            statistics_mode=enums.PRBSStatisticsMode.PERSECOND)
        # Set PRBS Config on the RX port
        await port_obj2.l1.prbs_config.set(
            prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE,
            polynomial=enums.PRBSPolynomial.PRBS13,
            invert=enums.PRBSInvertState.INVERTED,
            statistics_mode=enums.PRBSStatisticsMode.PERSECOND)

        # Enable PRBS on all serdes on the Tx port
        for i in range(_serdes_count1):
            await port_obj1.l1.serdes[i].prbs.control.set(prbs_seed=0, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

        # _list = []
        # for i in range(_serdes_count1):
        #     _list.append(port_obj1.serdes[i].prbs.tx_config.set(prbs_seed=0, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF))
        # await utils.apply(*_list)

        await asyncio.sleep(2.0)

        # clear counters on the Rx port
        await port_obj2.pcs_pma.rx.clear.set()

        # Sample PRBS status counter on the other port every second for 20 secs.
        _count = 0
        _list = []
        for i in range(_serdes_count1):
            _list.append(port_obj2.l1.serdes[i].prbs.status.get())
        while _count <= duration-1:
            resp = await utils.apply(*_list)
            print(f"*"*_count)
            for i in range(_serdes_count2):
                if resp[i].error_count > 0:
                    print(f"Serdes {i}, PRBS Lock={resp[i].lock.name}, PRBS Bits={resp[i].byte_count*8}, PRBS Errors={resp[i].error_count}, Error Rate={resp[i].error_count/resp[0].byte_count/8}")
                else:
                    print(f"Serdes {i}, PRBS Lock={resp[i].lock.name}, PRBS Bits={resp[i].byte_count*8}, PRBS Errors={resp[i].error_count}, Error Rate<{4.6/resp[0].byte_count/8}")
            await asyncio.sleep(1.0)
            _count += 1

        # Stop PRBS on the tx port all serdes
        _list = []
        for i in range(_serdes_count1):
            _list.append(port_obj1.l1.serdes[i].prbs.control.set(prbs_seed=0, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF))
        await utils.apply(*_list)

        # Release the ports
        await mgmt.release_port(port=port_obj1)
        await mgmt.release_port(port=port_obj2)

async def main():
    stop_event = asyncio.Event()
    try:
        await prbs_ber_stats(chassis=CHASSIS_IP, username=USERNAME, port_str1=PORT1, port_str2=PORT2, duration=DURATION)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
