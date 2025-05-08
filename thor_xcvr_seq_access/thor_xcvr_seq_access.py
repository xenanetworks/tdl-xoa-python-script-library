################################################################
#
#                   THOR XCVR SEQUENTIAL ACCESS
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve port
# 3. I2C sequential write into transceiver
# 4. I2C sequential read from transceiver
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
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
PORT = "0/0"

PAGE_ADDRESS = 1
REGISTER_ADDRESS = 2
DATA_HEX = "ffff"

#---------------------------
# thor_seq_access
#---------------------------
async def thor_seq_access(chassis: str, username: str, port_str: str, page: int, addr: int, data: str):
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
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module = tester.modules.obtain(_mid)
        if not isinstance(module, modules.Z400ThorModule):
            return None

        port = module.ports.obtain(_pid)

        logging.info(f"Reserve Port {_mid}/{_pid}")
        await mgmt.release_module(module=module)
        await mgmt.reserve_port(port=port)

        if len(data)%2 != 0:
            logging.info(f"Data length not valid")
            return None
        else:
            await port.transceiver.access_rw_seq(
                page_address=page,
                register_address=addr,
                byte_count=len(data)).set(value=Hex(data))
            logging.info(f"Write {data} into Page {page}, Reg {addr}")

            resp = await port.transceiver.access_rw_seq(
                page_address=page,
                register_address=addr,
                byte_count=len(data)).get()
            logging.info(f"Read from Page {page}, Reg {addr}: {resp.value}")


async def main():
    stop_event = asyncio.Event()
    try:
        await thor_seq_access(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            page=PAGE_ADDRESS,
            addr=REGISTER_ADDRESS,
            data=DATA_HEX
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())