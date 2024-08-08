################################################################
#
#                   CHECK PORT CAPABILITIES
#
# What this script example does:
# 1. Connect to a tester
# 2. Read port capabilities
#
################################################################

import asyncio
from xoa_driver import testers
import json
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS = "10.165.136.60"
USERNAME = "XOA"
PORT = "3/0"

#---------------------------
# check_port_capabilities
#---------------------------
async def check_port_capabilities(chassis: str, username: str, port_str: str):

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="check_port_capabilities.log", mode="a"),
            logging.StreamHandler()]
        )
    
    async with testers.L23Tester(chassis, username, enable_logging=False) as tester:

        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])

        module = tester.modules.obtain(_mid)
        port = module.ports.obtain(_pid)

        # Use capabilities_ext that returns JSON
        resp = await port.capabilities_ext.get()
        logging.info(json.dumps(json.loads(resp.data), sort_keys=True, indent=4))

        # Use capabilities that returns object
        resp = await port.capabilities.get()
        logging.info(f"Max streams: {resp.max_streams_per_port}")
        logging.info(f"Max fps: {resp.max_pps}")

async def main():
    stop_event = asyncio.Event()
    try:
        await check_port_capabilities(CHASSIS, USERNAME, PORT)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())