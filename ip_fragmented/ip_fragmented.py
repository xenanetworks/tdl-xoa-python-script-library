################################################################
#
#                   IP FRAGMENTATION
#
# This script shows you how emulate IP fragmentation
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

CHASSIS_IP = "10.165.136.70"    # Chassis IP address or hostname
USERNAME = "XOA"                # Username
PORT = "3/1"

# This is the total IP data size, e.g. 72 bytes each fragments and 20 fragments in total
IP_DATA_TOTAL = 72*20
IP_FRAGMENTS = 20

TRAFFIC_RATE_FPS = 100          # Traffic rate in frames per second
TRAFFIC_RATE_PERCENT = int(4/10 * 1000000)

#------------------------------
# ip_fragmentation
#------------------------------
async def ip_fragmentation(chassis: str, username: str, port_str: str) -> None:
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    if IP_DATA_TOTAL % IP_FRAGMENTS != 0:
        raise Exception("IP_DATA_TOTAL % IP_FRAGMENTS != 0")
    
    size_per_frag = int(IP_DATA_TOTAL/IP_FRAGMENTS)
    if size_per_frag % 8 != 0:
        raise Exception("size_per_frag % 8 != 0")
    
    frame_size_bytes = size_per_frag + 14 + 4 + 20
    
    # create tester instance and establish connection
    tester = await testers.L23Tester(chassis, username, enable_logging=False) 

    # access the module on the tester
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = tester.modules.obtain(_mid)

    # check if the module is of type Loki-100G-5S-2P
    if not isinstance(module_obj, modules.ModuleChimera):
        
        # access the txport on the module
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

        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure stream on the txport")

        ip_stream = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = "aaaa.aaaa.0005"
        eth.dst_mac = "bbbb.bbbb.0005"
        eth.ethertype = "0800"

        ipv4 = headers.IPV4()
        ipv4.src = "1.1.1.5"
        ipv4.dst = "2.2.2.5"
        ipv4.proto = 255

        await utils.apply(
            ip_stream.enable.set_on(),
            ip_stream.comment.set(f"IP Fragment Stream"),
            ip_stream.rate.fraction.set(stream_rate_ppm=10000),
            ip_stream.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP
                ]),
            ip_stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4))),
            ip_stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size_bytes, max_val=frame_size_bytes),
            ip_stream.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            ip_stream.tpld_id.set(test_payload_identifier = -1),
            ip_stream.insert_packets_checksum.set_on()
        )

        # use modifier to simulate IP fragmentation
        # create 2 modifiers
        await ip_stream.packet.header.modifiers.configure(2)

        # place the 1st modifier on IP.Flags.MoreFragments
        mod_0 = ip_stream.packet.header.modifiers.obtain(0)
        await mod_0.specification.set(position=20, mask=Hex("E0000000"), action=enums.ModifierAction.DEC, repetition=IP_FRAGMENTS-1) 
        await mod_0.range.set(min_val=0, step=1, max_val=1)

        # place the 2nd modifier on IP.FragmentOffset
        mod_1 = ip_stream.packet.header.modifiers.obtain(1)
        await mod_1.specification.set(position=20, mask=Hex("1FFF0000"), action=enums.ModifierAction.INC, repetition=1) 
        await mod_1.range.set(min_val=0, step=int(size_per_frag/8), max_val=int(int(size_per_frag/8)*(IP_FRAGMENTS-1)))

async def main():
    stop_event =asyncio.Event()
    try:
        await ip_fragmentation(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())