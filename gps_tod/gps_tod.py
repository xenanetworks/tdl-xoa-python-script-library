################################################################
#
#                   Traffic ToD Example
#
# What this script example does:
# - Start the preconfigured traffic based on GMT Time of Day (ToD)
# - Precision is second
# - Datetime format is "YYYY-MM-DD HH:MM:SS"
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

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.70"
USERNAME = "gps_tod"
PORT_LIST = ["3/2", "3/3"]
TOD_GMT = "2025-02-17 15:18:00"

# Function to convert string to datetime
def convert(datetime_str):
    format = "%Y-%m-%d %H:%M:%S"
    datetime_result = datetime.datetime.strptime(datetime_str, format)
    return datetime_result

#---------------------------
# gps_tod
#---------------------------
async def gps_tod(chassis: str, username: str, port_list_str: list, tod_chassis_gmt: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="gps_tod.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Xena tester using Python context manager
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
            await mgmt.reserve_port(tx_port, reset=True)

        await asyncio.sleep(1)

        resp = await tester_obj.time.get()
        c_time = resp.local_time
        logging.info(f"{'C_TIME:':<20}{c_time}")

        _delta_day = c_time // 86400
        _delta_sec = c_time % 86400
        time_now_gmt = datetime.datetime(2010, 1, 1, 0, 0, 0, 0) + datetime.timedelta(days=_delta_day, seconds=_delta_sec)
        logging.info(f"{'Now (GMT):':<20}{time_now_gmt}")

        scheduled_datetime_gmt = convert(tod_chassis_gmt)
        logging.info(f"{'Schedule (GMT):':<20} {scheduled_datetime_gmt}")

        delta = scheduled_datetime_gmt - time_now_gmt
        delta_sec = int(delta.total_seconds())
        logging.info(f"{'Delta (sec)':<20}{delta_sec}")

        c_trafficsync_time = c_time + delta_sec # Convert the time difference to C_TIME format
        logging.info(f"{'New C_TIME:':<20}{c_trafficsync_time}")

        # Start the traffic
        await tester_obj.traffic_sync.set(on_off=enums.OnOff.ON, timestamp=c_trafficsync_time, module_ports=module_port_list)



async def main():
    stop_event = asyncio.Event()
    try:
        await gps_tod(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_list_str=PORT_LIST,
            tod_chassis_gmt=TOD_GMT
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
