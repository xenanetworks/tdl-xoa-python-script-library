################################################################
#
#              SIGNAL INTEGRITY SAMPLE PLOTTING
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. 
# 3. Collecting SIV data from all 8 lanes
# 4. Plot the live sample data 
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
import math
from typing import List

import matplotlib.pyplot as plt
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
PORT = "6/0"
FIGURE_TITLE = "Z800 Freya Signal Integrity Sample Plot"
DENSITY = 1 # how many batches of siv data to show on the plot. A higher density means more data and slower plotting.
LANES = [0,1,2,3,4,5,6,7] # select lanes to display, ranging from 0 to 7
PLOTTING_INTERVAL = 1 # plots refreshed every n second
PLOTTING_DURATION = 120 # number of seconds for plotting

async def siv_plot(
        chassis: str, 
        username: str, 
        port_str: str,
        figure_title: str,
        density: int,
        plotting_interval: int,
        plotting_duration: int,
        lanes: List[int],
        ):
    
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="siv_plot.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # disable matplotlib.font_manager logging
    logging.getLogger('matplotlib.font_manager').disabled = True

    # remove duplicates and sort list
    lanes = list(set(lanes))
    lanes.sort()
    
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Lanes:                   {lanes}")
        logging.info(f"Figure Title:            {figure_title}")
        logging.info(f" Data Density:            {density}")
        logging.info(f" Plot Refresh Interval:   {plotting_interval} s")
        logging.info(f" Plot Duration:           {plotting_duration} s")
        logging.info(f"#####################################################################")

        # Access module on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        if not isinstance(module_obj, modules.Z800FreyaModule):
            logging.info(f"Module {_mid} is not Z800 Freya module. Abort.")
            return None
        
        port_obj = module_obj.ports.obtain(_pid)
        await mgmt.free_module(module=module_obj, should_free_ports=False)
        await mgmt.reserve_port(port_obj)

        resp = await port_obj.capabilities.get()
        max_serdes = resp.serdes_count
        serdes_cnt_to_show = len(lanes)
        if max(lanes) > 7:
            logging.warning(f"Exceed max serdes index. Abort.")
            return None
        if serdes_cnt_to_show > max_serdes:
            logging.warning(f"Exceed max serdes count. Abort.")
            return None
        if serdes_cnt_to_show == 0:
            logging.warning(f"Nothing to show Abort.")
            return None

        # figure config
        plt.ion()
        fig = plt.figure(constrained_layout=True)
        fig.suptitle(f"{figure_title}\nChassis {chassis}, Port {port_str}, L={lanes}, D={density}")

        # grid spec
        if serdes_cnt_to_show == 1:
            gs = fig.add_gridspec(nrows=1, ncols=1)
        if serdes_cnt_to_show > 1:
            gs = fig.add_gridspec(nrows=math.ceil(serdes_cnt_to_show/2), ncols=2)

        # add subplots
        siv_subplots = []
        for i in range(serdes_cnt_to_show):
            siv_subplots.append(fig.add_subplot(gs[i%gs.nrows, int(i/gs.nrows)]))
        
        # data dequeue for each serdes lane. queue depth = density*2000
        INT_CNT_PER_DATA = 2000
        data_queue = []
        for _ in range(serdes_cnt_to_show):
            data_queue.append(deque((), maxlen=density*INT_CNT_PER_DATA))

        # set x and y label for each subplot
        for i in range(serdes_cnt_to_show):
            siv_subplots[i].set(xlabel=f"Value", ylabel=f"Lane {lanes[i]}")
        
        # group control commands for each serdes lane together to later send it as a command group.
        control_cmd_group = []
        for i in range(serdes_cnt_to_show):
            control_cmd_group.append(port_obj.l1.serdes[lanes[i]].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN))
        
        # get commands for each serdes lane together to later send it as a command group.
        get_cmd_group = []
        for i in range(serdes_cnt_to_show):
            get_cmd_group.append(port_obj.l1.serdes[lanes[i]].medium.siv.data.get())

        resp_group = ()
        plot_count = math.ceil(plotting_duration/plotting_interval)
        for _ in range(plot_count):
            await utils.apply(*control_cmd_group)
            while True:
                # get responses from all lanes
                resp_group = await utils.apply(*get_cmd_group)
                result_flags = [x.result for x in resp_group]
                if 0 in result_flags:
                    # if not all lanes are ready in data, query again.
                    continue
                else:
                    for i in range(serdes_cnt_to_show):
                        siv_raw_levels = resp_group[i].value[0:12]
                        siv_raw_values = resp_group[i].value[12:]

                        # convert from 12 raw bytes into 6 signed int
                        siv_int_levels = []
                        for x in zip(siv_raw_levels[0::2], siv_raw_levels[1::2]):
                            siv_int_levels.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                        # Please note: only the first slicer data is used here.

                        # convert from 4000 bytes into 2000 signed int
                        siv_int_values = []
                        for x in zip(siv_raw_values[0::2], siv_raw_values[1::2]):
                            siv_int_values.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                        # put value data in queue
                        data_queue[i].extend(tuple(siv_int_values))

                        # siv data ranges from -64 to 63, thus 128 bins in total.
                        siv_subplots[i].cla()
                        siv_subplots[i].relim()
                        siv_subplots[i].autoscale_view()
                        siv_subplots[i].set(xlabel=f"Value", ylabel=f"Lane {lanes[i]}")
                        siv_subplots[i].plot([*data_queue[i]], 'bs')

                        # levels contains 6 values, 4 average pam4 levels and 2 slicers, (<p1> <p2> <p3> <m1> <m2> <m3>)
                        # add base slicer (this is always at 0)
                        y = 0
                        siv_subplots[i].axhline(y, color='black', linestyle='-', linewidth=0.5)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'base={y}', fontsize="small")
                        # add upper slicer <p2>
                        y = siv_int_levels[1]
                        siv_subplots[i].axhline(y, color='green', linestyle='dashed', linewidth=0.5)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'slicer={y}', fontsize="small")
                        # add lower slicer <m2>
                        y = siv_int_levels[4]
                        siv_subplots[i].axhline(y, color='green', linestyle='dashed', linewidth=0.5)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'slicer={y}', fontsize="small")
                        # add average level 3 <p3>
                        y = siv_int_levels[2]
                        siv_subplots[i].axhline(y, color='black', linestyle='dashed', linewidth=0.1)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'level3={y}', fontsize="small")
                        # add average level 2 <p1>
                        y = siv_int_levels[0]
                        siv_subplots[i].axhline(y, color='black', linestyle='dashed', linewidth=0.1)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'level2={y}', fontsize="small")
                        # add average level 1 <m3>
                        y = siv_int_levels[5]
                        siv_subplots[i].axhline(y, color='black', linestyle='dashed', linewidth=0.1)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'level1={y}', fontsize="small")
                        # add average level 0 <m1>
                        y = siv_int_levels[3]
                        siv_subplots[i].axhline(y, color='black', linestyle='dashed', linewidth=0.1)
                        siv_subplots[i].text(siv_subplots[i].get_xlim()[1] + 0.1, y, f'level0={y}', fontsize="small")
                        

                    plt.show()
                    plt.pause(plotting_interval)
                    break
        
        await mgmt.free_port(port_obj)
        logging.info(f"Bye!")

async def main():
    stop_event = asyncio.Event()
    try:
        await siv_plot(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            figure_title=FIGURE_TITLE,
            density=DENSITY,
            plotting_interval=PLOTTING_INTERVAL,
            plotting_duration = PLOTTING_DURATION,
            lanes=LANES
            )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())