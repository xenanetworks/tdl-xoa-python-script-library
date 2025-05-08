################################################################
#
#                   LOS Monitor
#
# What this script example does:
# Read the Latched RX LOS from CMIS transceiver
# 
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import Hex
import ipaddress
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "los_mon"
PORT = "3/0"


#---------------------------
# los_mon_gui
#---------------------------
async def rx_los_mon(chassis: str, username: str, port_str: str):
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
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        # Access module index 0 on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        if isinstance(module_obj, modules.E100ChimeraModule):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module as TX port
        port_obj = module_obj.ports.obtain(_pid)

        # Forcibly reserve the TX port
        # await mgmt.reserve_port(port_obj, reset=True)
        # await asyncio.sleep(1)

        # Supported Pages Advertising - BanksSupported
        # Banks supported for Pages 10h-1Fh
        banks_supported = 0
        resp = await port_obj.transceiver.access_rw_seq(page_address=0x01, register_address=124, byte_count=1).get()
        print(resp.value)
        banks_supported_field = int(resp.value, 16) & 0x03
        if banks_supported_field == 0x00: # 00b: Bank 0 supported (8 lanes)
            banks_supported = 1
        elif banks_supported_field == 0x01: # 01b: Banks 0 and 1 supported (16 lanes)
            banks_supported = 2
        elif banks_supported_field == 0x02: # 10b: Banks 0-3 supported (32 lanes)
            banks_supported = 4
        else:
            banks_supported = 0

        # Lane-Specific Output Status (Page 11h)
        # Latched Rx LOS Flag, media lane <i>
        PAGE_LANE_SPECIFIC_OUTPUT_STATUS = 17
        BYTE_LOS_FLAG_TX = 136
        BYTE_LOS_FLAG_RX = 147
        i = 0
        while True:
            for _bank in range(banks_supported):
                resp = await port_obj.transceiver.access_rw_seq_bank(
                    bank_address=_bank, 
                    page_address=PAGE_LANE_SPECIFIC_OUTPUT_STATUS, 
                    register_address=BYTE_LOS_FLAG_RX, 
                    byte_count=1).get()
                out = [1 if int(resp.value, 16) & (1 << (8-1-n)) else 0 for n in range(8)]
                print(f"{i} {resp.value} - {out}")
                i += 1
            await asyncio.sleep(0.05)

        

        # while True:
        #     resp = await port_obj.transceiver.access_rw_seq()


async def main():
    stop_event = asyncio.Event()
    try:
        await rx_los_mon(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
