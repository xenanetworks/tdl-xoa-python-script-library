import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, config_io
import logging
import csv
from datetime import datetime
from time import sleep
import os
import json
import sys

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.10.10.10"
USERNAME = "XOA"
PORT1 = "0/0"
PORT2 = "5/0"

async def my_awesome_func(chassis: str, username: str, port_str1: str, port_str2: str):
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

        # Access module index 0 on the tester
        _mid1 = int(port_str1.split("/")[0])
        _pid1 = int(port_str1.split("/")[1])
        _mid2 = int(port_str2.split("/")[0])
        _pid2 = int(port_str2.split("/")[1])
        module_obj1 = tester.modules.obtain(_mid1)
        module_obj2 = tester.modules.obtain(_mid2)

        if isinstance(module_obj1, modules.E100ChimeraModule):
            await asyncio.sleep(0)
            return  # commands which used in this example are not supported by Chimera Module
        if isinstance(module_obj2, modules.E100ChimeraModule):
            await asyncio.sleep(0)
            return  # commands which used in this example are not supported by Chimera Module

        # Get the port objects
        port_obj1 = module_obj1.ports.obtain(_pid1)
        port_obj2 = module_obj2.ports.obtain(_pid2)

        # Forcibly reserve and reset
        await mgmt.release_module(module_obj1, should_release_ports=True)
        await mgmt.release_module(module_obj2, should_release_ports=True)
        await mgmt.reserve_port(port_obj1, reset=True)
        await mgmt.reserve_port(port_obj2, reset=True)
        
        await asyncio.sleep(5)

        # -- Save Port Config Example --
        logging.info(f"Save port config from P-{port_obj1.kind.module_id}-{port_obj1.kind.port_id}.xpc")
        path = os.path.join(os.path.dirname(__file__), f"P-{port_obj1.kind.module_id}-{port_obj1.kind.port_id}.xpc")
        resp = await config_io.save_port_config(tester=tester, port=port_obj1, path=path)
        logging.info(resp)

        # -- Load Port Config Example --
        logging.info(f"Load port config to P-{port_obj1.kind.module_id}-{port_obj1.kind.port_id}")
        path = os.path.join(os.path.dirname(__file__), f"P-{port_obj1.kind.module_id}-{port_obj1.kind.port_id}.xpc")
        await config_io.load_port_config(tester=tester, port=port_obj1, path=path)
        
        # -- Save Test Case Config Example --
        logging.info(f"Save test case config to testcase1.xtc2")
        path = os.path.join(os.path.dirname(__file__), f"testcase1.xtc2")
        resp = await config_io.save_test_case_config(tester=tester, ports=[port_obj1, port_obj2], testbed_name="my testbed", path=f"testcase1.xtc2", with_module_config=True)
        logging.info(resp)

        # -- Load Test Case Config Example --
        logging.info(f"Load test case config from testcase1.xtc2")
        path = os.path.join(os.path.dirname(__file__), f"testcase1.xtc2")
        await config_io.load_test_case_config(tester=tester, path=path)

        #################################################
        #                  Release                      #
        #################################################
        # Release the ports
        await mgmt.release_port(port_obj1)
        await mgmt.release_port(port_obj2)

async def main():
    stop_event = asyncio.Event()
    try:
        await my_awesome_func(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str1=PORT1,
            port_str2=PORT2
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
