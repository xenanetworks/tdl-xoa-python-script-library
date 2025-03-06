################################################################
#
#                   ROCEV2 EMULATION
#
# This script shows you how to simulate a RoCEv2 flow
# on a port.
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

CHASSIS_IP = "10.165.153.101"       # Chassis IP address or hostname
USERNAME = "XOA"                    # Username
PORT = "7/0"

FRAME_SIZE_BYTES = 4500             # Frame size on wire including the FCS.
FRAMES_PER_ROCEV2_FLOW = 1000        # The number of frames including the first, the middle, and the last.
FLOW_REPEAT = 0                     # The number of repetitions of the frame sequence, set to 0 if you want the port to repeat over and over
RATE_PERCENT = 0.4                  # Traffic rate in percent

SRC_MAC = "aaaa.0a0a.0a0a"
DST_MAC = "aaaa.0a0a.0a14"
IP_VERSION = "ipv6" # "ipv4" or "ipv6"
SRC_IP = "2000::10" # "10.10.10.10" # "2000::10"
DST_IP = "2000::20" # "10.10.10.20" # "2000::20"

RDMA_OP = "UD_SEND" # "RC_SEND" or "UD_SEND"
RC_SEND_DST_QP = 5
UD_SEND_SRC_QP = 10
UD_SEND_DST_QP = 11
UD_SEND_Q_KEY = 1234

DELAY_AFTER_RESET = 2



