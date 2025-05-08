################################################################
#
#                   SERVER-CLIENT STREAM SYNC
#
# This script will help you access the streams that are created 
# on the port already.
# 
# Streams, once created on a port, will stay on the port until 
# you explicitly remove them or reset the port.
# 
# Using XOA Python API, you can write your own code to 
# "synchronize" your Python code to the server status so your 
# Python script can also access those streams on the port.
#
################################################################

import asyncio
from xoa_driver import (
    testers,
    modules,
    ports,
    utils,
    enums,
    exceptions
)
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.170"
USERNAME = "XOA"
PORT = "0/0"

#---------------------------
# stream_sync
#---------------------------
async def stream_sync(chassis: str, username: str, port_str: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        # access the port object
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)
        if isinstance(module_obj, modules.ModuleChimera):
            return None
        port_obj = module_obj.ports.obtain(_pid)

        # reserve the port by force
        await mgmt.release_module(module=module_obj, should_release_ports=False)
        await mgmt.reserve_port(port=port_obj, force=True)

        # synchronize the streams on the physical port and the stream indices on the port object
        await port_obj.streams.server_sync()

        logging.info(f"Number of streams on the port: {len(port_obj.streams)}")
        for i in range(len(port_obj.streams)):
            stream = port_obj.streams.obtain(i)
            resp = await stream.comment.get()
            logging.info(f"Stream [{i}] : {resp.comment}")

        # release the port
        await mgmt.release_port(port_obj)

async def main():
    stop_event = asyncio.Event()
    try:
        await stream_sync(
            chassis=CHASSIS_IP, 
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())