################################################################
#
#                   FEC STATS
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. Must be Freya, Thor, or Loki
# 3. Reset the port
# 4. Set the port FEC mode on
# 5. Clear FEC stats
# 6. Query FEC Blocks (symbol error) and FEC stats
# 7. Write the stats into csv file (csv example: fec_stats.csv)
# 8. logging.info the stats out
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

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.30.60"
USERNAME = "xoa"
PORT = "3/1"
        
#---------------------------
# fec_stats
#---------------------------
async def fec_stats(chassis: str, username: str, port_str: str):
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
        await mgmt.reset_port(port_obj)

        await asyncio.sleep(5)

        # set FEC mode on
        await port_obj.fec_mode.set(mode=enums.FECMode.ON)

        await port_obj.pcs_pma.rx.clear.set()
        _fec_status = await port_obj.pcs_pma.rx.fec_status.get()
        n = _fec_status.data_count - 2
        field = ["time"]
        for i in range(n):
            field.append(f"FEC Blocks (Symbol Errors = {i})")
        field.append(f"FEC Blocks (Symbol Errors > {n-1})")
        field.append("total_rx_bit_count")
        field.append("total_rx_codeword_count")
        field.append("total_corrected_codeword_count")
        field.append("total_uncorrectable_codeword_count")
        field.append("total_corrected_symbol_count")
        field.append("total_pre_fec_ber")
        field.append("total_post_fec_ber")

        with open('fec_stats.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(field)
            while True:
                dat = []
                dat.append(time.time())
                _total_status, _fec_status = await utils.apply(
                    port_obj.pcs_pma.rx.total_status.get(),
                    port_obj.pcs_pma.rx.fec_status.get()
                )
                logging.info(f"{_fec_status.data_count}")
                logging.info(f"{_fec_status.stats}")
                logging.info(f"{_total_status}")
                n = _fec_status.data_count - 2
                for i in range(n):
                    dat.append(_fec_status.stats[i])
                    logging.info(f"FEC Blocks (Symbol Errors = {i}): {_fec_status.stats[i]}")
                logging.info(f"FEC Blocks (Symbol Errors > {n-1}): {_fec_status.stats[n]}")
                dat.append(_fec_status.stats[n])
                dat.append(_total_status.total_rx_bit_count)
                dat.append(_total_status.total_rx_codeword_count)
                dat.append(_total_status.total_corrected_codeword_count)
                dat.append(_total_status.total_uncorrectable_codeword_count)
                dat.append(_total_status.total_corrected_symbol_count)
                if _total_status.total_pre_fec_ber == 0:
                    dat.append(0)
                else:
                    dat.append(abs(1/_total_status.total_pre_fec_ber))
                if _total_status.total_post_fec_ber == 0:
                    dat.append(0)
                else:
                    dat.append(abs(1/_total_status.total_post_fec_ber))
                writer.writerow(dat)
                logging.info(f"total_rx_bit_count: {_total_status.total_rx_bit_count}")
                logging.info(f"total_rx_codeword_count: {_total_status.total_rx_codeword_count}")
                logging.info(f"total_corrected_codeword_count: {_total_status.total_corrected_codeword_count}")
                logging.info(f"total_uncorrectable_codeword_count: {_total_status.total_uncorrectable_codeword_count}")
                logging.info(f"total_corrected_symbol_count: {_total_status.total_corrected_symbol_count}")
                if _total_status.total_pre_fec_ber == 0:
                    logging.info(f"total_pre_fec_ber: 0")
                elif _total_status.total_pre_fec_ber == -1:
                    logging.info(f"total_pre_fec_ber: N/A")
                else:
                    logging.info(f"total_pre_fec_ber: {abs(1/_total_status.total_pre_fec_ber)}")
                if _total_status.total_post_fec_ber == 0:
                    logging.info(f"total_post_fec_ber: 0")
                elif _total_status.total_post_fec_ber == 0:
                    logging.info(f"total_post_fec_ber: N/A")
                else:
                    logging.info(f"total_post_fec_ber: {abs(1/_total_status.total_post_fec_ber)}")
                await asyncio.sleep(1)

async def main():
    stop_event = asyncio.Event()
    try:
        await fec_stats(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