class XenaRoCEv2Emulator:

    @staticmethod
    async def rc_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, rocev2_rate_frac: float, src_mac: str, dst_mac: str, ipver: str, src_ip: str, dst_ip: str, dst_qp: int, delay_after_reset: int) -> None:

        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename="rc_send.log", mode="a"),
                logging.StreamHandler()]
            )
        
        # create tester instance and establish connection
        async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

            logging.info(f"#####################################################################")
            logging.info(f"Chassis:                 {chassis}")
            logging.info(f"Username:                {username}")
            logging.info(f"Port:                    {port_str}")
            logging.info(f"RoCEv2 Traffic Rate:     {rocev2_rate_frac*100}%")
            logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
            logging.info(f"RoCEv2 Flow Type:        RC SEND")
            logging.info(f"Frames Per Flow:         {frames_per_flow}")
            logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
            logging.info(f"Flow Repeat:             {flow_repeat}")
            logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
            logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
            logging.info(f"RoCEv2 Flow IP (Src):    {src_ip}")
            logging.info(f"RoCEv2 Flow IP (Dst):    {dst_ip}")
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
                port_obj.comment.set(comment=f"{ipver.upper()} RoCEv2 RC SEND"),
                port_obj.tx_config.enable.set_on(),
                port_obj.latency_config.offset.set(offset=0),
                port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
                port_obj.tx_config.burst_period.set(burst_period=0),
                port_obj.max_header_length.set(max_header_length=128),
                port_obj.autotrain.set(interval=0),
                port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
                port_obj.checksum.set(offset=0),
                port_obj.tx_config.delay.set(delay_val=0),
                port_obj.tpld_mode.set_normal(),
                port_obj.payload_mode.set_cdf(),
            )
            
            #--------------------------------------
            # Configure base_stream on the txport
            #--------------------------------------
            logging.info(f"   Configure RC SEND stream on port {port_str}")

            base_stream = await port_obj.streams.create()

            eth = headers.Ethernet()
            eth.src_mac = src_mac
            eth.dst_mac = dst_mac
            if ipver == "ipv6":    
                eth.ethertype = headers.EtherType.IPv6
                ip = headers.IPV6()
                ip.src = src_ip
                ip.dst = dst_ip
                ip.next_header = headers.IPProtocol.UDP
            else:
                eth.ethertype = headers.EtherType.IPv4
                ip = headers.IPV4()
                ip.src = src_ip
                ip.dst = dst_ip
                ip.proto = headers.IPProtocol.UDP
            udp = headers.UDP()
            udp.src_port = 4791
            udp.dst_port = 4791
            ib = IB()
            ib.bth.opcode = BTHOpcode.RC_SEND_FIRST
            ib.bth.destqp = dst_qp
            ib.bth.psn = 0
            _raw_header = "RAW_"+str(int(len(str(ib))/2))
            udp.length = frame_size - int(len(str(eth))/2 + len(str(ip))/2) - 4
            
            total_frames = int(frames_per_flow*flow_repeat)
            stream_rate_ppm = int(rocev2_rate_frac*1_000_000)
            await utils.apply(
                base_stream.enable.set_on(),
                base_stream.packet.limit.set(packet_count=total_frames),
                base_stream.comment.set(f"{ipver.upper()} RC SEND"),
                base_stream.rate.fraction.set(stream_rate_ppm=stream_rate_ppm),
                base_stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
                base_stream.payload.content.set(
                    payload_type=enums.PayloadType.PATTERN, 
                    hex_data=Hex("AABBCCDD")
                    ),
                base_stream.tpld_id.set(test_payload_identifier = base_stream.kind.index_id),
                base_stream.insert_packets_checksum.set_on()
            )
            if ipver == "ipv6":
                await base_stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.IPV6,
                    enums.ProtocolOption.UDP,
                    enums.ProtocolOption[_raw_header],
                    ])
            else:
                await base_stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.IP,
                    enums.ProtocolOption.UDP,
                    enums.ProtocolOption[_raw_header],
                    ])
            await base_stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ip)+str(udp)+str(ib)))

            # Configure a modifier on the base_stream
            await base_stream.packet.header.modifiers.configure(1)

            # Modifier on the SQN
            modifier = base_stream.packet.header.modifiers.obtain(0)
            sqn_pos = int(len(str(eth)+str(ip)+str(udp))/2)+10
            await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
            await modifier.range.set(min_val=1, step=1, max_val=frames_per_flow)

            # configure CDFs
            await base_stream.cdf.count.set(cdf_count=frames_per_flow)
            await base_stream.cdf.offset.set(offset=int(len(str(eth)+str(ip)+str(udp))/2))
            await base_stream.cdf.data(cdf_index=0).set(hex_data=Hex("0010"))
            for i in range(1, frames_per_flow):
                await base_stream.cdf.data(cdf_index=i).set(hex_data=Hex("0110"))
            await base_stream.cdf.data(cdf_index=frames_per_flow-1).set(hex_data=Hex("0210"))

            await port_obj.transceiver.access_rw(page_address=2000, register_address=0xf0036).set(value=Hex("00000001"))

            # free the port
            await mgmt.free_port(port_obj)
            logging.info(f"Configuration complete")

    @staticmethod
    async def ud_send(chassis: str, username: str, port_str: str, frame_size: int, frames_per_flow: int, flow_repeat: int, rocev2_rate_frac: float, src_mac: str, dst_mac: str, ipver: str, src_ip: str, dst_ip: str, dst_qp: int, src_qp: int, q_key: int, delay_after_reset: int) -> None:

        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename="ud_send.log", mode="a"),
                logging.StreamHandler()]
            )
        
        # create tester instance and establish connection
        async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

            logging.info(f"#####################################################################")
            logging.info(f"Chassis:                 {chassis}")
            logging.info(f"Username:                {username}")
            logging.info(f"Port:                    {port_str}")
            logging.info(f"Port Traffic Rate:       {rocev2_rate_frac*100}%")
            logging.info(f"Delay After Reset:       {delay_after_reset} seconds")
            logging.info(f"RoCEv2 Flow Type:        UD SEND")
            logging.info(f"Frames Per Flow:         {frames_per_flow}")
            logging.info(f"Frame Size:              {frame_size} bytes (incl. FCS)")
            logging.info(f"Flow Repeat:             {flow_repeat}")
            logging.info(f"RoCEv2 Flow MAC (Src):   {src_mac}")
            logging.info(f"RoCEv2 Flow MAC (Dst):   {dst_mac}")
            logging.info(f"RoCEv2 Flow IP (Src):    {src_ip}")
            logging.info(f"RoCEv2 Flow IP (Dst):    {dst_ip}")
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
                port_obj.comment.set(comment=f"{ipver.upper()} RoCEv2 UD SEND"),
                port_obj.tx_config.enable.set_on(),
                port_obj.latency_config.offset.set(offset=0),
                port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
                port_obj.tx_config.burst_period.set(burst_period=0),
                port_obj.max_header_length.set(max_header_length=128),
                port_obj.autotrain.set(interval=0),
                port_obj.loop_back.set_none(), # If you want loopback the port TX to its own RX, change it to set_txoff2rx()
                port_obj.checksum.set(offset=0),
                port_obj.tx_config.delay.set(delay_val=0),
                port_obj.tpld_mode.set_normal(),
            )

            base_stream = await port_obj.streams.create()

            eth = headers.Ethernet()
            eth.src_mac = src_mac
            eth.dst_mac = dst_mac
            if ipver == "ipv6":    
                eth.ethertype = headers.EtherType.IPv6
                ip = headers.IPV6()
                ip.src = src_ip
                ip.dst = dst_ip
                ip.next_header = headers.IPProtocol.UDP
            else:
                eth.ethertype = headers.EtherType.IPv4
                ip = headers.IPV4()
                ip.src = src_ip
                ip.dst = dst_ip
                ip.proto = headers.IPProtocol.UDP
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
            udp.length = frame_size - int(len(str(eth))/2 + len(str(ip))/2) - 4
        
            total_frames = int(frames_per_flow*flow_repeat)
            stream_rate_ppm = int(rocev2_rate_frac*1_000_000)
            await utils.apply(
                base_stream.enable.set_on(),
                base_stream.packet.limit.set(packet_count=total_frames),
                base_stream.comment.set(f"{ipver.upper()} UD SEND"),
                base_stream.rate.fraction.set(stream_rate_ppm=stream_rate_ppm),
                base_stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=frame_size, max_val=frame_size),
                base_stream.payload.content.set(
                    payload_type=enums.PayloadType.PATTERN, 
                    hex_data=Hex("AABBCCDD")
                    ),
                base_stream.tpld_id.set(test_payload_identifier = base_stream.kind.index_id),
                base_stream.insert_packets_checksum.set_on()
            )
            if ipver == "ipv6":
                await base_stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.IPV6,
                    enums.ProtocolOption.UDP,
                    enums.ProtocolOption[_raw_header],
                    ])
            else:
                await base_stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.IP,
                    enums.ProtocolOption.UDP,
                    enums.ProtocolOption[_raw_header],
                    ])
            await base_stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ip)+str(udp)+str(ib)))
            
            # Configure a modifier on the base_stream
            await base_stream.packet.header.modifiers.configure(1)

            # Modifier on the SQN
            modifier = base_stream.packet.header.modifiers.obtain(0)
            sqn_pos = int(len(str(eth)+str(ip)+str(udp))/2)+10
            await modifier.specification.set(position=sqn_pos, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1)
            await modifier.range.set(min_val=1, step=1, max_val=frames_per_flow)

            # free the port
            await mgmt.free_port(port_obj)
            logging.info(f"Configuration complete")


