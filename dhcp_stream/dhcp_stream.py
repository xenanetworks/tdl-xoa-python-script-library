################################################################
#
#                   DHCP STREAM
#
# What this script shows you how to configure a DHCP stream 
# on a port.
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
#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.70"
USERNAME = "XOA"
TX_PORT = "3/1"

#---------------------------
# dhcp_stream
#---------------------------
async def dhcp_stream(chassis: str, username: str, port_str: str,):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        _mid1 = int(port_str.split("/")[0])
        _pid1 = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid1)

        if isinstance(module_obj, modules.E100ChimeraModule):
            return None

        # Get the port object on module
        port_obj = module_obj.ports.obtain(_pid1)

        await mgmt.reserve_port(port_obj, reset=True)
        

        await asyncio.sleep(2)

        #### Configure TX Port ####
        await utils.apply(
            port_obj.comment.set(comment="my tx port"),
            port_obj.interframe_gap.set(min_byte_count=20),
            port_obj.loop_back.set(mode=enums.LoopbackMode.NONE),
            port_obj.max_header_length.set(max_header_length=512)
        )

        # Create a stream on the tx port
        # Stream index is automatically assigned
        stream = await port_obj.streams.create()
        stream_index = stream.idx
        print(f"DHCP stream index: {stream_index}")

        # Simple batch configure the stream on the TX port
        await utils.apply(
            stream.tpld_id.set(test_payload_identifier=-1),
            stream.enable.set_on(),
            stream.comment.set(comment="my stream"),
            stream.rate.fraction.set(1_000_000), # this is ppm
            stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=314, max_val=314),
            stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex("00")),
        )

        # Configure packet header data
        eth = headers.Ethernet()
        eth.dst_mac = "ffff.ffff.ffff"
        eth.src_mac = "aaaa.aaaa.aaaa"
        eth.ethertype = headers.EtherType.IPv4
        
        ip = headers.IPV4()
        ip.src = "0.0.0.0"
        ip.dst = "255.255.255.255"
        ip.total_length = 300
        ip.proto = headers.IPProtocol.UDP

        udp = headers.UDP()
        udp.src_port = 68
        udp.dst_port = 67
        udp.length = 280

        dhcp = headers.DHCPV4()
        dhcp.xid = "00003d1d"
        dhcp.chaddr = "aaaa.aaaa.aaaa"

        dhcp_option_1 = headers.DHCPOptionMessageType()
        dhcp_option_2 = headers.DHCPOptionClientIdentifier()
        dhcp_option_2.client_mac = "aaaa.aaaa.aaaa"
        dhcp_option_3 = headers.DHCPOptionRequestedIP()
        dhcp_option_4 = headers.DHCPOptionParamRequestList()
        dhcp_option_4.req_list = [1,3,6,42]
        dhcp_option_5 = headers.DHCPOptionEnd()

        await stream.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption.DHCPV4,
            ])
        await stream.packet.header.data.set(Hex(str(eth)+str(ip)+str(udp)+str(dhcp)+str(dhcp_option_1)+str(dhcp_option_2)+str(dhcp_option_3)+str(dhcp_option_4)+str(dhcp_option_5)))


        #################################################
        #                  Release                      #
        #################################################
        # Release the ports
        await port_obj.reservation.set_release()


async def main():
    stop_event = asyncio.Event()
    try:
        await dhcp_stream(CHASSIS_IP, USERNAME, TX_PORT)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())
