################################################################
#
#                   BUILD TCP STREAM
#
# This script shows you how to build TCP stream using the header 
# builder in headers.py
#
################################################################
import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import utils
from xoa_driver import enums
from ipaddress import IPv4Address, IPv6Address
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt, headers
import logging

#---------------------------
# Global parameters
#---------------------------

CHASSIS_IP = "10.165.136.70"      # Chassis IP address or hostname
USERNAME = "XOA"                # Username
PORT = "0/0"

FRAME_SIZE_BYTES = 1000         # Frame size on wire including the FCS.
FRAME_COUNT = 20                # The number of frames including the first, the middle, and the last.
TRAFFIC_RATE_FPS = 100          # Traffic rate in frames per second
TRAFFIC_RATE_PERCENT = int(4/10 * 1000000)

SHOULD_BURST = False            # Whether the middle frames should be bursty
BURST_SIZE_FRAMES = 9           # Burst size in frames for the middle frames
INTER_BURST_GAP_BYTES = 3000    # The inter-burst gap in bytes
INTRA_BURST_GAP_BYTES = 1000    # The inter-frame gap within a burst, aka. intra-burst gap, in bytes


#------------------------------
# build_tcp_stream
#------------------------------
async def build_tcp_stream(chassis: str, username: str, port_str: str, should_burst: bool) -> None:
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    tester = await testers.L23Tester(CHASSIS_IP, USERNAME, enable_logging=False) 

    # access the module on the tester
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = tester.modules.obtain(_mid)

    # check if the module is of type Loki-100G-5S-2P
    if not isinstance(module_obj, modules.ModuleChimera):
        
        # access the tx port on the module
        port_obj = module_obj.ports.obtain(_pid)

        #---------------------------
        # Port reservation
        #---------------------------
        logging.info(f"#---------------------------")
        logging.info(f"# Port reservation")
        logging.info(f"#---------------------------")
        await mgmt.reserve_port(port_obj)
    
        #---------------------------
        # Start port configuration
        #---------------------------
        logging.info(f"#---------------------------")
        logging.info(f"# Start port configuration")
        logging.info(f"#---------------------------")

        logging.info(f"Reset the txport")
        await mgmt.reset_port(port_obj)

        logging.info(f"Configure the txport")
        await utils.apply(
            port_obj.comment.set(comment="this is a comment"),
            port_obj.tx_config.enable.set_on(),
            port_obj.latency_config.offset.set(offset=0),
            port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port_obj.tx_config.burst_period.set(burst_period=0),
            port_obj.tx_config.packet_limit.set(packet_count_limit=FRAME_COUNT),
            port_obj.max_header_length.set(max_header_length=128),
            port_obj.autotrain.set(interval=0),
            port_obj.loop_back.set_none(),                                # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port_obj.checksum.set(offset=0),
            port_obj.tx_config.delay.set(delay_val=0),
            port_obj.tpld_mode.set_normal(),
            port_obj.payload_mode.set_normal(),
            #txport.rate.pps.set(port_rate_pps=TRAFFIC_RATE_FPS),       # If you want to control traffic rate with FPS, uncomment this.
            port_obj.rate.fraction.set(TRAFFIC_RATE_PERCENT),             # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
        )
        if should_burst:
            await port_obj.tx_config.mode.set_burst()
        else:
            await port_obj.tx_config.mode.set_sequential()
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure stream on the txport")

        stream_0 = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = "aaaa.aaaa.0005"
        eth.dst_mac = "bbbb.bbbb.0005"
        eth.ethertype = "0800"

        ipv4 = headers.IPV4()
        ipv4.src = "1.1.1.5"
        ipv4.dst = "2.2.2.5"
        ipv4.proto = 6
        
        ipv6 = headers.IPV6()
        ipv6.src = "2001::5"
        ipv6.dst = "2002::5"

        tcp = headers.TCP()
        tcp.src_port = 4791
        tcp.dst_port = 80
        tcp.seq_num = 19
        tcp.ack_num = 31
        tcp.ae = 0
        tcp.cwr = 0
        tcp.ece = 0
        tcp.urg = 1
        tcp.ack = 0
        tcp.psh = 0
        tcp.rst = 1
        tcp.syn = 0
        tcp.fin = 1

        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=1),
            stream_0.comment.set(f"Stream TCP"),
            stream_0.rate.fraction.set(stream_rate_ppm=10000),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.TCPCHECK,
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(tcp))),
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
        await build_tcp_stream(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            should_burst=SHOULD_BURST)
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())