################################################################
#
#                   PORT CONFIG INTEGRATION
#
# In XenaManager, port configurations are saved into files 
# with extension **.xpc** in the same command format as used by 
# [XOA CLI](https://docs.xenanetworks.com/projects/xoa-cli/). 
# This makes it very easy to go back and forth between a XenaManager 
# environment and a XOA CLI environment. For example, exporting a 
# port configuration from XenaManager generates a configuration 
# file in a simple text format that can be edited using a text 
# editing tool such as Microsoft Notepad. 
# It can then be imported back into XenaManager.
# 
# What this script example does:
# 1. Connect to a tester
# 2. Reserve port
# 3. Load a .xpc file to the port
#
################################################################

import asyncio
from contextlib import suppress
import ipaddress

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver import exceptions
from xoa_driver.hlfuncs import mgmt, cli
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "xoa"
PORT = "0/0"

#---------------------------
# xpc_integration
#---------------------------
async def xpc_integration(chassis: str, username: str, port_str: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # access module on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        # access port 0 on the module as the TX port
        port_obj = module_obj.ports.obtain(_pid)

        #---------------------------
        # Port reservation
        #---------------------------
        # use high-level func to reserve the port
        await mgmt.reserve_port(port_obj, reset=True)

        await cli.port_config_from_file(port_obj, "port_config.xpc")

        # use high-level func to reserve the port
        await mgmt.release_port(port_obj)


async def main():
    stop_event = asyncio.Event()
    try:
        await xpc_integration(
            chassis=CHASSIS_IP, 
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())