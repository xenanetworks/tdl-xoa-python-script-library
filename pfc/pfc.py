################################################################
#
#                   PFC Example
#
# What this script example does:
# Create a PFC stream on the port to suppress a specific traffic 
# class of the TX port traffic to a target fraction of the 
# port speed.
#
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import Hex
import logging
import datetime
from typing_extensions import List

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "pfc"
PORT = "6/0"
PRIO = 7                # Class 7
QUANTA = 65535
TARGET_FRACTION = 0.4   # 40% of the port speed

#---------------------------
# pfc
#---------------------------
async def pfc(chassis: str, username: str, port_str: str, prio: int, quanta: int, target_fraction: float):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="pfc.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")
        
        # Access module index 0 on the tester
        mid = int(port_str.split("/")[0])
        pid = int(port_str.split("/")[1])

        module_obj = tester_obj.modules.obtain(mid)
        if isinstance(module_obj, modules.E100ChimeraModule):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port object
        port_obj = module_obj.ports.obtain(pid)

        # Forcibly reserve the port
        await mgmt.reserve_port(port_obj)
        await mgmt.reset_port(port_obj)
        await asyncio.sleep(1)

        resp = await port_obj.net_config.mac_address.get()
        port_macaddress = resp.mac_address

        resp = await port_obj.speed.current.get()
        port_speed = resp.port_speed * 1_000_000
        print(f"Port speed: {port_speed} bps")
        pfc_pps = int(port_speed/512/quanta * (1-target_fraction))

        stream_obj = await port_obj.streams.create()
        eth_str = f"0180c2000001{port_macaddress}8808"
        macpfc = MACControlPFC()
        macpfc.class_enable_list[7-prio] = True
        macpfc.class_quanta_list[7-prio] = quanta
        # macpfc = MACControlPause()
        await stream_obj.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex("00"))
        await stream_obj.packet.length.set(length_type=enums.LengthType.FIXED, min_val=64, max_val=64)
        await stream_obj.packet.header.protocol.set(segments=[enums.ProtocolOption.ETHERNET, enums.ProtocolOption.MACCTRLPFC])
        await stream_obj.packet.header.data.set(hex_data=Hex(eth_str+str(macpfc)))
        await stream_obj.rate.pps.set(stream_rate_pps=pfc_pps)
        await stream_obj.enable.set_on()

        # Release the port
        await mgmt.free_port(port_obj)
        


class MACControlPFC:
    opcode: str = "0101"
    class_enable_list: List[bool] = [False] * 8
    class_quanta_list: List[int] = [65535] * 8
    
    def __str__(self):
        _opcode: str = self.opcode
        _class_enable_vector_str: str = ''.join([str(int(x)) for x in self.class_enable_list])
        _class_enable_vector_int: int = int(_class_enable_vector_str, 2)
        _class_enable_vector = '{:02X}'.format(_class_enable_vector_int)
        _reserved: str = "00"
        _class_quanta_list: str = ''.join([f"{x:04x}" for x in self.class_quanta_list])
        return f"{_opcode}{_reserved}{_class_enable_vector}{_class_quanta_list}".upper()
    
class MACControlPause:
    opcode: str = "0001"
    value: int = 65535
    
    def __str__(self):
        _opcode: str = self.opcode
        _value = '{:04X}'.format(self.value)
        return f"{_opcode}{_value}".upper()


async def main():
    stop_event = asyncio.Event()
    try:
        await pfc(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            prio=PRIO,
            quanta=QUANTA,
            target_fraction=TARGET_FRACTION
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
