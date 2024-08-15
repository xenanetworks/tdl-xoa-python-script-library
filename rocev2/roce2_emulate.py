################################################################
#
#                   ROCEV2 EMULATION
#
# This script shows you how to simulate a RoCEv2 flow
# on a port.
# 
# ipv6_rocev2_rc_send() emulates RoCEv2 RC SEND (IPv6)
# ipv6_rocev2_ud_send() emulates RoCEv2 UD SEND (IPv6)
# ipv4_rocev2_rc_send() emulates RoCEv2 RC SEND (IPv4)
# ipv4_rocev2_ud_send() emulates RoCEv2 UD SEND (IPv4)
#
################################################################
import asyncio
from contextlib import suppress
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver import exceptions
from ipaddress import IPv4Address, IPv6Address
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt, headers
import logging
from headers import *

#---------------------------
# Global parameters
#---------------------------

CHASSIS_IP = "10.165.136.66"       # Chassis IP address or hostname
USERNAME = "XOA"                    # Username
PORT = "0/0"

FRAME_SIZE_BYTES = 4500             # Frame size on wire including the FCS.
FRAMES_PER_ROCEV2_FLOW = 20        # The number of frames including the first, the middle, and the last.
FLOW_REPEAT = 0                     # The number of repetitions of the frame sequence, set to 0 if you want the port to repeat over and over
RATE_FPS = 100                      # Traffic rate in frames per second
RATE_PERCENT = 0.4                  # Traffic rate in percent

SHOULD_BURST = False            # Whether the middle frames should be bursty
BURST_SIZE_FRAMES = 9           # Burst size in frames for the middle frames
INTER_BURST_GAP_BYTES = 3000    # The inter-burst gap in bytes
INTER_PACKET_GAP = 1000         # The inter-frame gap within a burst, aka. intra-burst gap, in bytes

SRC_MAC = "aaaa.0a0a.0a0a"
DST_MAC = "aaaa.0a0a.0a14"

SRC_IPV4 = "10.10.10.10"
DST_IPV4 = "10.10.10.20"

SRC_IPV6 = "2000::10"
DST_IPV6 = "2000::20"

RC_SEND_DST_QP = 5

UD_SEND_SRC_QP = 10
UD_SEND_DST_QP = 11
UD_SEND_Q_KEY = 1234

DELAY_AFTER_RESET = 2

