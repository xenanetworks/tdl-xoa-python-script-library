################################################################
#
#               IPV4/IPv6 STREAM PAIRS & ARP/NDP TABLE
# 
# This example shows you how to configure ARP/NDP table that 
# matches the IP stream pairs.
#
################################################################

import asyncio
from contextlib import suppress
from xoa_driver import (
    testers,
    modules,
    ports,
    utils,
    enums,
    exceptions
)
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import ArpChunk, NdpChunk, Hex
import ipaddress
from binascii import hexlify
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
PORT_A = "0/0"
PORT_B ="0/1"

PORT_A_IPV4_BASE = "10.0.0.2"
PORT_A_IPV6_BASE = "fe80::10ba:9aa9:0002"
PORT_A_MAC_BASE = "aaaa.aaaa.aa00"
PORT_B_IPV4_BASE = "10.1.0.2"
PORT_B_IPV6_BASE = "fe80::10bb:9aa9:0002"
PORT_B_MAC_BASE = "bbbb.bbbb.bb00"

IP_PAIRS = 1500
FRAME_SIZE_BYTES = 128
STREAM_PPS = 100
TX_PKT_LIMIT = 1000

L3_PROTO = "ipv4" # or "ipv6"
L4_PROTO = "tcp" # or "udp"

#---------------------------
# prepare_arp_table
#---------------------------
def prepare_arp_table(ip_pairs: int, mac_base: str, ip_base: str, prefix: int) -> list[ArpChunk]:
    arp_list=[]
    mac_list = []
    for i in range(ip_pairs):
        mac = "{:012X}".format(int(mac_base.replace(".", ""), 16) + i)
        mac_string = ''.join(mac[j]+mac[j+1] for j in range(0, len(mac), 2))
        mac_list.append(mac_string)
    for i in range(ip_pairs):
        temp = ArpChunk(
            ipv4_address=ipaddress.IPv4Address(ip_base) + i,
            prefix=prefix,
            patched_mac=enums.OnOff.OFF,
            mac_address=mac_list[i]
            )
        arp_list.append(temp)
    return arp_list

#---------------------------
# prepare_ndp_table
#---------------------------
def prepare_ndp_table(ip_pairs: int, mac_base: str, ip_base: str, prefix: int) -> list[NdpChunk]:
    ndp_list=[]
    mac_list = []
    for i in range(ip_pairs):
        mac = "{:012X}".format(int(mac_base.replace(".", ""), 16) + i)
        mac_string = ''.join(mac[j]+mac[j+1] for j in range(0, len(mac), 2))
        mac_list.append(mac_string)
    for i in range(ip_pairs):
        temp = NdpChunk(
            ipv6_address=ipaddress.IPv6Address(ip_base) + i,
            prefix=prefix,
            patched_mac=enums.OnOff.OFF,
            mac_address=mac_list[i]
            )
        ndp_list.append(temp)
    return ndp_list

