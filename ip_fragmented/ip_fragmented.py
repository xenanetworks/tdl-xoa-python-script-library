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
from xoa_driver.misc import Hex
from headers import *
from xoa_driver.hlfuncs import mgmt

#---------------------------
# Global parameters
#---------------------------

CHASSIS_IP = "10.165.136.70"    # Chassis IP address or hostname
USERNAME = "XOA"                # Username
MODULE_IDX = 3                  # Module index
PORT_IDX = 1                    # TX Port index

# This is the total IP data size, e.g. 72 bytes each fragments and 20 fragments in total
IP_DATA_TOTAL = 72*20
IP_FRAGMENTS = 20

TRAFFIC_RATE_FPS = 100          # Traffic rate in frames per second
TRAFFIC_RATE_PERCENT = int(4/10 * 1000000)

#------------------------------
# def my_awesome_func()
#------------------------------
async def my_awesome_func(stop_event: asyncio.Event) -> None:
    if IP_DATA_TOTAL % IP_FRAGMENTS != 0:
        raise Exception("IP_DATA_TOTAL % IP_FRAGMENTS != 0")
    
    size_per_frag = int(IP_DATA_TOTAL/IP_FRAGMENTS)
    if size_per_frag % 8 != 0:
        raise Exception("size_per_frag % 8 != 0")
    
    frame_size_bytes = size_per_frag + 14 + 4 + 20
    
    # create tester instance and establish connection
    tester = await testers.L23Tester(CHASSIS_IP, USERNAME, enable_logging=False) 

    # access the module on the tester
    module = tester.modules.obtain(MODULE_IDX)

    # check if the module is of type Loki-100G-5S-2P
    if not isinstance(module, modules.ModuleChimera):
        
        # access the txport on the module
        port = module.ports.obtain(PORT_IDX)

        #---------------------------
        # Port reservation
        #---------------------------
        print(f"#---------------------------")
        print(f"# Port reservation")
        print(f"#---------------------------")
        await mgmt.reserve_port(port)
        

        #---------------------------
        # Start port configuration
        #---------------------------
        print(f"#---------------------------")
        print(f"# Start port configuration")
        print(f"#---------------------------")

        print(f"Reset the txport")
        await mgmt.reset_port(port)

        print(f"Configure the txport")
        await utils.apply(
            port.comment.set(comment="this is a comment"),
            port.tx_config.enable.set_on(),
            port.latency_config.offset.set(offset=0),
            port.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port.tx_config.burst_period.set(burst_period=0),
            port.max_header_length.set(max_header_length=128),
            port.autotrain.set(interval=0),
            port.loop_back.set_none(),                                # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port.checksum.set(offset=0),
            port.tx_config.delay.set(delay_val=0),
            port.tpld_mode.set_normal(),
            port.payload_mode.set_normal(),
            #txport.rate.pps.set(port_rate_pps=TRAFFIC_RATE_FPS),       # If you want to control traffic rate with FPS, uncomment this.
            port.rate.fraction.set(TRAFFIC_RATE_PERCENT),             # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
        )

        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        print(f"   Configure stream on the txport")

        ip_stream = await port.streams.create()
        eth = Ethernet()
        eth.src_mac = "aaaa.aaaa.0005"
        eth.dst_mac = "bbbb.bbbb.0005"
        eth.ethertype = "0800"

        ipv4 = IPV4()
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
        await my_awesome_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())