#------------------------------
# ipv6_rocev2_rc_send
#------------------------------
async def ipv6_rocev2_rc_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, traffic_rate_percent: float, should_burst: bool, burst_size: int, inter_burst_gap: int, inter_pkt_gap: int, src_mac: str, dst_mac: str, src_ipv6: str, dst_ipv6: str, dst_qp: int, delay_after_reset: int) -> None:

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="ipv6_rocev2_rc_send.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Port Traffic Rate:       {traffic_rate_percent*100}%")
        logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
        logging.info(f"RoCEv2 Flow Type:        RC SEND")
        logging.info(f"Frames Per Flow:         {frames_per_flow}")
        logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
        logging.info(f"Flow Repeat:             {flow_repeat}")
        logging.info(f"Burst Traffic:           {should_burst}")
        logging.info(f"Burst Size:              {burst_size} frames")
        logging.info(f"Inter-burst Gap:         {inter_burst_gap} bytes")
        logging.info(f"Inter-packet Gap:        {inter_pkt_gap} bytes")
        logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
        logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
        logging.info(f"RoCEv2 Flow IPv6 (Src):  {src_ipv6}")
        logging.info(f"RoCEv2 Flow IPv6 (Dst):  {dst_ipv6}")
        logging.info(f"RoCEv2 QP (Dst):         {dst_qp}")
        logging.info(f"#####################################################################")

        # access the module and port on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        # check if the module is of type Chimera
        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.warning(f"Module {_mid} is E100 Chimera module. Abort.")
            return
        
        port_obj = module_obj.ports.obtain(_pid)

        # reserve ports
        await mgmt.free_module(module_obj)
        await mgmt.reserve_port(port_obj)
        await mgmt.reset_port(port_obj)

        await asyncio.sleep(delay_after_reset)

        logging.info(f"Configure port {port_str}")
        await utils.apply(
            # txport.speed.mode.selection.set(mode=enums.PortSpeedMode.F100G),
            port_obj.comment.set(comment="IPv6 RoCEv2 RC SEND"),
            port_obj.tx_config.enable.set_on(),
            port_obj.latency_config.offset.set(offset=0),
            port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port_obj.tx_config.burst_period.set(burst_period=0),
            port_obj.tx_config.packet_limit.set(packet_count_limit=int(frames_per_flow*flow_repeat)),
            port_obj.max_header_length.set(max_header_length=128),
            port_obj.autotrain.set(interval=0),
            port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port_obj.checksum.set(offset=0),
            port_obj.tx_config.delay.set(delay_val=0),
            port_obj.tpld_mode.set_normal(),
            port_obj.payload_mode.set_normal(),
            #port_obj.rate.pps.set(port_rate_pps=1_000), # If you want to control traffic rate with FPS, uncomment this.
            port_obj.rate.fraction.set(int(traffic_rate_percent*1_000_000)),  # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
        )
        if should_burst:
            await port_obj.tx_config.mode.set_burst()
        else:
            await port_obj.tx_config.mode.set_sequential()
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND FIRST stream on port {port_str}")

        stream_0 = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = src_mac
        eth.dst_mac = dst_mac
        eth.ethertype = headers.EtherType.IPv6
        ipv6 = headers.IPV6()
        ipv6.src = src_ipv6
        ipv6.dst = dst_ipv6
        ipv6.next_header = headers.IPProtocol.UDP
        udp = headers.UDP()
        udp.src_port = 4791
        udp.dst_port = 4791
        ib = IB()
        ib.bth.opcode = BTHOpcode.RC_SEND_FIRST
        ib.bth.destqp = dst_qp
        ib.bth.psn = 0
        _raw_header = "RAW_"+str(int(len(str(ib))/2))
        
        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=1),
            stream_0.comment.set(f"IPV6 RC SEND FIRST"),
            stream_0.rate.fraction.set(stream_rate_ppm=10000),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IPV6,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv6)+str(udp)+str(ib))),
            stream_0.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_0.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_0.tpld_id.set(test_payload_identifier = stream_0.kind.index_id),
            stream_0.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_0.burst.burstiness.set(size=1, density=100)
            await stream_0.burst.gap.set(inter_packet_gap=0, inter_burst_gap=0)

        #--------------------------------------
        # Configure stream_1 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND MIDDLE stream on port {port_str}")

        stream_1 = await port_obj.streams.create()

        ib.bth.opcode = BTHOpcode.RC_SEND_MIDDLE
        ib.bth.destqp = dst_qp
        ib.bth.psn = 1
        _raw_header = "RAW_"+str(int(len(str(ib))/2))

        await utils.apply(
            stream_1.enable.set_on(),
            stream_1.packet.limit.set(packet_count=frames_per_flow-2),
            stream_1.comment.set(f"IPV6 RC SEND MIDDLE"),
            stream_1.rate.fraction.set(stream_rate_ppm=10000),
            stream_1.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IPV6,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_1.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv6)+str(udp)+str(ib))),
            stream_1.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_1.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_1.tpld_id.set(test_payload_identifier = stream_1.kind.index_id),
            stream_1.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_1.burst.burstiness.set(size=burst_size, density=100)
            await stream_1.burst.gap.set(inter_packet_gap=inter_pkt_gap, inter_burst_gap=inter_burst_gap)

        # Configure a modifier on the stream_1
        await stream_1.packet.header.modifiers.configure(1)

        # Modifier on the SQN
        modifier = stream_1.packet.header.modifiers.obtain(0)
        sqn_pos = int(len(str(eth)+str(ipv6)+str(udp))/2)+10
        await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
        await modifier.range.set(min_val=1, step=1, max_val=frames_per_flow-2)


        #--------------------------------------
        # Configure stream_2 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND LAST stream on port {port_str}")

        stream_2 = await port_obj.streams.create()

        ib.bth.opcode = BTHOpcode.RC_SEND_LAST
        ib.bth.destqp = dst_qp
        ib.bth.psn = frames_per_flow-1
        _raw_header = "RAW_"+str(int(len(str(ib))/2))

        await utils.apply(
            stream_2.enable.set_on(),
            stream_2.packet.limit.set(packet_count=1),
            stream_2.comment.set(f"IPV6 RC SEND LAST"),
            stream_2.rate.fraction.set(stream_rate_ppm=10000),
            stream_2.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IPV6,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_2.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv6)+str(udp)+str(ib))),
            stream_2.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_2.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_2.tpld_id.set(test_payload_identifier = stream_2.kind.index_id),
            stream_2.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_2.burst.burstiness.set(size=1, density=100)
            await stream_2.burst.gap.set(inter_packet_gap=0, inter_burst_gap=0)

        # free the port
        await mgmt.free_port(port_obj)
        logging.info(f"Configuration complete")


