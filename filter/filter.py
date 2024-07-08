################################################################
#
#                   PORT FILTER
#
# What this script shows you how to configure port filter, and
# how to read filtered traffic statistics
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
from ipaddress import IPv4Address
from binascii import hexlify

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "XOA"
TX_PORT = "2/3"
RX_PORT = "2/4"

#---------------------------
# port_filter
#---------------------------
async def port_filter(chassis: str, username: str, port_str1: str, port_str2: str):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        _mid1 = int(port_str1.split("/")[0])
        _pid1 = int(port_str1.split("/")[1])
        _mid2 = int(port_str2.split("/")[0])
        _pid2 = int(port_str2.split("/")[1])
        tx_module = tester.modules.obtain(_mid1)
        rx_module = tester.modules.obtain(_mid2)

        if isinstance(tx_module, modules.E100ChimeraModule):
            return None
        if isinstance(rx_module, modules.E100ChimeraModule):
            return None

        # Get the port object on module
        tx_port = tx_module.ports.obtain(_pid1)
        rx_port = rx_module.ports.obtain(_pid2)

        await mgmt.reserve_port(tx_port)
        await mgmt.reset_port(tx_port)
        await mgmt.reserve_port(rx_port)
        await mgmt.reset_port(rx_port)

        await asyncio.sleep(5)

        #### Configure TX Port ####
        await utils.apply(
            tx_port.comment.set(comment="my tx port"),
            tx_port.interframe_gap.set(min_byte_count=20),
            tx_port.loop_back.set(mode=enums.LoopbackMode.NONE),
        )

        # Create a stream on the tx port
        # Stream index is automatically assigned
        stream = await tx_port.streams.create()
        stream_index = stream.idx
        print(f"TX stream index: {stream_index}")

        # Simple batch configure the stream on the TX port
        await utils.apply(
            stream.tpld_id.set(test_payload_identifier=stream_index),
            stream.enable.set_on(),
            stream.comment.set(comment="my stream"),
            stream.rate.fraction.set(1_000_000), # this is ppm
            stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000),
        )

        # Configure packet header data
        eth = headers.Ethernet()
        eth.dst_mac = "0001.0100.0100"
        eth.src_mac = "aaaa.aaaa.aaaa"
        eth.ethertype = headers.EtherType.VLAN
        vlan = headers.VLAN()
        vlan.id = 100
        vlan.type = headers.EtherType.IPv4
        ip = headers.IPV4()
        ip.src = "1.1.1.1"
        ip.dst = "2.2.2.2"
        await stream.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.VLAN,
                enums.ProtocolOption.IP
            ])
        await stream.packet.header.data.set(Hex(str(eth)+str(vlan)+str(ip)))
        
        #### Configure RX Port ####
        await utils.apply(
            rx_port.comment.set(comment="my rx port"),
            rx_port.interframe_gap.set(min_byte_count=20),
            tx_port.loop_back.set(mode=enums.LoopbackMode.NONE),
        )

        # Configure match term on the RX port
        await rx_port.match_terms.create()
        match_term = rx_port.match_terms.obtain(0)
        await match_term.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.VLAN,
            ])
        await match_term.position.set(byte_offset=14) # on VLAN
        await match_term.match.set(mask=Hex("0FFF000000000000"), value=Hex("0064000000000000"))

        # Configure match term on the RX port
        await rx_port.length_terms.create()
        length_term = rx_port.length_terms.obtain(0)
        await length_term.length.set(length_check_type=enums.LengthCheckType.AT_LEAST, size=1000)

        # Configure filter on the RX port
        await rx_port.filters.create()
        filter = rx_port.filters.obtain(0)
        await filter.comment.set(comment="VLAN 100")
        await filter.condition.set(0,0,0,0,1,0)
        await filter.enable.set_on()
        
        #### Batch clear statistics ####
        await asyncio.gather(
            tx_port.statistics.tx.clear.set(),
            tx_port.statistics.rx.clear.set()
        )
        
        # Start traffic on the TX port
        await tx_port.traffic.state.set_start()

        await asyncio.sleep(1)

        #################################################
        #         TX Port Traffic Rate Statistics       #
        #################################################

        resp = await tx_port.interframe_gap.get()
        tx_ifg = resp.min_byte_count
        print(f"TX port inter-frame gap: {tx_ifg} bytes")

        resp = await stream.packet.length.get()
        tx_frame_size = resp.min_val
        print(f"TX port frame size: {tx_frame_size} bytes")

        resp = await rx_port.interframe_gap.get()
        rx_ifg = resp.min_byte_count
        print(f"RX port inter-frame gap: {rx_ifg} bytes")

        for i in range(10):
            filtered_stats = rx_port.statistics.rx.obtain_filter_statistics(0)

            # Query port-level traffic statistics
            resp1, resp2, resp3 = await asyncio.gather(
                tx_port.statistics.tx.total.get(),
                rx_port.statistics.rx.total.get(),
                filtered_stats.get(),
            )

            tx_bps_l2 = resp1.bit_count_last_sec
            tx_fps = resp1.packet_count_last_sec
            tx_bps_l1 = tx_fps*(tx_ifg+tx_frame_size)*8
            tx_byte = resp1.byte_count_since_cleared
            tx_pkt = resp1.packet_count_since_cleared

            print("*"*(i+1))
            print(f"TX bits per second (L1): {tx_bps_l1} bps")
            print(f"TX bits per second (L2): {tx_bps_l2} bps")
            print(f"TX frames per second: {tx_fps} fps")
            print(f"TX bytes (total): {tx_byte} bytes")
            print(f"TX frames (tota): {tx_pkt} frames")

            # resp = await rx_port.statistics.rx.total.get()
            
            rx_bps_l2 = resp2.bit_count_last_sec
            rx_fps = resp2.packet_count_last_sec
            rx_bps_l1 = rx_fps*rx_ifg*8 + rx_bps_l2
            rx_byte = resp2.byte_count_since_cleared
            rx_pkt = resp2.packet_count_since_cleared

            print(f"RX bits per second (L1): {rx_bps_l1} bps")
            print(f"RX bits per second (L2): {rx_bps_l2} bps")
            print(f"RX frames per second: {rx_fps} fps")
            print(f"RX bytes (total): {tx_byte} bytes")
            print(f"RX frames (tota): {tx_pkt} frames")

            rx_filtered_bps_l2 = resp3.bit_count_last_sec
            rx_filtered_fps = resp3.packet_count_last_sec
            rx_filtered_bps_l1 = rx_filtered_fps*rx_ifg*8 + rx_filtered_bps_l2
            rx_filtered_byte = resp3.byte_count_since_cleared
            rx_filtered_pkt = resp3.packet_count_since_cleared

            print(f"RX filtered bits per second (L1): {rx_filtered_bps_l1} bps")
            print(f"RX filtered bits per second (L2): {rx_filtered_bps_l2} bps")
            print(f"RX filtered frames per second: {rx_filtered_fps} fps")
            print(f"RX filtered bytes (total): {rx_filtered_byte} bytes")
            print(f"RX filtered frames (tota): {rx_filtered_pkt} frames")

            await asyncio.sleep(1)

        # Stop traffic on the TX port
        await tx_port.traffic.state.set_stop()

        # Stop filter on RX port
        await filter.enable.set_off()

        #################################################
        #                  Release                      #
        #################################################
        # Release the ports
        await tx_port.reservation.set_release()
        await rx_port.reservation.set_release()

async def main():
    stop_event = asyncio.Event()
    try:
        await port_filter(CHASSIS_IP, USERNAME, TX_PORT, RX_PORT)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())
