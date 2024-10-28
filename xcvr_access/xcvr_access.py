################################################################
#
#                   XCVR ACCESS
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve port
# 3. Read transceiver's temperature
# 4. Read transceiver's register value (single read)
# 5. Write transceiver's register value (single write)
# 6. Read MII transceiver's register value (single operation)
# 7. Write MII transceiver's register value (single operation)
# 8. Read transceiver's register value (sequential read)
# 9. Write transceiver's register value (sequential write)
# 10. Release the port
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "xoa"
PORT = "4/0"

#---------------------------
# xcvr_access
#---------------------------
async def xcvr_access(chassis: str, username: str, port_str: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Valkyrie tester
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as my_tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = my_tester.modules.obtain(_mid)

        # commands which used in this example are not supported by Chimera Module
        if isinstance(module_obj, modules.E100ChimeraModule):
            return None 

        # Get the port 2/2 (module 2)
        port_obj = module_obj.ports.obtain(_pid)

        # use high-level func to reserve the port
        await mgmt.reserve_port(port_obj)

        # Reset the port
        await port_obj.reset.set()

        await asyncio.sleep(10)

        # Read transceiver's temperature
        temperature = await port_obj.transceiver.access_temperature.get()
        logging.info(f"Transceiver temperature: {temperature.integral_part + temperature.fractional_part/256} degrees Celsius.")
        
        # Read transceiver's register value (single read)
        rx_power_lsb = await port_obj.transceiver.access_rw(page_address=0xA2, register_address=0x69).get()
        logging.info(rx_power_lsb.value)

        # Write transceiver's register value (single write)
        await port_obj.transceiver.access_rw(page_address=0xA2, register_address=0x69).set(Hex("FFFF"))

        # Read MII transceiver's register value (single operation)
        rx_power_lsb = await port_obj.transceiver.access_mii(register_address=0x69).get()
        logging.info(rx_power_lsb.value)

        # Write MII transceiver's register value (single operation)
        await port_obj.transceiver.access_mii(register_address=0x69).set(Hex("FFFF"))

        # Read transceiver's register value (sequential read)
        i2c_read = await port_obj.transceiver.access_rw_seq(page_address=0xA2, register_address=0x69, byte_count=16).get()
        logging.info(i2c_read.value)

        # Write transceiver's register value (sequential write)
        await port_obj.transceiver.access_rw_seq(page_address=0xA2, register_address=0x69, byte_count=16).set(Hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))

        # Read transceiver's register value (sequential read with bank)
        i2c_read_bank = await port_obj.transceiver.access_rw_seq_bank(bank_address=0x00, page_address=0x20, register_address=0x80, byte_count=1).get()
        logging.info(i2c_read_bank.value)

        # Release the port
        await port_obj.reservation.set_release()

async def main():
    stop_event = asyncio.Event()
    try:
        await xcvr_access(
            chassis=CHASSIS_IP, 
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())
