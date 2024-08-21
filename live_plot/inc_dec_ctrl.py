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
TX_PORT_1 = "3/0"
TX_PORT_1_MIN = 50
TX_PORT_1_MAX = 50
TX_PORT_2 = "3/1"
TX_PORT_2_MIN = 50
TX_PORT_2_MAX = 60
INTERVAL = 2.0


async def inc_dec_background_task(
        port: ports.GenericL23Port,
        min: int,
        max: int,
        interval: float,
        stop_event: asyncio.Event
    ) -> None:
        
        while True:
            if min != max:
                for i in range(min, max):
                    s = port.streams.obtain(i)
                    logging.info(f"Enable stream {s.idx} on port {port.kind.module_id}/{port.kind.port_id}")
                    await s.enable.set_on()
                    await asyncio.sleep(interval)
                    
                for i in reversed(range(min, max)):
                    s = port.streams.obtain(i)
                    logging.info(f"Enable stream {s.idx} on port {port.kind.module_id}/{port.kind.port_id}")
                    await s.enable.set_suppress()
                    await asyncio.sleep(interval)
            else:
                await asyncio.sleep(interval)

#---------------------------
# inc_dec_ctrl
#---------------------------
async def inc_dec_ctrl(
        chassis: str, 
        username: str, 
        tx_port_str_1: str,
        tx_port_1_min: int,
        tx_port_1_max: int,
        tx_port_2_min: int,
        tx_port_2_max: int,
        tx_port_str_2: str, 
        interval: float, 
        stop_event: asyncio.Event):
    
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
        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"TX Port 1:               {tx_port_str_1}")
        logging.info(f"TX Port 2:               {tx_port_str_2}")
        logging.info(f"#####################################################################")

        # Access module on the tester
        _mid_tx_1 = int(tx_port_str_1.split("/")[0])
        _pid_tx_1 = int(tx_port_str_1.split("/")[1])
        tx_module_obj_1 = tester.modules.obtain(_mid_tx_1)
        _mid_tx_2 = int(tx_port_str_2.split("/")[0])
        _pid_tx_2 = int(tx_port_str_2.split("/")[1])
        tx_module_obj_2 = tester.modules.obtain(_mid_tx_2)
        
        if isinstance(tx_module_obj_1, modules.E100ChimeraModule) or isinstance(tx_module_obj_1, modules.Z10OdinModule):
            logging.info(f"Module {_mid_tx_1} must not be Chimera or Odin")
            return None
        
        if isinstance(tx_module_obj_2, modules.E100ChimeraModule) or isinstance(tx_module_obj_2, modules.Z10OdinModule):
            logging.info(f"Module {_mid_tx_2} must not be Chimera or Odin")
            return None

        # Get the ports
        tx_port_obj_1 = tx_module_obj_1.ports.obtain(_pid_tx_1)
        tx_port_obj_2 = tx_module_obj_2.ports.obtain(_pid_tx_2)

        # Forcibly reserve the port
        await mgmt.free_module(module=tx_module_obj_1, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj_1)
        await mgmt.free_module(module=tx_module_obj_2, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj_2)

        await tx_port_obj_1.traffic.state.set_stop()
        await tx_port_obj_2.traffic.state.set_stop()

        # Sync the filters from chassis to script
        await asyncio.sleep(1)
        await tx_port_obj_1.streams.server_sync()
        await tx_port_obj_2.streams.server_sync()

        if tx_port_1_min > len(tx_port_obj_1.streams) or tx_port_1_max > len(tx_port_obj_1.streams):
            logging.warning(f"Start/End for Port {tx_port_str_1} must be <= 100")
            return None
        if tx_port_2_min > len(tx_port_obj_2.streams) or tx_port_2_max > len(tx_port_obj_2.streams):
            logging.warning(f"Start/End for Port {tx_port_str_1} must be <= 100")
            return None

        logging.info(f"Enable {tx_port_1_min} streams on Port {tx_port_str_1}")
        for i in range(tx_port_1_min):
            s = tx_port_obj_1.streams.obtain(i)
            await s.enable.set_on()
        logging.info(f"Suppress {len(tx_port_obj_1.streams)-tx_port_1_min} streams on Port {tx_port_str_1}")
        for i in range(tx_port_1_min, len(tx_port_obj_1.streams)):
            s = tx_port_obj_1.streams.obtain(i)
            await s.enable.set_suppress()
        await asyncio.sleep(1)
        logging.info(f"Enable {tx_port_2_min} streams on Port {tx_port_str_2}")
        for i in range(tx_port_2_min):
            s = tx_port_obj_2.streams.obtain(i)
            await s.enable.set_on()
        logging.info(f"Suppress {len(tx_port_obj_2.streams)-tx_port_2_min} streams on Port {tx_port_str_2}")    
        for i in range(tx_port_2_min, len(tx_port_obj_2.streams)):
            s = tx_port_obj_2.streams.obtain(i)
            await s.enable.set_suppress()
        await asyncio.sleep(1)

        logging.info(f"Start traffic on Port {tx_port_str_1}")
        await tx_port_obj_1.traffic.state.set_start()
        logging.info(f"Start traffic on Port {tx_port_str_2}")
        await tx_port_obj_2.traffic.state.set_start()

        asyncio.create_task(inc_dec_background_task(tx_port_obj_1, tx_port_1_min, tx_port_1_max, interval, stop_event))
        asyncio.create_task(inc_dec_background_task(tx_port_obj_2, tx_port_2_min, tx_port_2_max, interval, stop_event))
        await stop_event.wait()
        
        # await tx_port_obj_1.traffic.state.set_stop()
        # await mgmt.free_port(tx_port_obj_1)

async def main():
    stop_event = asyncio.Event()
    try:
        await inc_dec_ctrl(
            chassis=CHASSIS_IP,
            username=USERNAME,
            tx_port_str_1=TX_PORT_1,
            tx_port_1_min=TX_PORT_1_MIN,
            tx_port_1_max=TX_PORT_1_MAX,
            tx_port_str_2=TX_PORT_2,
            tx_port_2_min=TX_PORT_2_MIN,
            tx_port_2_max=TX_PORT_2_MAX,
            interval=INTERVAL,
            stop_event = stop_event
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
