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
RX_PORT = "6/0"
DURATION = 3600
ECN11_FILTER_IDX = 0
ECN10_FILTER_IDX = 0
WINDOW_SIZE = 60
PLOTTING_INTERVAL = 1.0

FIGURE_TITLE = "XenaManager Displaying Traffic and PFC on Z800 Freya"

#---------------------------
# live_plot
#---------------------------
async def live_plots(chassis: str, username: str, tx_port_str: str, rx_port_str: str, ecn11_filter_idx: int, ecn10_filter_idx: int, figure_title: str, duration: int, win_size: int, plot_interval: float):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="live_plot.log", mode="a"),
            logging.StreamHandler()]
        )

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        # Access module on the tester
        _mid_rx = int(rx_port_str.split("/")[0])
        _pid_rx = int(rx_port_str.split("/")[1])
        rx_module_obj = tester.modules.obtain(_mid_rx)
        _mid_tx = int(tx_port_str.split("/")[0])
        _pid_tx = int(tx_port_str.split("/")[1])
        tx_module_obj = tester.modules.obtain(_mid_tx)

        if isinstance(rx_module_obj, modules.E100ChimeraModule):
            logging.info(f"FEC not supported on E100 Chimera modules")
            return None
        
        if isinstance(rx_module_obj, modules.Z10OdinModule):
            logging.info(f"FEC not supported on Z10 Odin modules")
            return None 
        
        if isinstance(tx_module_obj, modules.E100ChimeraModule):
            logging.info(f"FEC not supported on E100 Chimera modules")
            return None
        
        if isinstance(tx_module_obj, modules.Z10OdinModule):
            logging.info(f"FEC not supported on Z10 Odin modules")
            return None 

        # Get the ports
        rx_port_obj = rx_module_obj.ports.obtain(_pid_rx)
        tx_port_obj = tx_module_obj.ports.obtain(_pid_tx)

        # Forcibly reserve the port
        await mgmt.free_module(module=rx_module_obj, should_free_ports=False)
        await mgmt.reserve_port(rx_port_obj)
        await mgmt.free_module(module=tx_module_obj, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj)

        # Sync the filters from chassis to script
        await asyncio.sleep(1)
        await rx_port_obj.filters.server_sync()
        # Get filter's description
        # filter0 = rx_port_obj.filters.obtain(filter_idx)
        # resp = await filter0.comment.get()
        # figure_title = resp.comment

        # live plotting
        x = 0
        y0 = 0
        y1 = 0
        y2 = 0
        y3 = 0

        plt.ion()

        fig = plt.figure()
        gs = fig.add_gridspec(4, hspace=0)
        axs = gs.subplots(sharex=True)

        fig.suptitle(figure_title)
        
        data0 = deque([(x, y0)], maxlen=win_size)
        data1 = deque([(x, y1)], maxlen=win_size)
        data2 = deque([(x, y2)], maxlen=win_size)
        data3 = deque([(x, y3)], maxlen=win_size)

        line0, = axs[0].step(*zip(*data0), c='black')
        line1, = axs[1].step(*zip(*data1), c='blue')
        line2, = axs[2].step(*zip(*data2), c='red')
        line3, = axs[3].step(*zip(*data3), c='blue')

        axs[0].set(xlabel=f"Time ({plot_interval}s)", ylabel=f"Traffic Rate Gbps (port {tx_port_str})")
        axs[1].set(xlabel=f"Time ({plot_interval}s)", ylabel=f"PFC Count (port {tx_port_str})")
        axs[2].set(xlabel=f"Time ({plot_interval}s)", ylabel=f"ECN = 11 (port {rx_port_str})")
        axs[3].set(xlabel=f"Time ({plot_interval}s)", ylabel=f"ECN = 10 (port {rx_port_str})")
        
        await rx_port_obj.statistics.rx.clear.set()
        await tx_port_obj.statistics.rx.clear.set()

        for i in range(duration):
            x = i
            resp0, resp1, resp2, resp3 = await asyncio.gather(
                tx_port_obj.statistics.tx.total.get(), # Read tx port total rate
                tx_port_obj.statistics.rx.pfc_stats.get(), # Read pfc packet count on the tx port
                rx_port_obj.statistics.rx.obtain_filter_statistics(filter=ecn11_filter_idx).get(), # Read the filtered traffic stats - packet count since cleared
                rx_port_obj.statistics.rx.obtain_filter_statistics(filter=ecn10_filter_idx).get(), # Read the filtered traffic stats - packet count since cleared
            )

            y0 = resp0.bit_count_last_sec/1_000_000_000
            y1 = resp1.packet_count
            y2 = resp2.packet_count_since_cleared
            y3 = resp3.packet_count_since_cleared

            data0.append((x, y0))
            axs[0].relim()
            axs[0].autoscale_view()
            line0.set_data(*zip(*data0))

            data1.append((x, y1))
            axs[1].relim()
            axs[1].autoscale_view()
            line1.set_data(*zip(*data1))

            data2.append((x, y2))
            axs[2].relim()
            axs[2].autoscale_view()
            line2.set_data(*zip(*data2))

            data3.append((x, y3))
            axs[3].relim()
            axs[3].autoscale_view()
            line3.set_data(*zip(*data3))

            plt.show()
            plt.pause(plot_interval)
        # plt.show()


async def main():
    stop_event = asyncio.Event()
    try:
        await live_plots(
            chassis=CHASSIS_IP,
            username=USERNAME,
            tx_port_str=TX_PORT,
            rx_port_str=RX_PORT,
            ecn11_filter_idx=ECN11_FILTER_IDX,
            ecn10_filter_idx=ECN10_FILTER_IDX,
            figure_title=FIGURE_TITLE,
            duration=DURATION,
            win_size=WINDOW_SIZE,
            plot_interval=PLOTTING_INTERVAL
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
