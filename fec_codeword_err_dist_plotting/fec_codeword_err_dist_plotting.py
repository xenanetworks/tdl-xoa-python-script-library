################################################################
#
#                   FEC CODEWORD ERROR DISTRIBUTION PLOT
#
# Prerequisites:
# 1. Use GUI to configure the module media and port speed (the script doesn't configure it)
#
# What this script example does:
# 1. Monitor and plot the FEC Codeword Error Distribution (log10) in real time for all ports on a module.
# 2. The plot is refreshed every N seconds for a total of M seconds.
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
from decimal import Decimal, ROUND_HALF_UP

import matplotlib.pyplot as plt
import numpy as np
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.153.50"
TCP_PORT = 22606
USERNAME = "xoa"
MODULE = "10"
FIGURE_TITLE = "FEC Codeword Error Distribution (log10)"
PLOTTING_INTERVAL = 1 # Plot is refreshed every N seconds
PLOTTING_DURATION = 120 # Plotting duration in M seconds

# Enable the FEC mode you want
FEC_MODE = enums.FECMode.ON # either RS FEC KR or KP. Determined by the port automatically
# FEC_MODE = enums.FECMode.FC_FEC
# FEC_MODE = enums.FECMode.RS_FEC_INT
        
#---------------------------
# fec_codeword_err_dist_plotting
#---------------------------
async def fec_codeword_err_dist_plotting(
        chassis: str,
        tcp_port: int,
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
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=tcp_port, enable_logging=False) as tester:
        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}:{tcp_port}")
        logging.info(f"Username:                {username}")
        logging.info(f"Module:                  {module_str}")
        logging.info(f"Figure Title:            {figure_title}")
        logging.info(f" Plot Refresh Interval:   {plotting_interval} s")
        logging.info(f" Plot Duration:           {plotting_duration} s")
        logging.info(f"#####################################################################")

        # Access module on the tester
        module_objs = await mgmt.obtain_modules_by_ids(tester=tester, module_ids=[module_str])
        module_obj = module_objs[0]
        
        if not isinstance(module_obj, (modules.Z100LokiModule, modules.Z400ThorModule, modules.Z800FreyaModule)):
            logging.info(f"The module must be a L23 module")
            logging.info(f"Abort")
            return None
        
        # reserve all ports on a module
        port_objs = await mgmt.obtain_ports_by_ids(tester=tester, port_ids=[f"{module_str}/*"])
        port_cnt = len(port_objs)

        # Forcibly reserve the port
        await mgmt.release_modules(modules=[module_obj], should_release_ports=False)
        resp = await module_obj.revision.get() # type: ignore
        module_module_name = resp.revision
        await mgmt.reserve_ports(ports=list(port_objs), reset=True)
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
            pre_fec_subplots.append(fig.add_subplot(gs[i%gs.nrows, int(i/gs.nrows)])) # type: ignore

        # set x and y label for each subplot
        for i in range(port_cnt):
            pre_fec_subplots[i].set(xlabel=f"Symbol Errors", ylabel=f"FEC Codewords ({module_str}/{i}) (log10)")

        # set FEC mode on
        logging.info(f"Set FEC Mode = {fec_mode.name}")
        for p in port_objs:
            await p.layer1.pcs.fec_mode.set(mode=fec_mode) # type: ignore

        # clear FEC counter
        logging.info(f"Clear FEC counter")
        for p in port_objs:
            await p.layer1.pcs.clear.set() # type: ignore

        # query FEC Totals and Pre-FEC Error Distribution
        plot_count = math.ceil(plotting_duration/plotting_interval)
        pre_fec_error_dist_data = [[0]*17]*port_cnt
        print(len(pre_fec_subplots))
        for _ in range(plot_count):
            logging.info(f"PRE-FEC ERROR DISTRIBUTION")
            for i in range(port_cnt):
                port_obj = port_objs[i]
                logging.info(f"Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
                _total_status, _fec_status = await utils.apply(
                    port_obj.layer1.pcs.fec_symbol_status.total_status.get(), # type: ignore
                    port_obj.layer1.pcs.fec_symbol_status.fec_status.get() # type: ignore
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
                    _pre_fec_ber = 0
                    pre_fec_ber_str = f"Pre-FEC BER = {_pre_fec_ber}"
                else:
                    _pre_fec_ber = abs(1/_total_status.total_pre_fec_ber)
                    pre_fec_ber_str = f"Pre-FEC BER = {_pre_fec_ber}"

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
                print(pre_fec_error_dist_data_log10)
                tmp = pre_fec_subplots[i].bar(x=x_axis, height=pre_fec_error_dist_data_log10, color=color_array,)
                pre_fec_subplots[i].bar_label(container=tmp, fmt='%.1f')
                x0, xmax = pre_fec_subplots[i].get_xbound()
                y0, ymax = pre_fec_subplots[i].get_ybound()

                pre_fec_subplots[i].text((x0+xmax)*0.7, (y0+ymax)*0.9, pre_fec_ber_str, fontsize="small")

            plt.show()
            logging.info(f"Clear FEC counter")
            for p in port_objs:
                await p.layer1.pcs.clear.set() # type: ignore
            plt.pause(plotting_interval)
            


async def main():
    stop_event = asyncio.Event()
    try:
        await fec_codeword_err_dist_plotting(
            chassis=CHASSIS_IP,
            tcp_port=TCP_PORT,
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
