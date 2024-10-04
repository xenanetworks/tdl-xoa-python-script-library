################################################################
#
#                   CHASSIS UPTIME
#
# What this script shows you how to monitor the chassis uptime
# and save it into a csv file
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
import csv
import datetime

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.153.122"
USERNAME = "XOA"
FILENAME = "sys_uptime.csv"

#---------------------------
# chassis_uptime
#---------------------------
async def chassis_uptime(chassis: str, username: str, csv_filename: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="chassis_uptime.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        resp = await tester.version_str.get()
        print(f"Chassis version string: {resp.version_str}")
        resp = await tester.model_name.get()
        print(f"Chassis model name: {resp.name}")

        field = ["datetime", "sys uptime (sec)"]
        with open(csv_filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(field)
            while True:
                dat = []
                _time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dat.append(_time_str)
                resp = await mgmt.get_chassis_sys_uptime_sec(tester)
                dat.append(resp)
                writer.writerow(dat)
                logging.info(f"sys uptime = {resp}")
                await asyncio.sleep(1)

async def main():
    stop_event = asyncio.Event()
    try:
        await chassis_uptime(
            chassis=CHASSIS_IP,
            username=USERNAME,
            csv_filename=FILENAME
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