#-----------------------------
# ipv4_rocev2_rc_send
#------------------------------
async def ipv4_rocev2_rc_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, traffic_rate_percent: float, should_burst: bool, burst_size: int, inter_burst_gap: int, inter_pkt_gap: int, src_mac: str, dst_mac: str, src_ipv4: str, dst_ipv4: str, dst_qp: int, delay_after_reset: int) -> None:

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="ipv4_rocev2_rc_send.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Port Traffic Rate:       {traffic_rate_percent*100}%")
        logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
        logging.info(f"RoCEv2 Flow Type:        RC SEND")
        logging.info(f"Frames Per Flow:         {frames_per_flow}")
        logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
        logging.info(f"Flow Repeat:             {flow_repeat}")
        logging.info(f"Burst Traffic:           {should_burst}")
        logging.info(f"Burst Size:              {burst_size} frames")
        logging.info(f"Inter-burst Gap:         {inter_burst_gap} bytes")
        logging.info(f"Inter-packet Gap:        {inter_pkt_gap} bytes")
        logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
        logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
        logging.info(f"RoCEv2 Flow IPv4 (Src):  {src_ipv4}")
        logging.info(f"RoCEv2 Flow IPv4 (Dst):  {dst_ipv4}")
        logging.info(f"RoCEv2 QP (Dst):         {dst_qp}")
        logging.info(f"#####################################################################")

        # access the module and port on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        # check if the module is of type Chimera
        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.warning(f"Module {_mid} is E100 Chimera module. Abort.")
            return
        
        port_obj = module_obj.ports.obtain(_pid)

        # reserve ports
        await mgmt.free_module(module_obj)
        await mgmt.reserve_port(port_obj)
        await mgmt.reset_port(port_obj)

        await asyncio.sleep(delay_after_reset)

        logging.info(f"Configure port {port_str}")
        await utils.apply(
            # txport.speed.mode.selection.set(mode=enums.PortSpeedMode.F100G),
            port_obj.comment.set(comment="IPv4 RoCEv2 RC SEND"),
            port_obj.tx_config.enable.set_on(),
            port_obj.latency_config.offset.set(offset=0),
            port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port_obj.tx_config.burst_period.set(burst_period=0),
            port_obj.tx_config.packet_limit.set(packet_count_limit=int(frames_per_flow*flow_repeat)),
            port_obj.max_header_length.set(max_header_length=128),
            port_obj.autotrain.set(interval=0),
            port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port_obj.checksum.set(offset=0),
            port_obj.tx_config.delay.set(delay_val=0),
            port_obj.tpld_mode.set_normal(),
            port_obj.payload_mode.set_normal(),
            #port_obj.rate.pps.set(port_rate_pps=1_000), # If you want to control traffic rate with FPS, uncomment this.
            port_obj.rate.fraction.set(int(traffic_rate_percent*1_000_000)),  # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
        )
        if should_burst:
            await port_obj.tx_config.mode.set_burst()
        else:
            await port_obj.tx_config.mode.set_sequential()
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND FIRST stream on port {port_str}")

        stream_0 = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = src_mac
        eth.dst_mac = dst_mac
        eth.ethertype = headers.EtherType.IPv4
        ipv4 = headers.IPV4()
        ipv4.src = src_ipv4
        ipv4.dst = dst_ipv4
        ipv4.proto = headers.IPProtocol.UDP
        udp = headers.UDP()
        udp.src_port = 4791
        udp.dst_port = 4791
        ib = IB()
        ib.bth.opcode = BTHOpcode.RC_SEND_FIRST
        ib.bth.destqp = dst_qp
        ib.bth.psn = 0
        _raw_header = "RAW_"+str(int(len(str(ib))/2))
        
        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=1),
            stream_0.comment.set(f"IPV4 RC SEND FIRST"),
            stream_0.rate.fraction.set(stream_rate_ppm=10000),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp)+str(ib))),
            stream_0.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_0.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_0.tpld_id.set(test_payload_identifier = stream_0.kind.index_id),
            stream_0.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_0.burst.burstiness.set(size=1, density=100)
            await stream_0.burst.gap.set(inter_packet_gap=0, inter_burst_gap=0)

        #--------------------------------------
        # Configure stream_1 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND MIDDLE stream on port {port_str}")

        stream_1 = await port_obj.streams.create()

        ib.bth.opcode = BTHOpcode.RC_SEND_MIDDLE
        ib.bth.destqp = dst_qp
        ib.bth.psn = 1
        _raw_header = "RAW_"+str(int(len(str(ib))/2))

        await utils.apply(
            stream_1.enable.set_on(),
            stream_1.packet.limit.set(packet_count=frames_per_flow-2),
            stream_1.comment.set(f"IPV4 RC SEND MIDDLE"),
            stream_1.rate.fraction.set(stream_rate_ppm=10000),
            stream_1.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_1.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp)+str(ib))),
            stream_1.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_1.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_1.tpld_id.set(test_payload_identifier = stream_1.kind.index_id),
            stream_1.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_1.burst.burstiness.set(size=burst_size, density=100)
            await stream_1.burst.gap.set(inter_packet_gap=inter_pkt_gap, inter_burst_gap=inter_burst_gap)

        # Configure a modifier on the stream_1
        await stream_1.packet.header.modifiers.configure(1)

        # Modifier on the SQN
        modifier = stream_1.packet.header.modifiers.obtain(0)
        sqn_pos = int(len(str(eth)+str(ipv4)+str(udp))/2)+10
        await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
        await modifier.range.set(min_val=1, step=1, max_val=frames_per_flow-2)


        #--------------------------------------
        # Configure stream_2 on the txport
        #--------------------------------------
        logging.info(f"   Configure RC SEND LAST stream on port {port_str}")

        stream_2 = await port_obj.streams.create()

        ib.bth.opcode = BTHOpcode.RC_SEND_LAST
        ib.bth.destqp = dst_qp
        ib.bth.psn = frames_per_flow-1
        _raw_header = "RAW_"+str(int(len(str(ib))/2))

        await utils.apply(
            stream_2.enable.set_on(),
            stream_2.packet.limit.set(packet_count=1),
            stream_2.comment.set(f"IPV4 RC SEND LAST"),
            stream_2.rate.fraction.set(stream_rate_ppm=10000),
            stream_2.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_2.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp)+str(ib))),
            stream_2.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_2.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_2.tpld_id.set(test_payload_identifier = stream_2.kind.index_id),
            stream_2.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_2.burst.burstiness.set(size=1, density=100)
            await stream_2.burst.gap.set(inter_packet_gap=0, inter_burst_gap=0)

        # free the port
        await mgmt.free_port(port_obj)
        logging.info(f"Configuration complete")


