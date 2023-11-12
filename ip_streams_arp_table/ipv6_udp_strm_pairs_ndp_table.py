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
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import ArpChunk, NdpChunk, Hex
import ipaddress
from binascii import hexlify

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
MODULE_INDEX = 8
PORT_INDEX_A = 0
PORT_INDEX_B = 1

#---------------------------
# STREAM ADDR
#---------------------------
PORT_A_IP_BASE = "fe80::10ba:9aa9:0002"
PORT_A_MAC_BASE = "AAAAAAAAAA00"
PORT_B_IP_BASE = "fe80::10bb:9aa9:0002"
PORT_B_MAC_BASE = "BBBBBBBBBB00"

#---------------------------
# STREAM PROPERTIES
#---------------------------
IP_PAIRS = 1500
FRAME_SIZE_BYTES = 128
STREAM_PPS = 100
TX_PKT_LIMIT = 1000

#---------------------------
# STREAM HEADER
#---------------------------
# ETHERNET HEADER
ETHERNET_TYPE =     "86DD"

# IPV6
VERSION = "6"
TRAFFIC_CLASS_FLOW_LABEL = "0000000"
PAYLOAD_LENGTH = "0000"
NEXT_HEADER = "11"
HOP_LIMIT = "FF"

# UDP
UDP_SRC_PORT = "0000"
UDP_DEST_PORT = "0000"
UDP_LEN = FRAME_SIZE_BYTES - 14 - 20 - 4
UDP_CHK = "0000"






#---------------------------
# NDP TABLE PORT A
#---------------------------
ndp_list_a=[]
mac_list_a = []
for i in range(IP_PAIRS):
    mac = "{:012X}".format(int(PORT_A_MAC_BASE, 16) + i)
    mac_string = ''.join(mac[j]+mac[j+1] for j in range(0, len(mac), 2))
    mac_list_a.append(mac_string)
for i in range(IP_PAIRS):
    temp = NdpChunk(
        ipv6_address=ipaddress.IPv6Address(PORT_A_IP_BASE) + i,
        prefix=21,
        patched_mac=enums.OnOff.OFF,
        mac_address=mac_list_a[i]
        )
    ndp_list_a.append(temp)

#---------------------------
# NDP TABLE PORT B
#---------------------------
ndp_list_b=[]
mac_list_b = []
for i in range(IP_PAIRS):
    mac = "{:012X}".format(int(PORT_B_MAC_BASE, 16) + i)
    mac_string = ''.join(mac[j]+mac[j+1] for j in range(0, len(mac), 2))
    mac_list_b.append(mac_string)
for i in range(256):
    temp = NdpChunk(
        ipv6_address=ipaddress.IPv6Address(PORT_B_IP_BASE) + i,
        prefix=32,
        patched_mac=enums.OnOff.OFF,
        mac_address=mac_list_b[i]
        )
    ndp_list_b.append(temp)


