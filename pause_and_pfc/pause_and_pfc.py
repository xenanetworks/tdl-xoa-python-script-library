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
# A PFC pause frame contains a 2-byte timer value for each CoS 
# that indicates the length of time that the traffic needs to be 
# paused. The unit of time for the timer is specified in pause 
# quanta. A quanta is the time that is required for transmitting 
# 512 bits at the speed of the port. The range is from 0 to 65535.
# 
# To suppress a specific traffic class of the TX port traffic to a 
# target fraction of the port speed, the following formula is used:
# 
# PFC_fps = PortSpeed_bps/512/Quanta * (1-TargetFraction)
# 
# e.g. if the port speed is 800Gbps, the quanta is 65535, and the
# target fraction is 40%, the PFC frames per second is 
# 100_000_000_000/512/65535 * (1-0.4) = 14305 fps.
# 
################################################################

################################################################
#
#                   PAUSE Example
#
# What this script example does:
# Create a PAUSE stream on the port to suppress a specific traffic
# class of the TX port traffic to a target fraction of the
# port speed.
#
# To suppress a specific traffic class of the TX port traffic to a 
# target fraction of the port speed, the following formula is used:
#
# PAUSE_fps = PortSpeed_bps/512/Quanta * (1-TargetFraction)
#
# e.g. if the port speed is 800Gbps, the quanta is 65535, and the
# target fraction is 40%, the PAUSE frames per second is 
# 100_000_000_000/512/65535 * (1-0.4) = 14305 fps.
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
from typing_extensions import List

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.70"
USERNAME = "pause_pfc"
PORT = "2/0"
PRIO = 7                # Class 7, valid when USE_PFC is True
QUANTA = 65535          # Valid range: 0~65535
TARGET_FRACTION = 0.4   # Suppress the incoming traffic to 40% of the port speed
USE_PFC = False         # True to use PFC, False to use PAUSE

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
        await mgmt.reserve_port(port_obj, reset=True)
        
        await asyncio.sleep(1)

        resp = await port_obj.net_config.mac_address.get()
        port_macaddress = resp.mac_address

        # get the port speed
        resp = await port_obj.speed.current.get()
        port_speed = resp.port_speed * 1_000_000
        print(f"Port speed: {port_speed} bps")

        # Calculate the PFC frames per second
        pfc_pps = int(port_speed/512/quanta * (1-target_fraction))

        # Create and config a PFC stream
        stream_obj = await port_obj.streams.create()
        eth_str = f"0180c2000001{port_macaddress}8808"
        macpfc = MACControlPFC()
        macpfc.class_enable_list[7-prio] = True
        macpfc.class_quanta_list[7-prio] = quanta
        await stream_obj.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex("00"))
        await stream_obj.packet.length.set(length_type=enums.LengthType.FIXED, min_val=64, max_val=64)
        await stream_obj.packet.header.protocol.set(segments=[enums.ProtocolOption.ETHERNET, enums.ProtocolOption.MACCTRLPFC])
        await stream_obj.packet.header.data.set(hex_data=Hex(eth_str+str(macpfc)))
        await stream_obj.rate.pps.set(stream_rate_pps=pfc_pps)
        await stream_obj.enable.set_on()

        # Release the port
        await mgmt.release_port(port_obj)
        

#---------------------------
# pause
#---------------------------
async def pause(chassis: str, username: str, port_str: str, quanta: int, target_fraction: float):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="pause.log", mode="a"),
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
        await mgmt.reserve_port(port_obj, reset=True)
        
        await asyncio.sleep(1)

        resp = await port_obj.net_config.mac_address.get()
        port_macaddress = resp.mac_address

        # get the port speed
        resp = await port_obj.speed.current.get()
        port_speed = resp.port_speed * 1_000_000
        print(f"Port speed: {port_speed} bps")

        # Calculate the PAUSE frames per second
        pause_pps = int(port_speed/512/quanta * (1-target_fraction))

        # Create and config a PAUSE stream
        stream_obj = await port_obj.streams.create()
        eth_str = f"0180c2000001{port_macaddress}8808"
        macpause = MACControlPAUSE()
        await stream_obj.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex("00"))
        await stream_obj.packet.length.set(length_type=enums.LengthType.FIXED, min_val=64, max_val=64)
        await stream_obj.packet.header.protocol.set(segments=[enums.ProtocolOption.ETHERNET, enums.ProtocolOption.MACCTRL])
        await stream_obj.packet.header.data.set(hex_data=Hex(eth_str+str(macpause)))
        await stream_obj.rate.pps.set(stream_rate_pps=pause_pps)
        await stream_obj.enable.set_on()

        # Release the port
        await mgmt.release_port(port_obj)

#---------------------------
# helpers
#---------------------------
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

class MACControlPAUSE:
    opcode: str = "0001"
    quanta: int = 65535
    
    def __str__(self):
        _opcode: str = self.opcode
        _quanta: str = f"{self.quanta:04x}"
        return f"{_opcode}{_quanta}".upper()


async def main():
    stop_event = asyncio.Event()
    try:
        if USE_PFC:
            await pfc(
                chassis=CHASSIS_IP,
                username=USERNAME,
                port_str=PORT,
                prio=PRIO,
                quanta=QUANTA,
                target_fraction=TARGET_FRACTION
            )
        else:
            await pause(
                chassis=CHASSIS_IP,
                username=USERNAME,
                port_str=PORT,
                quanta=QUANTA,
                target_fraction=TARGET_FRACTION
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