#------------------------------
# ipv6_rocev2_ud_send
#------------------------------
async def ipv6_rocev2_ud_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, traffic_rate_percent: float, should_burst: bool, burst_size: int, src_mac: str, dst_mac: str, src_ipv6: str, dst_ipv6: str, dst_qp: int, src_qp: int, q_key: int, delay_after_reset: int) -> None:

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="ipv6_rocev2_ud_send.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Port Traffic Rate:       {traffic_rate_percent*100}%")
        logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
        logging.info(f"RoCEv2 Flow Type:        UD SEND")
        logging.info(f"Frames Per Flow:         {frames_per_flow}")
        logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
        logging.info(f"Flow Repeat:             {flow_repeat}")
        logging.info(f"Burst Traffic:           {should_burst}")
        logging.info(f"Burst Size:              {burst_size} frames")
        logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
        logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
        logging.info(f"RoCEv2 Flow IPv6 (Src):  {src_ipv6}")
        logging.info(f"RoCEv2 Flow IPv6 (Dst):  {dst_ipv6}")
        logging.info(f"RoCEv2 QP (Src):         {src_qp}")
        logging.info(f"RoCEv2 QP (Dst):         {dst_qp}")
        logging.info(f"#####################################################################")

        # access the module and port on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        # check if the module is of type Chimera
        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.warning(f"Module {_mid} is E100 Chimera module. Abort.")
            return
        
        port_obj = module_obj.ports.obtain(_pid)

        # reserve ports
        await mgmt.free_module(module_obj)
        await mgmt.reserve_port(port_obj)
        await mgmt.reset_port(port_obj)

        await asyncio.sleep(delay_after_reset)

        logging.info(f"Configure port {port_str}")
        await utils.apply(
            # txport.speed.mode.selection.set(mode=enums.PortSpeedMode.F100G),
            port_obj.comment.set(comment="IPv6 RoCEv2 UD SEND emulation"),
            port_obj.tx_config.enable.set_on(),
            port_obj.latency_config.offset.set(offset=0),
            port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port_obj.tx_config.burst_period.set(burst_period=0),
            # port_obj.tx_config.packet_limit.set(packet_count_limit=int(frames_per_flow*flow_repeat)),
            port_obj.max_header_length.set(max_header_length=128),
            port_obj.autotrain.set(interval=0),
            port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port_obj.checksum.set(offset=0),
            port_obj.tx_config.delay.set(delay_val=0),
            port_obj.tpld_mode.set_normal(),
            port_obj.payload_mode.set_normal(),
            #port_obj.rate.pps.set(port_rate_pps=1_000), # If you want to control traffic rate with FPS, uncomment this.
            # port_obj.rate.fraction.set(int(traffic_rate_percent*1_000_000)),  # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
            port_obj.tx_config.mode.set_normal(),
        )
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure UD SEND on port {port_str}")

        stream_0 = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = src_mac
        eth.dst_mac = dst_mac
        eth.ethertype = headers.EtherType.IPv6
        ipv6 = headers.IPV6()
        ipv6.src = src_ipv6
        ipv6.dst = dst_ipv6
        ipv6.next_header = headers.IPProtocol.UDP
        udp = headers.UDP()
        udp.src_port = 4791
        udp.dst_port = 4791
        ib = IB()
        ib.bth.opcode = BTHOpcode.UD_SEND_ONLY
        ib.bth.destqp = dst_qp
        ib.bth.psn = 0
        ib.deth.src_qp = src_qp
        ib.deth.q_key = q_key
        _raw_header = "RAW_"+str(int(len(str(ib))/2))
        
        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=int(frames_per_flow*flow_repeat)),
            stream_0.comment.set(f"IPV6 UD SEND"),
            stream_0.rate.fraction.set(stream_rate_ppm=int(traffic_rate_percent*1_000_000)),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IPV6,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv6)+str(udp)+str(ib))),
            stream_0.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_0.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_0.tpld_id.set(test_payload_identifier = stream_0.kind.index_id),
            stream_0.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_0.burst.burstiness.set(size=burst_size, density=100)

        # Configure a modifier on the stream_0
        await stream_0.packet.header.modifiers.configure(1)

        # Modifier on the SQN
        modifier = stream_0.packet.header.modifiers.obtain(0)
        sqn_pos = int(len(str(eth)+str(ipv6)+str(udp))/2)+10
        await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
        await modifier.range.set(min_val=0, step=1, max_val=frames_per_flow-1)

        # free the port
        await mgmt.free_port(port_obj)
        logging.info(f"Configuration complete")


