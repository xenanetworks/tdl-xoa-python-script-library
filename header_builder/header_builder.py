#--------------------------------
# Author: leonard.yu@teledyne.com
#--------------------------------
import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import utils
from xoa_driver import enums
from ipaddress import IPv4Address, IPv6Address
from binascii import hexlify
from xoa_driver.misc import Hex

#---------------------------
# Global parameters
#---------------------------

CHASSIS_IP = "10.10.10.10"      # Chassis IP address or hostname
USERNAME = "XOA"                # Username
MODULE_INDEX = 0                # Module index
TX_PORT_INDEX = 0               # TX Port index

FRAME_SIZE_BYTES = 1000         # Frame size on wire including the FCS.
FRAME_COUNT = 20                # The number of frames including the first, the middle, and the last.
TRAFFIC_RATE_FPS = 100          # Traffic rate in frames per second
TRAFFIC_RATE_PERCENT = int(4/10 * 1000000)

SHOULD_BURST = False            # Whether the middle frames should be bursty
BURST_SIZE_FRAMES = 9           # Burst size in frames for the middle frames
INTER_BURST_GAP_BYTES = 3000    # The inter-burst gap in bytes
INTRA_BURST_GAP_BYTES = 1000    # The inter-frame gap within a burst, aka. intra-burst gap, in bytes



#---------------------------
# Header content for streams
#---------------------------
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
    
class IPV4:
    def __init__(self):
        self.version = 4
        self.header_length = 5
        self.dscp = 0
        self.ecn = 0
        self.total_length = 42
        self.identification = "0000"
        self.flags = 0
        self.offset = 0
        self.ttl = 255
        self.proto = 255
        self.checksum = "0000"
        self.src = "0.0.0.0"
        self.dst = "0.0.0.0"

    def __str__(self):
        _ver = '{:01X}'.format(self.version)
        _header_length = '{:01X}'.format(self.header_length)
        _dscp_ecn = '{:02X}'.format((self.dscp<<2)+self.ecn)
        _total_len = '{:04X}'.format(self.total_length)
        _ident = self.identification
        _flag_offset = '{:04X}'.format((self.flags<<13)+self.offset)
        _ttl = '{:02X}'.format(self.ttl)
        _proto = '{:02X}'.format(self.proto)
        _check = self.checksum
        _src = hexlify(IPv4Address(self.src).packed).decode()
        _dst = hexlify(IPv4Address(self.dst).packed).decode()
        return f"{_ver}{_header_length}{_dscp_ecn}{_total_len}{_ident}{_flag_offset}{_ttl}{_proto}{_check}{_src}{_dst}".upper()

class IPV6:
    def __init__(self):
        self.version = 6
        self.traff_class = 8
        self.flow_label = 0
        self.payload_length = 0
        self.next_header = "11"
        self.hop_limit = 1
        self.src = "2000::2"
        self.dst = "2000::100"

    def __str__(self):
        _ver = '{:01X}'.format(self.version)
        _traff_class = '{:01X}'.format(self.traff_class)
        _flow_label = '{:06X}'.format(self.flow_label)
        _payload_len = '{:04X}'.format(self.payload_length)
        _next_header = self.next_header
        _hop_limit = '{:02X}'.format(self.hop_limit)
        _src = hexlify(IPv6Address(self.src).packed).decode()
        _dst = hexlify(IPv6Address(self.dst).packed).decode()
        return f"{_ver}{_traff_class}{_flow_label}{_payload_len}{_next_header}{_hop_limit}{_src}{_dst}".upper()

class UDP:
    def __init__(self):
        self.src_port = 0
        self.dst_port = 0
        self.length = 0
        self.checksum = 0

    def __str__(self):
        _src_port = '{:04X}'.format(self.src_port)
        _dst_port = '{:04X}'.format(self.dst_port)
        _length = '{:04X}'.format(self.length)
        _checksum = '{:04X}'.format(self.checksum)
        return f"{_src_port}{_dst_port}{_length}{_checksum}".upper()



