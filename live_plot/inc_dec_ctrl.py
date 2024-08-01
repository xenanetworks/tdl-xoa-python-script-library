################################################################
#
#                   LIVE PLOTTING
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. Must be Freya.
# 3. Sync the port filter from chassis to script
# 4. Read the traffic stats of a filter
# 5. Plot the number of packets from the filter
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

import matplotlib.pyplot as plt
import numpy as np
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
TX_PORT = "3/0"
INTERVAL = 2.0

#---------------------------
# inc_dec_ctrl
#---------------------------
async def inc_dec_ctrl(chassis: str, username: str, tx_port_str: str, interval: float, stop_event: asyncio.Event):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="inc_dec_ctrl.log", mode="a"),
            logging.StreamHandler()]
        )

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        # Access module on the tester
        _mid_tx = int(tx_port_str.split("/")[0])
        _pid_tx = int(tx_port_str.split("/")[1])
        tx_module_obj = tester.modules.obtain(_mid_tx)
        
        if isinstance(tx_module_obj, modules.E100ChimeraModule):
            logging.info(f"FEC not supported on E100 Chimera modules")
            return None
        
        if isinstance(tx_module_obj, modules.Z10OdinModule):
            logging.info(f"FEC not supported on Z10 Odin modules")
            return None 

        # Get the ports
        tx_port_obj = tx_module_obj.ports.obtain(_pid_tx)

        # Forcibly reserve the port
        await mgmt.free_module(module=tx_module_obj, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj)

        # Sync the filters from chassis to script
        await asyncio.sleep(1)
        await tx_port_obj.streams.server_sync()

        logging.info(f"Suppress streams before traffic start")
        for s in tx_port_obj.streams:
            await s.enable.set_suppress()
        await asyncio.sleep(1)

        logging.info(f"Start traffic")
        await tx_port_obj.traffic.state.set_start()

        while not stop_event.is_set():
            for s in tx_port_obj.streams:
                logging.info(f"Enable stream {s.idx}")
                await s.enable.set_on()
                await asyncio.sleep(interval)
            for s in tx_port_obj.streams:
                logging.info(f"Suppress stream {s.idx}")
                await s.enable.set_suppress()
                await asyncio.sleep(interval)
        
        await tx_port_obj.traffic.state.set_stop()
        await mgmt.free_port(tx_port_obj)

async def main():
    stop_event = asyncio.Event()
    try:
        await inc_dec_ctrl(
            chassis=CHASSIS_IP,
            username=USERNAME,
            tx_port_str=TX_PORT,
            interval=INTERVAL,
            stop_event = stop_event
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
