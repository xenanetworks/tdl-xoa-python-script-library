import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
from ipaddress import IPv4Address, IPv6Address
from binascii import hexlify
from xoa_driver.misc import Hex

CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "quick_start"
MODULE_IDX = 2
PORT_IDX = 0
ARP_FPS = 1

class Ethernet:
    def __init__(self):
        self.dst_mac = "0000.0000.0000"
        self.src_mac = "0000.0000.0000"
        self.ethertype = "86DD"
    
    def __str__(self):
        _dst_mac = self.dst_mac.replace(".", "")
        _src_mac = self.src_mac.replace(".", "")
        _ethertype = self.ethertype
        return f"{_dst_mac}{_src_mac}{_ethertype}".upper()
    
class ARP:
    def __init__(self):
        self.hardware_type: str = "0001"
        self.protocol_type: str = "0800"
        self.hardware_size: str = "06"
        self.protocol_size: str = "04"
        self.opcode: str = "0001"
        self.sender_mac = "0000.0000.0000"
        self.sender_ip = "0.0.0.0"
        self.target_mac = "0000.0000.0000"
        self.target_ip = "0.0.0.0"
    
    def __str__(self):
        _hardware_type = self.hardware_type
        _protocol_type = self.protocol_type
        _hardware_size = self.hardware_size
        _protocol_size = self.protocol_size
        _sender_mac = self.sender_mac.replace(".", "")
        _sender_ip = hexlify(IPv4Address(self.sender_ip).packed).decode()
        _target_mac = self.target_mac.replace(".", "")
        _target_ip = hexlify(IPv4Address(self.target_ip).packed).decode()
        return f"{_hardware_type}{_protocol_type}{_hardware_size}{_protocol_size}{_sender_mac}{_sender_ip}{_target_mac}{_target_ip}".upper()

async def gratuitous_arp(stop_event: asyncio.Event):
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        my_module = tester.modules.obtain(MODULE_IDX)

        if isinstance(my_module, modules.ModuleChimera):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module 
        port = my_module.ports.obtain(PORT_IDX)

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
            stream.rate.pps.set(stream_rate_pps=ARP_FPS),
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
        eth = Ethernet()
        eth.src_mac = "0000.0000.0002"
        eth.dst_mac = "0000.0000.0003"
        arp = ARP()
        arp.sender_mac = eth.src_mac
        arp.sender_ip = "1.1.1.2"
        arp.target_mac = eth.dst_mac
        arp.target_ip = "1.1.1.3"
        await stream.packet.header.data.set(hex_data=Hex(str(eth)+str(arp)))

        # Start traffic on the port for 10 secs
        await port.traffic.state.set_start()
        await asyncio.sleep(10)
        await port.traffic.state.set_stop()

async def main():
    stop_event =asyncio.Event()
    try:
        await gratuitous_arp(stop_event)
    except KeyboardInterrupt:
        stop_event.set()

if __name__=="__main__":
    asyncio.run(main())