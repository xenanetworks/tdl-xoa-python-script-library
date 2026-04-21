import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver.hlfuncs import mgmt, config_io
import logging
import os

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.153.243"
USERNAME = "XOADev"
PORT1 = "2/0"
PORT2 = "2/1"
TESTCASE_PATH = "TestMe.xtc2"

async def my_awesome_func(chassis: str, username: str, port_str1: str, port_str2: str, testcase_path: str):
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
        await mgmt.release_modules(modules=[module_obj1, module_obj2], should_release_ports=True)
        await mgmt.reserve_ports(ports=[port_obj1, port_obj2], reset=False)
        
        await asyncio.sleep(5)

        # -- Load Test Case Config Example --
        logging.info(f"Load test case config from {testcase_path}")
        path = os.path.join(os.path.dirname(__file__), f"{testcase_path}")
        await config_io.load_testbed_config(tester=tester, path=path)

        await asyncio.sleep(2)
        await mgmt.reserve_ports(ports=[port_obj1, port_obj2], reset=False)
        await asyncio.sleep(2)
        await port_obj1.traffic.state.set_start()
        await asyncio.sleep(10)
        await port_obj1.traffic.state.set_stop()

async def main():
    stop_event = asyncio.Event()
    try:
        await my_awesome_func(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str1=PORT1,
            port_str2=PORT2,
            testcase_path=TESTCASE_PATH
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
