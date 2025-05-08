################################################################
#
#                   Z800 FREYA TX TAP TUNING
#
# This script show you how to adjust the TX tap values on Z800
# Freya modules.
# 
# There are 3 ways to adjust the TX taps:
# 1. Using the native values that has no unit (NATIVE).
# 2. Using the mV/dB values (LEVEL).
# 3. Using the IEEE coefficient values (IEEE).
# 
# Changing the taps using either of the 3 methods will update 
# the corresponding values of the other 2.
#
################################################################

import asyncio
from xoa_driver import testers, modules, ports, enums
from typing import Generator, Optional, Union, List, Dict, Any
from xoa_driver.hlfuncs import mgmt, anlt
from xoa_driver.lli import commands
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.170"
USERNAME = "XOA"
PORT = "0/0"
SERDES = 0

async def freya_tx_tune(
        chassis_ip: str, 
        username: str, 
        serdes_id: int, 
        port_str: str):

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
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)
        if not isinstance(module_obj, modules.Z800FreyaModule):
            logging.info(f"The module is not a Freya module")
            logging.info(f"Abort")
            return None

        # Get the port
        port_obj = module_obj.ports.obtain(_pid)

        await mgmt.reserve_port(port_obj, reset=True)
        

        # Read serdes lane count from port
        resp = await port_obj.capabilities.get()
        _serdes_cnt = resp.serdes_count

        if serdes_id+1>_serdes_cnt:
            logging.info(f"Serdes lane {serdes_id} doesn't exit. There are {_serdes_cnt} serdes lanes on this port.")
            return None

        # set using NATIVE
        logging.info(f"Write (native): pre3=0, pre2=0, pre=3, main=42, post=0")
        await port_obj.l1.serdes[serdes_id].medium.tx.native.set(pre3=0, pre2=0, pre=3, main=42, post=3)

        # get using NATIVE, LEVEL, and IEEE
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.native.get()
        logging.info(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.level.get()
        logging.info(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.ieee.get()
        logging.info(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")

        # set using LEVEL
        logging.info(f"Write (level): pre3=0.0 dB, pre2=0.0 dB, pre=1.2 dB, main=483 mV, post=0.0 dB")
        await port_obj.l1.serdes[serdes_id].medium.tx.level.set(pre3=0, pre2=0, pre=12, main=483, post=0)

        # get using NATIVE, LEVEL, and IEEE
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.native.get()
        logging.info(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.level.get()
        logging.info(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.ieee.get()
        logging.info(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")

        # set using IEEE
        logging.info(f"Write (level): pre3=0.0, pre2=0.0, pre=-0.034, main=0.483, post=0")
        await port_obj.l1.serdes[serdes_id].medium.tx.ieee.set(pre3=0, pre2=0, pre=-34, main=483, post=0)

        # get using NATIVE, LEVEL, and IEEE
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.native.get()
        logging.info(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.level.get()
        logging.info(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await port_obj.l1.serdes[serdes_id].medium.tx.ieee.get()
        logging.info(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")

        # release the port
        await mgmt.release_port(port_obj)


async def main():
    stop_event = asyncio.Event()
    try:
        await freya_tx_tune(
            chassis_ip=CHASSIS_IP,
            username=USERNAME,
            serdes_id = SERDES,
            port_str=PORT
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())