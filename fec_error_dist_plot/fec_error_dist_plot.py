################################################################
#
#                   PRE-FEC ERROR DIST PLOT
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. Must be Freya, Thor, or Loki
# 3. Set the port FEC mode on
# 4. Clear FEC stats
# 5. Query FEC Blocks (symbol error) and FEC stats
# 6. Plot the Pre-FEC error distribution
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
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
PORT = "3/0"
FIGURE_TITLE = "Pre-FEC Error Distribution Plot"
PLOTTING_INTERVAL = 1 # plots refreshed every n second
PLOTTING_DURATION = 120 # number of seconds for plotting
        
#---------------------------
# pre_fec_error_dist_plot
#---------------------------
async def pre_fec_error_dist_plot(
        chassis: str,
        username: str,
        port_str: str,
        figure_title: str,
        plotting_interval: int,
        plotting_duration: int,
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
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Figure Title:            {figure_title}")
        logging.info(f" Plot Refresh Interval:   {plotting_interval} s")
        logging.info(f" Plot Duration:           {plotting_duration} s")
        logging.info(f"#####################################################################")

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

        await asyncio.sleep(1)
        
        # figure config
        plt.ion()
        fig = plt.figure(constrained_layout=True)
        fig.suptitle(f"{figure_title}")
        
        # grid spec: 1 rows and 1 column
        gs = fig.add_gridspec(nrows=1, ncols=1)

        # add subplots
        pre_fec_dist_plot = fig.add_subplot(gs[0,0])

        # set x and y label for each subplot
        pre_fec_dist_plot.set(xlabel=f"Symbol Errors", ylabel=f"FEC Codewords")

        # set FEC mode on
        logging.info(f"Set FEC Mode = ON")
        await port_obj.fec_mode.set(mode=enums.FECMode.ON)

        # clear FEC counter
        logging.info(f"Clear FEC counter")
        await port_obj.pcs_pma.rx.clear.set()

        # query FEC Totals and Pre-FEC Error Distribution
        plot_count = math.ceil(plotting_duration/plotting_interval)
        pre_fec_error_dist_data = [0]*17
        for _ in range(plot_count):
            _total_status, _fec_status = await utils.apply(
                port_obj.pcs_pma.rx.total_status.get(),
                port_obj.pcs_pma.rx.fec_status.get()
            )
            logging.info(f"PRE-FEC ERROR DISTRIBUTION")
            n = _fec_status.data_count - 2
            for i in range(n):
                logging.info(f"  FEC Blocks (Symbol Errors = {i}): {_fec_status.stats[i]}")
            logging.info(f"  FEC Blocks (Symbol Errors > {n-1}): {_fec_status.stats[n]}")
            
            x_axis = [str(x) for x in range(n)]
            x_axis.append(f"> {n-1}")
            color_array = ['y']*(n-1)
            color_array.insert(0, 'g')
            color_array.append('r')

            pre_fec_error_dist_data = [x + y for x, y in zip(pre_fec_error_dist_data, _fec_status.stats[0:n+1])] 

            pre_fec_dist_plot.relim()
            pre_fec_dist_plot.autoscale_view()
            print(x_axis)
            print(pre_fec_error_dist_data)
            tmp = pre_fec_dist_plot.bar(x=x_axis, height=pre_fec_error_dist_data, color=color_array)
            # pre_fec_dist_plot.bar_label(container=tmp, fmt='%e')
            # for i in range(len(pre_fec_error_dist_data)):
            #     pre_fec_dist_plot.text(x=i, y=pre_fec_error_dist_data[i], s="{:e}".format(pre_fec_error_dist_data[i]))

            logging.info(f"{_total_status}")
            logging.info(f"FEC TOTALS")
            logging.info(f"  Total RX Bits:                 {_total_status.total_rx_bit_count}")
            logging.info(f"  Total RX Codewords:            {_total_status.total_rx_codeword_count}")
            logging.info(f"  Total Corrected Codewords:     {_total_status.total_corrected_codeword_count}")
            logging.info(f"  Total Uncorrectable Codewords: {_total_status.total_uncorrectable_codeword_count}")
            logging.info(f"  Total Corrected Symbols:       {_total_status.total_corrected_symbol_count}")
            if _total_status.total_pre_fec_ber == -1:
                logging.info(f"  Total Pre-FEC BER:             N/A")
            elif _total_status.total_pre_fec_ber == 0:
                logging.info(f"  Total Pre-FEC BER:             0")
            elif _total_status.total_pre_fec_ber < 0:
                logging.info(f"  Total Pre-FEC BER:             < {abs(1/_total_status.total_pre_fec_ber)}")
            else:
                logging.info(f"  Total Post-FEC BER:            {1/_total_status.total_pre_fec_ber}")
            if _total_status.total_post_fec_ber == -1:
                logging.info(f"  Total Post-FEC BER:            N/A")
            elif _total_status.total_post_fec_ber == 0:
                logging.info(f"  Total Post-FEC BER:            0")
            elif _total_status.total_post_fec_ber < 0:
                logging.info(f"  Total Post-FEC BER:            < {abs(1/_total_status.total_post_fec_ber)}")
            else:
                logging.info(f"  Total Post-FEC BER:            {1/_total_status.total_post_fec_ber}")

            plt.show()
            plt.pause(plotting_interval)


async def main():
    stop_event = asyncio.Event()
    try:
        await pre_fec_error_dist_plot(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            figure_title=FIGURE_TITLE,
            plotting_interval=PLOTTING_INTERVAL,
            plotting_duration=PLOTTING_DURATION
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
