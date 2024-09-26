################################################################
#
#                   PUSH NOTIFICATION
#
# What this script example does:
# 1. Connect to a tester
# 2. Catch port receive sync change event
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
import time
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.66"
USERNAME = "xoa"
PORT = "8/1"

# this is the callback function when event change happens
async def _change_sync_status(port: ports.GenericL23Port, v) -> None:
        print(f"{'{:.9f}'.format(time.time())}, {v.sync_status.name}")

#---------------------------
# push_notification
#---------------------------
async def push_notification(chassis: str, username: str, port_str: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="push_notification.log", mode="a"),
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
        module = tester.modules.obtain(_mid)

        # Get the port on module as TX port
        port = module.ports.obtain(_pid)

        port.on_receive_sync_change(_change_sync_status)
        
        i = 0
        while True:
            i += 1
            await asyncio.sleep(1)

async def main():
    stop_event = asyncio.Event()
    try:
        await push_notification(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