#------------------------------
# ipv4_rocev2_ud_send
#------------------------------
async def ipv4_rocev2_ud_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, traffic_rate_percent: float, should_burst: bool, burst_size: int, src_mac: str, dst_mac: str, src_ipv4: str, dst_ipv4: str, dst_qp: int, src_qp: int, q_key: int, delay_after_reset: int) -> None:

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="ipv4_rocev2_ud_send.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")
        logging.info(f"Port Traffic Rate:       {traffic_rate_percent*100}%")
        logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
        logging.info(f"RoCEv2 Flow Type:        UD SEND")
        logging.info(f"Frames Per Flow:         {frames_per_flow}")
        logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
        logging.info(f"Flow Repeat:             {flow_repeat}")
        logging.info(f"Burst Traffic:           {should_burst}")
        logging.info(f"Burst Size:              {burst_size} frames")
        logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
        logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
        logging.info(f"RoCEv2 Flow IPv4 (Src):  {src_ipv4}")
        logging.info(f"RoCEv2 Flow IPv4 (Dst):  {dst_ipv4}")
        logging.info(f"RoCEv2 QP (Src):         {src_qp}")
        logging.info(f"RoCEv2 QP (Dst):         {dst_qp}")
        logging.info(f"#####################################################################")

        # access the module and port on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        # check if the module is of type Chimera
        if isinstance(module_obj, modules.E100ChimeraModule):
            logging.warning(f"Module {_mid} is E100 Chimera module. Abort.")
            return
        
        port_obj = module_obj.ports.obtain(_pid)

        # reserve ports
        await mgmt.free_module(module_obj)
        await mgmt.reserve_port(port_obj)
        await mgmt.reset_port(port_obj)

        await asyncio.sleep(delay_after_reset)

        logging.info(f"Configure port {port_str}")
        await utils.apply(
            # txport.speed.mode.selection.set(mode=enums.PortSpeedMode.F100G),
            port_obj.comment.set(comment="IPv4 RoCEv2 UD SEND emulation"),
            port_obj.tx_config.enable.set_on(),
            port_obj.latency_config.offset.set(offset=0),
            port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
            port_obj.tx_config.burst_period.set(burst_period=0),
            # port_obj.tx_config.packet_limit.set(packet_count_limit=int(frames_per_flow*flow_repeat)),
            port_obj.max_header_length.set(max_header_length=128),
            port_obj.autotrain.set(interval=0),
            port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
            port_obj.checksum.set(offset=0),
            port_obj.tx_config.delay.set(delay_val=0),
            port_obj.tpld_mode.set_normal(),
            port_obj.payload_mode.set_normal(),
            #port_obj.rate.pps.set(port_rate_pps=1_000), # If you want to control traffic rate with FPS, uncomment this.
            # port_obj.rate.fraction.set(int(traffic_rate_percent*1_000_000)),  # If you want to control traffic rate with fraction, uncomment this. 1,000,000 = 100%
            port_obj.tx_config.mode.set_normal(),
        )
        
        #--------------------------------------
        # Configure stream_0 on the txport
        #--------------------------------------
        logging.info(f"   Configure UD SEND on port {port_str}")

        stream_0 = await port_obj.streams.create()
        eth = headers.Ethernet()
        eth.src_mac = src_mac
        eth.dst_mac = dst_mac
        eth.ethertype = headers.EtherType.IPv4
        ipv4 = headers.IPV4()
        ipv4.src = src_ipv4
        ipv4.dst = dst_ipv4
        ipv4.proto = headers.IPProtocol.UDP
        udp = headers.UDP()
        udp.src_port = 4791
        udp.dst_port = 4791
        ib = IB()
        ib.bth.opcode = BTHOpcode.UD_SEND_ONLY
        ib.bth.destqp = dst_qp
        ib.bth.psn = 0
        ib.deth.src_qp = src_qp
        ib.deth.q_key = q_key
        _raw_header = "RAW_"+str(int(len(str(ib))/2))
        
        await utils.apply(
            stream_0.enable.set_on(),
            stream_0.packet.limit.set(packet_count=int(frames_per_flow*flow_repeat)),
            stream_0.comment.set(f"IPV4 UD SEND"),
            stream_0.rate.fraction.set(stream_rate_ppm=int(traffic_rate_percent*1_000_000)),
            stream_0.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.IP,
                enums.ProtocolOption.UDP,
                enums.ProtocolOption[_raw_header],
                ]),
            stream_0.packet.header.data.set(hex_data=Hex(str(eth)+str(ipv4)+str(udp)+str(ib))),
            stream_0.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
            stream_0.payload.content.set(
                payload_type=enums.PayloadType.PATTERN, 
                hex_data=Hex("AABBCCDD")
                ),
            stream_0.tpld_id.set(test_payload_identifier = stream_0.kind.index_id),
            stream_0.insert_packets_checksum.set_on()
        )
        if should_burst:
            await stream_0.burst.burstiness.set(size=burst_size, density=100)

        # Configure a modifier on the stream_0
        await stream_0.packet.header.modifiers.configure(1)

        # Modifier on the SQN
        modifier = stream_0.packet.header.modifiers.obtain(0)
        sqn_pos = int(len(str(eth)+str(ipv4)+str(udp))/2)+10
        await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
        await modifier.range.set(min_val=0, step=1, max_val=frames_per_flow-1)

        # free the port
        await mgmt.free_port(port_obj)
        logging.info(f"Configuration complete")



