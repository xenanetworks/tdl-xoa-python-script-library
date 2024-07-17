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
PORT = "6/0"
DURATION = 120
FILTER_IDX = 0
WINDOW_SIZE = 10
PLOTTING_INTERVAL = 1.0

#---------------------------
# live_plot
#---------------------------
async def live_plot(chassis: str, username: str, port_str: str, filter_idx: int, duration: int, win_size: int, plot_interval: float):
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

        # Access module on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.info(f"FEC not supported on E100 Chimera modules")
            return None
        
        if isinstance(module_obj, modules.Z10OdinModule):
            logging.info(f"FEC not supported on Z10 Odin modules")
            return None 

        # Get the port on module as TX port
        port_obj = module_obj.ports.obtain(_pid)

        # Forcibly reserve the port and reset it.
        await mgmt.free_module(module=module_obj, should_free_ports=False)
        await mgmt.reserve_port(port_obj)

        # Sync the filters from chassis to script
        await asyncio.sleep(1)
        await port_obj.filters.server_sync()
        # Get filter's description
        filter0 = port_obj.filters.obtain(filter_idx)
        resp = await filter0.comment.get()
        figure_title = resp.comment

        # live plotting
        x = 0
        y = 0
        plt.ion()
        # fig = plt.figure(facecolor='white', layout='constrained')
        fig, ax = plt.subplots()
        fig.suptitle(f"Filter {filter_idx}: {figure_title}")
        
        data = deque([(x, y)], maxlen=win_size)
        line, = plt.step(*zip(*data), c='black')
        plt.xlabel(f"Time Interval ({plot_interval}s)")
        plt.ylabel("packet_count_since_cleared")
        await port_obj.statistics.rx.clear.set()
        for i in range(duration):
            x = i
            # Read the filtered traffic stats - packet count since cleared
            resp = await port_obj.statistics.rx.obtain_filter_statistics(filter=filter_idx).get()
            y = resp.packet_count_since_cleared
            data.append((x, y))
            ax.relim()
            ax.autoscale_view()
            line.set_data(*zip(*data))
            plt.show()
            plt.pause(plot_interval)
        # plt.show()


async def main():
    stop_event = asyncio.Event()
    try:
        await live_plot(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            filter_idx=FILTER_IDX,
            duration=DURATION,
            win_size=WINDOW_SIZE,
            plot_interval=PLOTTING_INTERVAL
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
