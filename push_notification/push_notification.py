################################################################
#
#                   PUSH NOTIFICATION (SYNC MONITORING)
#
# What this script example does:
# 1. Connect to a tester
# 2. Catch port receive sync change event
# 3. Save data in csv file
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
import csv

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
PORT = "6/0"
CSV_FILENAME = "sync_detection.csv"

#---------------------------
# Class PushNotification
#---------------------------
class PushNotification():

    def __init__(self):
        self.previous_time = time.time()
        self.chassis: str
        self.username: str
        self.port_str: str
        self.csv_filename: str

    # this is the callback function when event change happens
    async def _change_sync_status(self, port: ports.GenericL23Port, v) -> None:
            port_id_str = f"{port.kind.module_id}-{port.kind.port_id}"
            sync_status_str = v.sync_status.name
            current_time = time.time()
            event_time_str = '{:.9f}'.format(current_time)
            delta_time_str = '{:.9f}'.format(current_time-self.previous_time)
            self.previous_time = current_time
            logging.info(f"{port_id_str}, {sync_status_str}, {event_time_str}, {delta_time_str}")
            with open(self.csv_filename, 'a', newline='') as file:
                    writer = csv.writer(file)
                    dat = [port_id_str, sync_status_str, event_time_str, delta_time_str]
                    writer.writerow(dat)

    #---------------------------
    # push_notification
    #---------------------------
    async def push_notification(self):
        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename="sync_detection.log", mode="a"),
                logging.StreamHandler()]
            )
        
        # Establish connection to a Valkyrie tester using Python context manager
        # The connection will be automatically terminated when it is out of the block
        async with testers.L23Tester(host=self.chassis, username=self.username, password="xena", port=22606, enable_logging=False) as tester:
            logging.info(f"===================================")
            logging.info(f"{'Connect to chassis:':<20}{self.chassis}")
            logging.info(f"{'Username:':<20}{self.username}")

            # Access module index 0 on the tester
            _mid = int(self.port_str.split("/")[0])
            _pid = int(self.port_str.split("/")[1])
            module = tester.modules.obtain(_mid)

            # Get the port on module as TX port
            port = module.ports.obtain(_pid)

            field = ["port", "status", "timestamp (sec)", "delta"]
            with open(self.csv_filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(field)

            port.on_receive_sync_change(self._change_sync_status)
            
            i = 0
            while True:
                i += 1
                await asyncio.sleep(1)

async def main():
    stop_event = asyncio.Event()
    try:
        pn = PushNotification()
        pn.chassis = CHASSIS_IP
        pn.username = USERNAME
        pn.port_str = PORT
        pn.csv_filename = CSV_FILENAME
        await pn.push_notification()
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
