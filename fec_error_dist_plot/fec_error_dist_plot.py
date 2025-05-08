################################################################
#
#                   PRE-FEC ERROR DIST PLOT
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a all ports on a module
# 3. Set the port FEC mode on
# 4. Clear FEC stats
# 5. Query FEC Blocks (symbol error) and FEC stats
# 6. Plot the Pre-FEC error distribution for all ports
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

import matplotlib.pyplot as plt
import numpy as np
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.66"
USERNAME = "xoa"
MODULE = "4"
FIGURE_TITLE = "Pre-FEC Error Distribution Plot (log10)"
PLOTTING_INTERVAL = 1 # plots refreshed every n second
PLOTTING_DURATION = 120 # number of seconds for plotting

# Enable the FEC mode you want
FEC_MODE = enums.FECMode.ON # either RS FEC KR or KP. Determined by the port automatically
# FEC_MODE = enums.FECMode.FC_FEC
# FEC_MODE = enums.FECMode.RS_FEC_INT
        
#---------------------------
# pre_fec_error_dist_plot
#---------------------------
async def pre_fec_error_dist_plot(
        chassis: str,
        username: str,
        module_str: str,
        figure_title: str,
        plotting_interval: int,
        plotting_duration: int,
        fec_mode: enums.FECMode
        ):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="fec_plot.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # disable matplotlib.font_manager logging
    logging.getLogger('matplotlib.font_manager').disabled = True

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {module_str}")
        logging.info(f"Figure Title:            {figure_title}")
        logging.info(f" Plot Refresh Interval:   {plotting_interval} s")
        logging.info(f" Plot Duration:           {plotting_duration} s")
        logging.info(f"#####################################################################")

        # Access module on the tester
        _mid = int(module_str)
        module_obj = tester.modules.obtain(_mid)

        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.info(f"FEC not supported on E100 Chimera modules")
            return None
        
        if isinstance(module_obj, modules.Z10OdinModule):
            logging.info(f"FEC not supported on Z10 Odin modules")
            return None 
        
        # reserve all ports on a module
        port_objs = [x for x in module_obj.ports]
        port_cnt = len(port_objs)

        # Forcibly reserve the port
        await mgmt.release_module(module=module_obj, should_release_ports=False)
        resp = await module_obj.revision.get()
        module_module_name = resp.revision
        for p in port_objs:
            await mgmt.reserve_port(p)

        await asyncio.sleep(1)
        
        # figure config
        plt.ion()
        fig = plt.figure(constrained_layout=True)
        fig.suptitle(f"{figure_title}\nChassis {chassis}, Module {module_str}, {module_module_name}")
        
        # grid spec
        if port_cnt == 1:
            gs = fig.add_gridspec(nrows=1, ncols=1)
        if port_cnt > 1:
            gs = fig.add_gridspec(nrows=math.ceil(port_cnt/2), ncols=2)

        # add subplots
        pre_fec_subplots = []
        for i in range(port_cnt):
            pre_fec_subplots.append(fig.add_subplot(gs[i%gs.nrows, int(i/gs.nrows)]))

        # set x and y label for each subplot
        for i in range(port_cnt):
            pre_fec_subplots[i].set(xlabel=f"Symbol Errors", ylabel=f"FEC Codewords ({module_str}/{i}) (log10)")

        # set FEC mode on
        logging.info(f"Set FEC Mode = {fec_mode.name}")
        for p in port_objs:
            await p.fec_mode.set(mode=fec_mode)

        # clear FEC counter
        logging.info(f"Clear FEC counter")
        for p in port_objs:
            await p.pcs_pma.rx.clear.set()

        # query FEC Totals and Pre-FEC Error Distribution
        plot_count = math.ceil(plotting_duration/plotting_interval)
        pre_fec_error_dist_data = [[0]*17]*port_cnt
        print(len(pre_fec_subplots))
        for _ in range(plot_count):
            logging.info(f"PRE-FEC ERROR DISTRIBUTION")
            for i in range(port_cnt):
                port_obj = port_objs[i]
                logging.info(f"Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
                # await port_obj.pcs_pma.rx.clear.set()
                _total_status, _fec_status = await utils.apply(
                    port_obj.pcs_pma.rx.total_status.get(),
                    port_obj.pcs_pma.rx.fec_status.get()
                )
                n = _fec_status.data_count - 2
                for j in range(n):
                    logging.info(f"  FEC Blocks (Symbol Errors = {j}): {_fec_status.stats[j]}")
                logging.info(f"  FEC Blocks (Symbol Errors > {n-1}): {_fec_status.stats[n]}")
                
                x_axis = [str(x) for x in range(n)]
                x_axis.append(f"> {n-1}")
                color_array = ['y']*(n-1)
                color_array.insert(0, 'g')
                color_array.append('r')

                pre_fec_error_dist_data[i] = [x + y for x, y in zip(pre_fec_error_dist_data[i], _fec_status.stats[0:n+1])]
                pre_fec_ber_str = ""
                if _total_status.total_pre_fec_ber == 0:
                    pre_fec_ber_str = f"Pre-FEC BER = 0"
                else:
                    pre_fec_ber_str = f"Pre-FEC BER = {abs(1/_total_status.total_pre_fec_ber)}"

                pre_fec_subplots[i].cla()
                pre_fec_subplots[i].relim()
                pre_fec_subplots[i].autoscale_view()
                pre_fec_subplots[i].set(xlabel=f"Symbol Errors", ylabel=f"FEC Codewords ({module_str}/{i})")
                pre_fec_error_dist_data_log10 = []
                for x in pre_fec_error_dist_data[i]:
                    if x > 0:
                        pre_fec_error_dist_data_log10.append(np.log10(x))
                    else:
                        pre_fec_error_dist_data_log10.append(0)
                # print(pre_fec_error_dist_data_log10)
                tmp = pre_fec_subplots[i].bar(x=x_axis, height=pre_fec_error_dist_data_log10, color=color_array,)
                pre_fec_subplots[i].bar_label(container=tmp, fmt='%.1f')
                x0, xmax = pre_fec_subplots[i].get_xbound()
                y0, ymax = pre_fec_subplots[i].get_ybound()

                pre_fec_subplots[i].text((x0+xmax)*0.7, (y0+ymax)*0.9, pre_fec_ber_str, fontsize="small")

            plt.show()
            logging.info(f"Clear FEC counter")
            for p in port_objs:
                await p.pcs_pma.rx.clear.set()
            plt.pause(plotting_interval)
            


async def main():
    stop_event = asyncio.Event()
    try:
        await pre_fec_error_dist_plot(
            chassis=CHASSIS_IP,
            username=USERNAME,
            module_str=MODULE,
            figure_title=FIGURE_TITLE,
            plotting_interval=PLOTTING_INTERVAL,
            plotting_duration=PLOTTING_DURATION,
            fec_mode=FEC_MODE
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