#---------------------------
# UDP FUNC
#---------------------------
async def udp_ipv6_config_func(stop_event: asyncio.Event):
    print(f"Making {IP_PAIRS} UDP stream pairs")
    # create tester instance and establish connection
    tester = await testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) 

    # access the module on the tester
    module = tester.modules.obtain(MODULE_INDEX)

    # check if the module is of Chimera
    if isinstance(module, modules.ModuleChimera):
        return

    # access the port on the module
    port_a = module.ports.obtain(PORT_INDEX_A)
    port_b = module.ports.obtain(PORT_INDEX_B)

    #---------------------------------------------------------------------------------
    # Port reservation (the logic will be abstracted as one func in xoa-driver 2.0)
    #---------------------------------------------------------------------------------
    await mgmt.reserve_port(port_a)
    await mgmt.reserve_port(port_b)

    #------------------------
    # Read port capabilities
    #------------------------
    resp_a = await port_a.capabilities.get()
    resp_b = await port_b.capabilities.get()
    if resp_a.max_modifiers < 6:
        print(f"Port A cannot support 6 modifiers (max modifier count is {resp_a.max_modifiers}). End")
        return None
    if resp_b.max_modifiers < 6:
        print(f"Port B cannot support 6 modifiers (max modifier count is {resp_b.max_modifiers}). End")
        return None

    #-------------------
    # Configure Port A
    # ------------------
    print(f"Reset Port A")
    await mgmt.reset_port(port_a)

    await asyncio.sleep(5)

    print(f"Configure Port A")
    await utils.apply(
        port_a.speed.mode.selection.set(mode=enums.PortSpeedMode.UNKNOWN),
        port_a.comment.set(comment="Port A"),
        port_a.tx_config.enable.set_on(),
        port_a.tx_config.packet_limit.set(packet_count_limit=TX_PKT_LIMIT),
        # Enable ARP and Ping reply on Port A
        port_a.net_config.ipv6.arp_reply.set_on(),
        port_a.net_config.ipv6.ping_reply.set_on(),

        # set ARP table for Port A
        port_a.ndp_rx_table.set(chunks=ndp_list_a),
    )
    
    # Create streams on the port and configure the streams
    print(f"Configure UDP streams A to B")
    stream_a = await port_a.streams.create()

    src_ip = ipaddress.IPv6Address(PORT_A_IP_BASE)
    hexlify(src_ip.packed).decode()
    dst_ip = ipaddress.IPv6Address(PORT_B_IP_BASE)
    hexlify(dst_ip.packed).decode()

    HEADER = f'{PORT_B_MAC_BASE}{PORT_A_MAC_BASE}{ETHERNET_TYPE}{VERSION}{TRAFFIC_CLASS_FLOW_LABEL}{PAYLOAD_LENGTH}{NEXT_HEADER}{HOP_LIMIT}{hexlify(src_ip.packed).decode()}{hexlify(dst_ip.packed).decode()}{UDP_SRC_PORT}{UDP_DEST_PORT}{UDP_LEN}{UDP_CHK}'
    
    await utils.apply(
        stream_a.enable.set_on(),
        stream_a.packet.limit.set(packet_count=-1),
        stream_a.comment.set(f"Stream A to B"),
        stream_a.rate.pps.set(stream_rate_pps=STREAM_PPS),
        
        stream_a.packet.header.protocol.set(segments=[
            enums.ProtocolOption.ETHERNET,
            enums.ProtocolOption.IPV6,
            enums.ProtocolOption.UDP
            ]),
        stream_a.packet.header.data.set(hex_data=Hex(HEADER)),

        stream_a.packet.length.set(length_type=enums.LengthType.FIXED, min_val=FRAME_SIZE_BYTES, max_val=FRAME_SIZE_BYTES),
        # stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data="0x0000FFFF0000FFFF0000FFFF0000FFFF"),
        stream_a.tpld_id.set(test_payload_identifier = 0),
        stream_a.insert_packets_checksum.set_on(),
        stream_a.gateway.ipv6.set(gateway=ipaddress.IPv6Address('::'))
    )
    # Configure a modifier on the stream
    await stream_a.packet.header.modifiers.configure(6)

    # Modifier on DMAC lowest two bytes (pos=4), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. BB:BB:BB:BB:00:00, BB:BB:BB:BB:00:01 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(0)
    await modifier_dmac.specification.set(position=4, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=IP_PAIRS-1)

    # Modifier on SMAC lowest two bytes (pos=10), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. AA:AA:AA:AA:00:00, AA:AA:AA:AA:00:01 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(1)
    await modifier_dmac.specification.set(position=10, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=IP_PAIRS-1)

    # Modifier on SRC IP lowest two bytes (pos=28), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.0.0.2, 10.0.0.3 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(2)
    await modifier_dmac.specification.set(position=34, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+IP_PAIRS-1)

    # Modifier on DST IP lowest two bytes (pos=32), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.1.0.2, 10.1.0.3 ...
    modifier_dmac = stream_a.packet.header.modifiers.obtain(3)
    await modifier_dmac.specification.set(position=52, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+IP_PAIRS-1)

    # Modifier on UDP SRC PORT (pos=34), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_a.packet.header.modifiers.obtain(4)
    await modifier_dmac.specification.set(position=54, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+IP_PAIRS-1)

    # Modifier on UDP DST PORT (pos=36), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_a.packet.header.modifiers.obtain(5)
    await modifier_dmac.specification.set(position=56, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+IP_PAIRS-1)

    #-------------------
    # Configure Port B
    # ------------------
    print(f"Reset Port B")
    await mgmt.reset_port(port_b)

    await asyncio.sleep(5)

    print(f"Configure Port B")
    await utils.apply(
        port_b.speed.mode.selection.set(mode=enums.PortSpeedMode.UNKNOWN),
        port_b.comment.set(comment="Port B"),
        port_b.tx_config.enable.set_on(),
        port_b.tx_config.packet_limit.set(packet_count_limit=TX_PKT_LIMIT),
        # Enable ARP and Ping reply on Port B
        port_b.net_config.ipv6.arp_reply.set_on(),
        port_b.net_config.ipv6.ping_reply.set_on(),

        # set ARP table for Port B
        port_b.ndp_rx_table.set(chunks=ndp_list_b),
    )
    
    # Create streams on the port and configure the streams
    print(f"Configure UDP streams B to A")
    stream_b = await port_b.streams.create()

    src_ip = ipaddress.IPv6Address(PORT_B_IP_BASE)
    hexlify(src_ip.packed).decode()
    dst_ip = ipaddress.IPv6Address(PORT_A_IP_BASE)
    hexlify(dst_ip.packed).decode()


    HEADER = f'{PORT_A_MAC_BASE}{PORT_B_MAC_BASE}{ETHERNET_TYPE}{VERSION}{TRAFFIC_CLASS_FLOW_LABEL}{PAYLOAD_LENGTH}{NEXT_HEADER}{HOP_LIMIT}{hexlify(src_ip.packed).decode()}{hexlify(dst_ip.packed).decode()}{UDP_SRC_PORT}{UDP_DEST_PORT}{UDP_LEN}{UDP_CHK}'
    
    await utils.apply(
        stream_b.enable.set_on(),
        stream_b.packet.limit.set(packet_count=-1),
        stream_b.comment.set(f"Stream B to A"),
        stream_b.rate.fraction.set(stream_rate_ppm=STREAM_PPS),
        
        stream_b.packet.header.protocol.set(segments=[
            enums.ProtocolOption.ETHERNET,
            enums.ProtocolOption.IPV6,
            enums.ProtocolOption.UDP
            ]),
        stream_b.packet.header.data.set(hex_data=Hex(HEADER)),

        stream_b.packet.length.set(length_type=enums.LengthType.FIXED, min_val=FRAME_SIZE_BYTES, max_val=FRAME_SIZE_BYTES),
        # stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data="0x0000FFFF0000FFFF0000FFFF0000FFFF"),
        stream_b.tpld_id.set(test_payload_identifier = 1),
        stream_b.insert_packets_checksum.set_on(),
        stream_b.gateway.ipv6.set(gateway=ipaddress.IPv6Address('::'))
    )
    # Configure a modifier on the stream
    await stream_b.packet.header.modifiers.configure(6)

    # Modifier on DMAC lowest two bytes (pos=4), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. AA:AA:AA:AA:00:00, AA:AA:AA:AA:00:01 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(0)
    await modifier_dmac.specification.set(position=4, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=IP_PAIRS-1)

    # Modifier on SMAC lowest two bytes (pos=10), range from 0 to IP_STREAM_CNT-1 in step of 1
    # e.g. BB:BB:BB:BB:00:00, BB:BB:BB:BB:00:01 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(1)
    await modifier_dmac.specification.set(position=10, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=0, step=1, max_val=IP_PAIRS-1)

    # Modifier on SRC IP lowest two bytes (pos=28), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.1.0.2, 10.1.0.3 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(2)
    await modifier_dmac.specification.set(position=34, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+IP_PAIRS-1)

    # Modifier on DST IP lowest two bytes (pos=32), range from 2 to 2+IP_STREAM_CNT-1 in step of 1
    # e.g. 10.0.0.2, 10.0.0.3 ...
    modifier_dmac = stream_b.packet.header.modifiers.obtain(3)
    await modifier_dmac.specification.set(position=52, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=2, step=1, max_val=2+IP_PAIRS-1)

    # Modifier on UDP SRC PORT (pos=34), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_b.packet.header.modifiers.obtain(4)
    await modifier_dmac.specification.set(position=54, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+IP_PAIRS-1)

    # Modifier on UDP DST PORT (pos=36), range from 4000 to 4000+IP_STREAM_CNT-1 in step of 1
    modifier_dmac = stream_b.packet.header.modifiers.obtain(5)
    await modifier_dmac.specification.set(position=56, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
    await modifier_dmac.range.set(min_val=4000, step=1, max_val=4000+IP_PAIRS-1)

    print(f"Done")

async def main():
    stop_event =asyncio.Event()
    try:
        await udp_ipv6_config_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())