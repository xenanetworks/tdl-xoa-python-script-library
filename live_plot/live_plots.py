################################################################
#
#                   LIVE PLOTTING
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve three ports. Must not be Chimera or Odin.
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
import logging

import matplotlib.pyplot as plt
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
TX_PORT_1 = "3/0"
TX_PORT_2 = "3/1"
RX_PORT = "6/0"
DURATION = 3600
ECN11_FILTER_IDX = 0
ECN10_FILTER_IDX = 2
WINDOW_SIZE = 60
PLOTTING_INTERVAL = 2.0

FIGURE_TITLE = "XenaManager Displaying Traffic and PFC on Z800 Freya"

#---------------------------
# live_plot
#---------------------------
async def live_plots(
        chassis: str, 
        username: str, 
        tx_port_str_1: str, 
        tx_port_str_2: str,
        rx_port_str: str, 
        ecn11_filter_idx: int, 
        ecn10_filter_idx: int, 
        figure_title: str, 
        duration: int, 
        win_size: int, 
        plot_interval: float):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="live_plots.log", mode="a"),
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
        logging.info(f"RX Port:                 {rx_port_str}")
        logging.info(f"  ECN 10 Filter Index:   {ecn10_filter_idx}")
        logging.info(f"  ECN 11 Filter Index:   {ecn11_filter_idx}")
        logging.info(f"Figure Title:            {figure_title}")
        logging.info(f"Plot Duration:           {duration} sec")
        logging.info(f"Plot Windows:            {win_size} sec")
        logging.info(f"Plot Refresh Interval:   {plot_interval} sec")

        # Access module on the tester
        _mid_rx = int(rx_port_str.split("/")[0])
        _pid_rx = int(rx_port_str.split("/")[1])
        rx_module_obj = tester.modules.obtain(_mid_rx)
        _mid_tx_1 = int(tx_port_str_1.split("/")[0])
        _pid_tx_1 = int(tx_port_str_1.split("/")[1])
        tx_module_obj_1 = tester.modules.obtain(_mid_tx_1)
        _mid_tx_2 = int(tx_port_str_2.split("/")[0])
        _pid_tx_2 = int(tx_port_str_2.split("/")[1])
        tx_module_obj_2 = tester.modules.obtain(_mid_tx_2)

        if isinstance(rx_module_obj, modules.E100ChimeraModule) or isinstance(rx_module_obj, modules.Z10OdinModule):
            logging.info(f"Module {_mid_rx} must not be Chimera or Odin")
            return None
        
        if isinstance(tx_module_obj_1, modules.E100ChimeraModule) or isinstance(tx_module_obj_1, modules.Z10OdinModule):
            logging.info(f"Module {_mid_tx_1} must not be Chimera or Odin")
            return None
        
        if isinstance(tx_module_obj_2, modules.E100ChimeraModule) or isinstance(tx_module_obj_2, modules.Z10OdinModule):
            logging.info(f"Module {_mid_tx_2} must not be Chimera or Odin")
            return None

        # Get the ports
        rx_port_obj = rx_module_obj.ports.obtain(_pid_rx)
        tx_port_obj_1 = tx_module_obj_1.ports.obtain(_pid_tx_1)
        tx_port_obj_2 = tx_module_obj_2.ports.obtain(_pid_tx_2)

        # Forcibly reserve the port
        await mgmt.free_module(module=rx_module_obj, should_free_ports=False)
        await mgmt.reserve_port(rx_port_obj)
        await mgmt.free_module(module=tx_module_obj_1, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj_1)
        await mgmt.free_module(module=tx_module_obj_2, should_free_ports=False)
        await mgmt.reserve_port(tx_port_obj_2)

        # Sync the filters from chassis to script
        await asyncio.sleep(1)
        await rx_port_obj.filters.server_sync()
        # Get filter's description
        ecn11_filter = rx_port_obj.filters.obtain(ecn11_filter_idx)
        resp = await ecn11_filter.comment.get()
        ecn11_filter_description = resp.comment
        ecn10_filter = rx_port_obj.filters.obtain(ecn10_filter_idx)
        resp = await ecn10_filter.comment.get()
        ecn10_filter_description = resp.comment
        await tx_port_obj_1.streams.server_sync()
        await tx_port_obj_2.streams.server_sync()
        s = tx_port_obj_1.streams.obtain(0)
        resp = await s.packet.length.get()
        factor = (resp.min_val+20)/resp.min_val

        logging.info(f"Packet Size:             {resp.min_val} bytes")
        logging.info(f"#####################################################################")

        # live plotting
        x = 0       # time axis
        y0 = 0      # traffic rate for tx port 1
        y1 = 0      # pfc for tx port 1
        y2 = 0      # ecn 11 for rx port
        y3 = 0      # ecn 10 for rx port
        y4 = 0      # traffic rate for tx port 2
        y5 = 0      # pfc for tx port 2

        plt.ion()

        fig = plt.figure()
        gs = fig.add_gridspec(nrows=4, ncols=2, hspace=0)
        ax0 = fig.add_subplot(gs[0, 0])  # traffic rate for tx port 1
        ax1 = fig.add_subplot(gs[1, 0])  # pfc for tx port 1
        ax2 = fig.add_subplot(gs[2, 0])  # ecn 11 for rx port
        ax3 = fig.add_subplot(gs[3, 0])  # ecn 10 for rx port
        ax4 = fig.add_subplot(gs[0, 1])  # traffic rate for tx port 2
        ax5 = fig.add_subplot(gs[1, 1])  # pfc for tx port 2
        ax6 = fig.add_subplot(gs[2, 1])  # ecn 11 for rx port
        ax7 = fig.add_subplot(gs[3, 1])  # ecn 10 for rx port
        # axs = gs.subplots(sharex=True)

        fig.suptitle(figure_title)
        
        data0 = deque([(x, y0)], maxlen=win_size) # traffic rate for tx port 1
        data1 = deque([(x, y1)], maxlen=win_size) # pfc for tx port 1
        data2 = deque([(x, y2)], maxlen=win_size) # ecn 11 for rx port
        data3 = deque([(x, y3)], maxlen=win_size) # ecn 10 for rx port
        data4 = deque([(x, y4)], maxlen=win_size) # traffic rate for tx port 2
        data5 = deque([(x, y5)], maxlen=win_size) # pfc for tx port 2

        line0, = ax0.step(*zip(*data0), c='black') # traffic rate for tx port 1
        line1, = ax1.step(*zip(*data1), c='blue') # pfc for tx port 1
        line2, = ax2.step(*zip(*data2), c='red') # ecn 11 for rx port
        line3, = ax3.step(*zip(*data3), c='blue') # ecn 10 for rx port
        line4, = ax4.step(*zip(*data4), c='black') # traffic rate for tx port 2
        line5, = ax5.step(*zip(*data5), c='blue') # pfc for tx port 2
        line6, = ax6.step(*zip(*data2), c='red') # ecn 11 for rx port
        line7, = ax7.step(*zip(*data3), c='blue') # ecn 10 for rx port

        ax0.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"Traffic Rate Mbps ({tx_port_str_1})")
        ax1.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"PFC Count ({tx_port_str_1})")
        ax2.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"{ecn11_filter_description} ({rx_port_str})")
        ax3.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"{ecn10_filter_description} ({rx_port_str})")

        ax4.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"Traffic Rate Mbps ({tx_port_str_2})")
        ax5.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"PFC Count ({tx_port_str_2})")
        ax6.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"{ecn11_filter_description} ({rx_port_str})")
        ax7.set(xlabel=f"Time ({plot_interval}s)", ylabel=f"{ecn10_filter_description} ({rx_port_str})")
        
        await rx_port_obj.statistics.rx.clear.set()
        await tx_port_obj_1.statistics.rx.clear.set()
        await tx_port_obj_2.statistics.rx.clear.set()

        for i in range(duration):
            x = i
            resp0, resp1, resp2, resp3, resp4, resp5 = await asyncio.gather(
                tx_port_obj_1.statistics.tx.total.get(), # Read tx port 1 total rate
                tx_port_obj_1.statistics.rx.pfc_stats.get(), # Read pfc packet count on the tx port 1
                rx_port_obj.statistics.rx.obtain_filter_statistics(filter=ecn11_filter_idx).get(), # Read the filtered traffic stats - packet count since cleared
                rx_port_obj.statistics.rx.obtain_filter_statistics(filter=ecn10_filter_idx).get(), # Read the filtered traffic stats - packet count since cleared
                tx_port_obj_2.statistics.tx.total.get(), # Read tx port 2 total rate
                tx_port_obj_2.statistics.rx.pfc_stats.get(), # Read pfc packet count on the tx port 2
            )

            y0 = resp0.bit_count_last_sec/1_000_000*factor
            y1 = resp1.packet_count
            y2 = resp2.packet_count_since_cleared
            y3 = resp3.packet_count_since_cleared
            y4 = resp4.bit_count_last_sec/1_000_000*factor
            y5 = resp5.packet_count

            data0.append((x, y0))
            ax0.relim()
            ax0.autoscale_view()
            line0.set_data(*zip(*data0))

            data1.append((x, y1))
            ax1.relim()
            ax1.autoscale_view()
            line1.set_data(*zip(*data1))

            data2.append((x, y2))
            ax2.relim()
            ax2.autoscale_view()
            line2.set_data(*zip(*data2))

            data3.append((x, y3))
            ax3.relim()
            ax3.autoscale_view()
            line3.set_data(*zip(*data3))

            data4.append((x, y4))
            ax4.relim()
            ax4.autoscale_view()
            line4.set_data(*zip(*data4))

            data5.append((x, y5))
            ax5.relim()
            ax5.autoscale_view()
            line5.set_data(*zip(*data5))

            ax6.relim()
            ax6.autoscale_view()
            line6.set_data(*zip(*data2))

            ax7.relim()
            ax7.autoscale_view()
            line7.set_data(*zip(*data3))

            plt.show()
            plt.pause(plot_interval)
        # plt.show()


async def main():
    stop_event = asyncio.Event()
    try:
        await live_plots(
            chassis=CHASSIS_IP,
            username=USERNAME,
            tx_port_str_1=TX_PORT_1,
            tx_port_str_2=TX_PORT_2,
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