#---------------------------
# tcp_udp_ipv4_ipv6_config_func
#---------------------------
async def tcp_udp_ipv4_ipv6_config_func(chassis: str, username: str, port_str1: str, port_str2: str, stream_pair: int, mac_base1: str, mac_base2: str, ipv4_base1: str, ipv4_base2: str, ipv6_base1: str, ipv6_base2: str, pps: int, frame_size: int, limit: int, l3: str, l4: str):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    logging.info(f"Making {stream_pair} stream pairs")
    # create tester instance and establish connection
    tester = await testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) 

    logging.info(f"===================================")
    logging.info(f"{'Connect to chassis:':<20}{chassis}")
    logging.info(f"{'Username:':<20}{username}")

    # access the module on the tester
    _mid1 = int(port_str1.split("/")[0])
    _pid1 = int(port_str1.split("/")[1])
    _mid2 = int(port_str2.split("/")[0])
    _pid2 = int(port_str2.split("/")[1])
    module_obj_a = tester.modules.obtain(_mid1)
    module_obj_b = tester.modules.obtain(_mid2)

    # check if the module is of Chimera
    if isinstance(module_obj_a, modules.E100ChimeraModule):
        return
    if isinstance(module_obj_b, modules.E100ChimeraModule):
        return

    # access the port on the module
    port_obj_a = module_obj_a.ports.obtain(_pid1)
    port_obj_b = module_obj_b.ports.obtain(_pid2)

    #------------------
    # Port reservation 
    #------------------
    await mgmt.reserve_port(port_obj_a)
    await mgmt.reserve_port(port_obj_b)

    #------------------------
    # Read port capabilities
    #------------------------
    resp_a = await port_obj_a.capabilities.get()
    resp_b = await port_obj_b.capabilities.get()
    if resp_a.max_modifiers < 6:
        logging.info(f"Port A cannot support 6 modifiers (max modifier count is {resp_a.max_modifiers}). End")
        return None
    if resp_b.max_modifiers < 6:
        logging.info(f"Port B cannot support 6 modifiers (max modifier count is {resp_b.max_modifiers}). End")
        return None
    
    #-------------------
    # Configure Port A
    # ------------------
    logging.info(f"Reset Port A")
    await mgmt.reset_port(port_obj_a)

    await asyncio.sleep(5)

    logging.info(f"Configure Port A")
    await utils.apply(
        port_obj_a.comment.set(comment="Port A"),
        port_obj_a.tx_config.enable.set_on(),
        port_obj_a.tx_config.packet_limit.set(packet_count_limit=limit),
        # Enable ARP and Ping reply on Port A
        port_obj_a.net_config.ipv4.arp_reply.set_on(),
        port_obj_a.net_config.ipv4.ping_reply.set_on(),
    )
    # set ARP table for Port A
    _arp_list_a = prepare_arp_table(ip_pairs=stream_pair, mac_base=mac_base1, ip_base=ipv4_base1, prefix=24)
    await port_obj_a.arp_rx_table.set(chunks=_arp_list_a)

    # set NDP table for Port A
    _ndp_list_a = prepare_ndp_table(ip_pairs=stream_pair, mac_base=mac_base1, ip_base=ipv6_base1, prefix=24)
    await port_obj_a.ndp_rx_table.set(chunks=_ndp_list_a)
    
    # Create streams on the port and configure the streams
    logging.info(f"Configure streams A to B")
    stream_a = await port_obj_a.streams.create()

    eth = headers.Ethernet()
    eth.src_mac = mac_base1
    eth.dst_mac = mac_base2
    eth.ethertype = "0800"
    ipv4 = headers.IPV4()
    ipv4.src = ipv4_base1
    ipv4.dst = ipv4_base2
    ipv4.proto = 255
    ipv6 = headers.IPV6()
    ipv6.src = ipv6_base1
    ipv6.dst = ipv6_base2
    tcp = headers.TCP()
    tcp.src_port = 4791
    tcp.dst_port = 80
    tcp.seq_num = 0
    tcp.ack_num = 0
    tcp.ae = 0
    tcp.cwr = 0
    tcp.ece = 0
    tcp.urg = 1
    tcp.ack = 0
    tcp.psh = 0
    tcp.rst = 1
    tcp.syn = 0
    tcp.fin = 1
    udp = headers.UDP()
    udp.src_port = 0
    udp.dst_port = 0

    await utils.apply(
        stream_a.enable.set_on(),
        stream_a.packet.limit.set(packet_count=-1),
        stream_a.comment.set(f"Stream A to B"),
        stream_a.rate.pps.set(stream_rate_pps=pps),
        
        stream_a.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
        # stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data="0x0000FFFF0000FFFF0000FFFF0000FFFF"),
        stream_a.tpld_id.set(test_payload_identifier = 0),
        stream_a.insert_packets_checksum.set_on()
    )
    _segments=[enums.ProtocolOption.ETHERNET]
    _data = str(eth)
    if l3 == "ipv4":
        _segments.append(enums.ProtocolOption.IP)
        _data += str(ipv4)
    else:
        _segments.append(enums.ProtocolOption.IPV6)
        _data += str(ipv6)
    if l3 == "tcp":
        _segments.append(enums.ProtocolOption.TCPCHECK)
        _data += str(tcp)        
    else:
        _segments.append(enums.ProtocolOption.UDPCHECK)
        _data += str(udp)

    await utils.apply(
        stream_a.packet.header.protocol.set(segments=_segments),
        stream_a.packet.header.data.set(hex_data=Hex(_data)),
    )
        
    # Configure a modifier on the stream
    await stream_a.packet.header.modifiers.configure(6)

    # Modifier on DMAC lowest two bytes (pos=4), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. BB:BB:BB:BB:00:00, BB:BB:BB:BB:00:01 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(0)
    await modifier_dmac.specification.set(position=4, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=stream_pair-1)

    # Modifier on SMAC lowest two bytes (pos=10), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. AA:AA:AA:AA:00:00, AA:AA:AA:AA:00:01 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(1)
    await modifier_dmac.specification.set(position=10, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=stream_pair-1)

    # Modifier on SRC IP lowest two bytes (pos=28), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.0.0.2, 10.0.0.3 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(2)
    await modifier_dmac.specification.set(position=28, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+stream_pair-1)

    # Modifier on DST IP lowest two bytes (pos=32), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.1.0.2, 10.1.0.3 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(3)
    await modifier_dmac.specification.set(position=32, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+stream_pair-1)

    # Modifier on TCP SRC PORT (pos=34), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_a.packet.header.modifiers.obtain(4)
    await modifier_dmac.specification.set(position=34, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+stream_pair-1)

    # Modifier on TCP DST PORT (pos=36), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_a.packet.header.modifiers.obtain(5)
    await modifier_dmac.specification.set(position=36, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+stream_pair-1)

    #-------------------
    # Configure Port B
    # ------------------
    logging.info(f"Reset Port B")
    await mgmt.reset_port(port_obj_b)

    await asyncio.sleep(5)

    logging.info(f"Configure Port B")
    await utils.apply(
        port_obj_b.comment.set(comment="Port B"),
        port_obj_b.tx_config.enable.set_on(),
        port_obj_b.tx_config.packet_limit.set(packet_count_limit=limit),
        # Enable ARP and Ping reply on Port B
        port_obj_b.net_config.ipv4.arp_reply.set_on(),
        port_obj_b.net_config.ipv4.ping_reply.set_on()
    )
    # set ARP table for Port B
    _arp_list_b = prepare_arp_table(ip_pairs=stream_pair, mac_base=mac_base2, ip_base=ipv4_base2, prefix=24)
    await port_obj_b.arp_rx_table.set(chunks=_arp_list_b)

    # set NDP table for Port B
    _ndp_list_b = prepare_ndp_table(ip_pairs=stream_pair, mac_base=mac_base1, ip_base=ipv6_base2, prefix=24)
    await port_obj_b.ndp_rx_table.set(chunks=_ndp_list_b)
    
    # Create streams on the port and configure the streams
    logging.info(f"Configure streams B to A")
    stream_b = await port_obj_b.streams.create()

    eth = headers.Ethernet()
    eth.src_mac = mac_base2
    eth.dst_mac = mac_base1
    eth.ethertype = "0800"
    ipv4 = headers.IPV4()
    ipv4.src = ipv4_base2
    ipv4.dst = ipv4_base1
    ipv4.proto = 255
    ipv6 = headers.IPV6()
    ipv6.src = ipv6_base2
    ipv6.dst = ipv6_base1
    tcp = headers.TCP()
    tcp.src_port = 4791
    tcp.dst_port = 80
    tcp.seq_num = 0
    tcp.ack_num = 0
    tcp.ae = 0
    tcp.cwr = 0
    tcp.ece = 0
    tcp.urg = 1
    tcp.ack = 0
    tcp.psh = 0
    tcp.rst = 1
    tcp.syn = 0
    tcp.fin = 1
    udp = headers.UDP()
    udp.src_port = 0
    udp.dst_port = 0
    
    await utils.apply(
        stream_b.enable.set_on(),
        stream_b.packet.limit.set(packet_count=-1),
        stream_b.comment.set(f"Stream B to A"),
        stream_b.rate.fraction.set(stream_rate_ppm=pps),
        
        stream_b.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
        # stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data="0x0000FFFF0000FFFF0000FFFF0000FFFF"),
        stream_b.tpld_id.set(test_payload_identifier = 1),
        stream_b.insert_packets_checksum.set_on()
    )
    _segments=[enums.ProtocolOption.ETHERNET]
    _data = str(eth)
    if l3 == "ipv4":
        _segments.append(enums.ProtocolOption.IP)
        _data += str(ipv4)
    else:
        _segments.append(enums.ProtocolOption.IPV6)
        _data += str(ipv6)
    if l3 == "tcp":
        _segments.append(enums.ProtocolOption.TCPCHECK)
        _data += str(tcp)        
    else:
        _segments.append(enums.ProtocolOption.UDPCHECK)
        _data += str(udp)

    await utils.apply(
        stream_b.packet.header.protocol.set(segments=_segments),
        stream_b.packet.header.data.set(hex_data=Hex(_data)),
    )

    # Configure a modifier on the stream
    await stream_b.packet.header.modifiers.configure(6)

    # Modifier on DMAC lowest two bytes (pos=4), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. AA:AA:AA:AA:00:00, AA:AA:AA:AA:00:01 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(0)
    await modifier_dmac.specification.set(position=4, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=stream_pair-1)

    # Modifier on SMAC lowest two bytes (pos=10), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. BB:BB:BB:BB:00:00, BB:BB:BB:BB:00:01 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(1)
    await modifier_dmac.specification.set(position=10, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=stream_pair-1)

    # Modifier on SRC IP lowest two bytes (pos=28), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 110.1.0.2, 10.1.0.3 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(2)
    await modifier_dmac.specification.set(position=28, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+stream_pair-1)

    # Modifier on DST IP lowest two bytes (pos=32), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.0.0.2, 10.0.0.3 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(3)
    await modifier_dmac.specification.set(position=32, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+stream_pair-1)

    # Modifier on TCP SRC PORT (pos=34), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_b.packet.header.modifiers.obtain(4)
    await modifier_dmac.specification.set(position=34, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+stream_pair-1)

    # Modifier on TCP DST PORT (pos=36), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_b.packet.header.modifiers.obtain(5)
    await modifier_dmac.specification.set(position=36, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+stream_pair-1)

    logging.info(f"Done")
    
async def main():
    stop_event =asyncio.Event()
    try:
        await tcp_udp_ipv4_ipv6_config_func(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str1=PORT_A,
            port_str2=PORT_B,
            stream_pair=IP_PAIRS,
            mac_base1=PORT_A_MAC_BASE,
            mac_base2=PORT_B_MAC_BASE,
            ipv4_base1=PORT_A_IPV4_BASE,
            ipv4_base2=PORT_B_IPV4_BASE,
            ipv6_base1=PORT_A_IPV4_BASE,
            ipv6_base2=PORT_B_IPV4_BASE,
            pps = STREAM_PPS,
            frame_size=FRAME_SIZE_BYTES,
            limit=TX_PKT_LIMIT,
            l3=L3_PROTO,
            l4=L4_PROTO           
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())