#------------------------------
# def my_awesome_func()
#------------------------------
async def my_awesome_func(stop_event: asyncio.Event, should_burst: bool) -> None:

    # create tester instance and establish connection
    tester = await testers.L23Tester(CHASSIS_IP, USERNAME, enable_logging=False) 

    # access the module on the tester
    module = tester.modules.obtain(MODULE_INDEX)

    # check if the module is of type Loki-100G-5S-2P
    if not isinstance(module, modules.ModuleChimera):
        
        # access the txport on the module
        txport = module.ports.obtain(TX_PORT_INDEX)

        #---------------------------
        # Port reservation
        #---------------------------
        print(f"#---------------------------")
        print(f"# Port reservation")
        print(f"#---------------------------")
        if txport.is_released():
            print(f"The txport is released (not owned by anyone). Will reserve the txport to continue txport configuration.")
            await txport.reservation.set_reserve() # set reservation , means txport will be controlled by our session
        elif not txport.is_reserved_by_me():
            print(f"The txport is reserved by others. Will relinquish and reserve the txport to continue txport configuration.")
            await txport.reservation.set_relinquish() # send relinquish the txport
            await txport.reservation.set_reserve() # set reservation , means txport will be controlled by our session

        #---------------------------
        # Start port configuration
        #---------------------------
        print(f"#---------------------------")
        print(f"# Start port configuration")
        print(f"#---------------------------")

        print(f"Reset the txport")
        await txport.reset.set()

        print(f"Configure the txport")
        await utils.apply(
            txport.comment.set(comment="this is a comment"),
            txport.tx_config.enable.set_on(),
            txport.latency_config.offset.set(offset=0),
            txport.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            txport.tx_config.burst_period.set(burst_period=0),
            txport.tx_config.packet_limit.set(packet_count_limit=FRAME_COUNT),
            txport.max_header_length.set(max_header_length=128),
            txport.autotrain.set(interval=0),
            txport.loop_back.set_none(),                                # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            txport.checksum.set(offset=0),
            txport.tx_config.delay.set(delay_val=0),
            txport.tpld_mode.set_normal(),
            txport.payload_mode.set_normal(),
            #txport.rate.pps.set(port_rate_pps=TRAFFIC_RATE_FPS),       # If you want to control traffic rate with FPS, uncomment this.
            txport.rate.fraction.set(TRAFFIC_RATE_PERCENT),             # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
        )
        if should_burst:
            await txport.tx_config.mode.set_burst()
        else:
            await txport.tx_config.mode.set_sequential()
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        print(f"   Configure stream on the txport")

        stream_0 = await txport.streams.create()
        eth = Ethernet()
        eth.src_mac = "aaaa.aaaa.0005"
        eth.dst_mac = "bbbb.bbbb.0005"

        ipv4 = IPV4()
        ipv4.src = "1.1.1.5"
        ipv4.dst = "2.2.2.5"

        ipv6 = IPV6()
        ipv6.src = "2001::5"
        ipv6.dst = "2002::5"

        udp = UDP()
        udp.src_port = 4791
        udp.dst_port = 4791

        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=1),
            stream_0.comment.set(f"First packet"),
            stream_0.rate.fraction.set(stream_rate_ppm=10000),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp))),
            stream_0.packet.length.set(length_type=enums.LengthType.FIXED, min_val=FRAME_SIZE_BYTES, max_val=FRAME_SIZE_BYTES),
            stream_0.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_0.tpld_id.set(test_payload_identifier = 0),
            stream_0.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_0.burst.burstiness.set(size=100, density=100)
            await stream_0.burst.gap.set(inter_packet_gap=INTER_BURST_GAP_BYTES, inter_burst_gap=INTER_BURST_GAP_BYTES)


async def main():
    stop_event =asyncio.Event()
    try:
        await my_awesome_func(stop_event, should_burst=SHOULD_BURST)
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())