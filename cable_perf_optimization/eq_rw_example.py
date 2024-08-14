################################################################
#
#                   EQ R/W EXAMPLE
#
# This script shows you how to do EQ read and write
#
################################################################

import asyncio

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from func_lib import *
import logging

#---------------------------
# Global parameters
#---------------------------
CHASSIS_IP = "10.165.136.60"
P0 = "3/0"
P1 = "6/0"
LANE = 1
USERNAME = "xoa"
WAIT_TIME = 2

#---------------------------
# eq_rw_example
#---------------------------
async def eq_rw_example(chassis_ip: str, p0: str, p1: str, lane: int, username: str):
    
    _mid_0 = int(p0.split("/")[0])
    _pid_0 = int(p0.split("/")[1])
    _mid_1 = int(p1.split("/")[0])
    _pid_1 = int(p1.split("/")[1])

    # configure basic logger
    logger = logging.getLogger("rw_func")
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="rw_func.log", mode="a"),
            logging.StreamHandler()]
        )

    if not 1<=lane<=8:
        logger.warning(f"Lane must in range[1,8]")
        return

    logger.info(f"#####################################################################")
    logger.info(f"Chassis:            {chassis_ip}")
    logger.info(f"Username:           {username}")
    logger.info(f"Port 0:             {p0}")
    logger.info(f"Port 1:             {p1}")
    logger.info(f"Lane:               {lane}")
    logger.info(f"#####################################################################")

    # connect to the tester and automatically disconnect when ended
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:
    
        # access module on the tester
        module_0 = tester_obj.modules.obtain(_mid_0)
        module_1 = tester_obj.modules.obtain(_mid_1)

        # the module must be a freya module
        if not isinstance(module_0, modules.Z800FreyaModule):
            return None
        if not isinstance(module_1, modules.Z800FreyaModule):
            return None
        
        # get the port object
        port_0 = module_0.ports.obtain(_pid_0)
        port_1 = module_1.ports.obtain(_pid_1)

        # reserve the port and reset the port
        await mgmt.free_module(module_0, should_free_ports=True)
        await mgmt.reserve_port(port_0)
        await mgmt.reset_port(port_0)
        await mgmt.free_module(module_1, should_free_ports=True)
        await mgmt.reserve_port(port_1)
        await mgmt.reset_port(port_1)
        await asyncio.sleep(WAIT_TIME)

        # read port 0 & 1
        await output_eq_read(port=port_0, lane=lane, cursor=Cursor.AMPLITUDE, logger=logger)
        await output_eq_read(port=port_0, lane=lane, cursor=Cursor.PRECURSOR, logger=logger)
        await output_eq_read(port=port_0, lane=lane, cursor=Cursor.POSTCURSOR, logger=logger)
        await output_eq_read(port=port_1, lane=lane, cursor=Cursor.AMPLITUDE, logger=logger)
        await output_eq_read(port=port_1, lane=lane, cursor=Cursor.PRECURSOR, logger=logger)
        await output_eq_read(port=port_1, lane=lane, cursor=Cursor.POSTCURSOR, logger=logger)
        await asyncio.sleep(WAIT_TIME)

        # write port 0 & 1
        await output_eq_write(port=port_0, lane=lane, db=1, cursor=Cursor.AMPLITUDE, logger=logger)
        await output_eq_write(port=port_0, lane=lane, db=2, cursor=Cursor.PRECURSOR, logger=logger)
        await output_eq_write(port=port_0, lane=lane, db=3, cursor=Cursor.POSTCURSOR, logger=logger)
        await output_eq_write(port=port_1, lane=lane, db=1, cursor=Cursor.AMPLITUDE, logger=logger)
        await output_eq_write(port=port_1, lane=lane, db=2, cursor=Cursor.PRECURSOR, logger=logger)
        await output_eq_write(port=port_1, lane=lane, db=3, cursor=Cursor.POSTCURSOR, logger=logger)
        await asyncio.sleep(WAIT_TIME)

if __name__ == "__main__":
    asyncio.run(eq_rw_example(CHASSIS_IP, P0, P1, LANE, USERNAME))