#---------------
async def main():
    stop_event = asyncio.Event()
    try:
        if RDMA_OP == "RC_SEND":
            await XenaRoCEv2Emulator.rc_send(
                chassis=CHASSIS_IP,
                username=USERNAME,
                port_str=PORT,
                frame_size=FRAME_SIZE_BYTES,
                frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
                flow_repeat=FLOW_REPEAT,
                rocev2_rate_frac=RATE_PERCENT,
                src_mac=SRC_MAC,
                dst_mac=DST_MAC,
                ipver = IP_VERSION,
                src_ip=SRC_IP,
                dst_ip=DST_IP,
                dst_qp=RC_SEND_DST_QP,
                delay_after_reset = DELAY_AFTER_RESET,
            )
        else:
            await XenaRoCEv2Emulator.ud_send(
                chassis=CHASSIS_IP,
                username=USERNAME,
                port_str=PORT,
                frame_size=FRAME_SIZE_BYTES,
                frames_per_flow=FRAMES_PER_ROCEV2_FLOW,
                flow_repeat=FLOW_REPEAT,
                rocev2_rate_frac=RATE_PERCENT,
                src_mac=SRC_MAC,
                dst_mac=DST_MAC,
                ipver=IP_VERSION,
                src_ip=SRC_IP,
                dst_ip=DST_IP,
                src_qp=UD_SEND_SRC_QP,
                dst_qp=UD_SEND_DST_QP,
                q_key = UD_SEND_Q_KEY,
                delay_after_reset = DELAY_AFTER_RESET,
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())