async def main():
    stop_event = asyncio.Event()
    try:
        await ipv6_rocev2_rc_send(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            frame_size=FRAME_SIZE_BYTES,
            frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
            flow_repeat=FLOW_REPEAT,
            traffic_rate_percent=RATE_PERCENT,
            should_burst=SHOULD_BURST,
            burst_size=BURST_SIZE_FRAMES,
            inter_burst_gap=INTER_BURST_GAP_BYTES,
            inter_pkt_gap=INTER_PACKET_GAP,
            src_mac=SRC_MAC,
            dst_mac=DST_MAC,
            src_ipv6=SRC_IPV6,
            dst_ipv6=DST_IPV6,
            dst_qp=RC_SEND_DST_QP,
            delay_after_reset = DELAY_AFTER_RESET,
        )
        # await ipv6_rocev2_ud_send(
        #     chassis=CHASSIS_IP,
        #     username=USERNAME,
        #     port_str=PORT,
        #     frame_size=FRAME_SIZE_BYTES,
        #     frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
        #     flow_repeat=FLOW_REPEAT,
        #     traffic_rate_percent=RATE_PERCENT,
        #     should_burst=SHOULD_BURST,
        #     burst_size=BURST_SIZE_FRAMES,
        #     src_mac=SRC_MAC,
        #     dst_mac=DST_MAC,
        #     src_ipv6=SRC_IPV6,
        #     dst_ipv6=DST_IPV6,
        #     src_qp=UD_SEND_SRC_QP,
        #     dst_qp=UD_SEND_DST_QP,
        #     q_key = UD_SEND_Q_KEY,
        #     delay_after_reset = DELAY_AFTER_RESET,
        # )
        # await ipv4_rocev2_rc_send(
        #     chassis=CHASSIS_IP,
        #     username=USERNAME,
        #     port_str=PORT,
        #     frame_size=FRAME_SIZE_BYTES,
        #     frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
        #     flow_repeat=FLOW_REPEAT,
        #     traffic_rate_percent=RATE_PERCENT,
        #     should_burst=SHOULD_BURST,
        #     burst_size=BURST_SIZE_FRAMES,
        #     inter_burst_gap=INTER_BURST_GAP_BYTES,
        #     inter_pkt_gap=INTER_PACKET_GAP,
        #     src_mac=SRC_MAC,
        #     dst_mac=DST_MAC,
        #     src_ipv4=SRC_IPV4,
        #     dst_ipv4=DST_IPV4,
        #     dst_qp=RC_SEND_DST_QP,
        #     delay_after_reset = DELAY_AFTER_RESET,
        # )
        # await ipv4_rocev2_ud_send(
        #     chassis=CHASSIS_IP,
        #     username=USERNAME,
        #     port_str=PORT,
        #     frame_size=FRAME_SIZE_BYTES,
        #     frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
        #     flow_repeat=FLOW_REPEAT,
        #     traffic_rate_percent=RATE_PERCENT,
        #     should_burst=SHOULD_BURST,
        #     burst_size=BURST_SIZE_FRAMES,
        #     src_mac=SRC_MAC,
        #     dst_mac=DST_MAC,
        #     src_ipv4=SRC_IPV4,
        #     dst_ipv4=DST_IPV4,
        #     src_qp=UD_SEND_SRC_QP,
        #     dst_qp=UD_SEND_DST_QP,
        #     q_key = UD_SEND_Q_KEY,
        #     delay_after_reset = DELAY_AFTER_RESET,
        # )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())