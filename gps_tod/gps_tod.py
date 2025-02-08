################################################################
#
#                   GPS ToD Example
#
# What this script example does:
# - Start the preconfigured traffic based on GPS Time of Day (ToD)
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
import logging
import datetime
from typing_extensions import List

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.70"
USERNAME = "gps_tod"
PORT_LIST = ["2/0", "2/1"]
YEAR = 2025
MONTH = 2
DAY = 8
HOUR = 14
MIUNTE = 7
SECOND = 0
MICROSECOND = 0

#---------------------------
# gps_tod
#---------------------------
async def gps_tod(chassis: str, username: str, port_list_str: List[str], year: int, month: int, day: int, hour: int, minute: int, second: int, microsecond: int):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="gps_tod.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")
        
        module_port_list = []
        for port_str in port_list_str:

            # Access module index 0 on the tester
            mid = int(port_str.split("/")[0])
            module_port_list.append(mid)
            pid = int(port_str.split("/")[1])
            module_port_list.append(pid)

            module_obj = tester_obj.modules.obtain(mid)
            if isinstance(module_obj, modules.E100ChimeraModule):
                return None # commands which used in this example are not supported by Chimera Module

            # Get the port on module as TX port
            tx_port = module_obj.ports.obtain(pid)

            # Forcibly reserve the TX port
            await mgmt.reserve_port(tx_port)

        await asyncio.sleep(1)

        resp = await tester_obj.time.get()
        logging.info(f"{'Current Time:':<20}{resp.local_time}")
        c_time = resp.local_time
        now_to_epoch = int(datetime.datetime.now().timestamp()) # Get the current time in epoch
        schedule_to_epoch = int(datetime.datetime(year, month, day, hour, minute, microsecond).timestamp()) # Get the scheduled time in epoch
        schedule_to_now = schedule_to_epoch - now_to_epoch # Calculate the time difference between the current time and the scheduled time
        c_trafficsync_time = c_time + schedule_to_now # Convert the time difference to C_TIME format

        # Start the traffic
        await tester_obj.traffic_sync.set(on_off=enums.OnOff.ON, timestamp=c_trafficsync_time, module_ports=module_port_list)



async def main():
    stop_event = asyncio.Event()
    try:
        await gps_tod(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_list_str=PORT_LIST,
            year=YEAR,
            month=MONTH,
            day=DAY,
            hour=HOUR,
            minute=MIUNTE,
            second=SECOND,
            microsecond=MICROSECOND
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
