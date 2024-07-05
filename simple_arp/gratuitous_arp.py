################################################################
#
#                   GRATUITOUS ARP
#
# This script show you how to send a gratuitous ARP
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
from ipaddress import IPv4Address, IPv6Address
from binascii import hexlify
from xoa_driver.misc import Hex

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "simple_arp"
PORT = "2/0"
ARP_FPS = 1

#---------------------------
# gratuitous_arp
#---------------------------
async def gratuitous_arp(chassis: str, username: str, port_str: str, fps: int):
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module = tester.modules.obtain(_mid)

        if isinstance(module, modules.E100ChimeraModule):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module 
        port = module.ports.obtain(_pid)

        # Forcibly reserve the TX port and reset it.
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        await asyncio.sleep(5)

        # Configure the port with minimal necessary settings after reset
        await utils.apply(
            port.comment.set(comment="gratuitous arp sim port"),
            port.tx_config.enable.set_on()
        )
        # Create a stream on the port
        stream = await port.streams.create()

        # Configure the stream
        await utils.apply(
            # Enable the stream
            stream.enable.set_on(),
            # Stream description
            stream.comment.set(f"gratuitous arp"),
            # Stream fps rate
            stream.rate.pps.set(stream_rate_pps=fps),
            # Stream header structure
            stream.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.ARP,
                ]),
            # Stream packet size
            stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=68, max_val=68),
            # Stream payload
            stream.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("0000")
                ),
            # Stream test ID. (set to -1 to disable)
            stream.tpld_id.set(test_payload_identifier = 0),
            # Set FCS checksum on
            stream.insert_packets_checksum.set_on()
        )
        # Configure the stream header value
        eth = headers.Ethernet()
        eth.src_mac = "0000.0000.0002"
        eth.dst_mac = "0000.0000.0003"
        arp = headers.ARP()
        arp.sender_mac = eth.src_mac
        arp.sender_ip = "1.1.1.2"
        arp.target_mac = eth.dst_mac
        arp.target_ip = "1.1.1.3"
        await stream.packet.header.data.set(hex_data=Hex(str(eth)+str(arp)))

        # Start traffic on the port for 10 secs
        await port.traffic.state.set_start()
        await asyncio.sleep(10)
        await port.traffic.state.set_stop()

        # release port
        await mgmt.free_port(port=port)

async def main():
    stop_event =asyncio.Event()
    try:
        await gratuitous_arp(chassis=CHASSIS_IP, username=USERNAME, port_str=PORT, fps=ARP_FPS)
    except KeyboardInterrupt:
        stop_event.set()

if __name__=="__main__":
    asyncio.run(main())