################################################################
#
#                   TCP HANDSHAKE
#
# This script shows you how to simulate TCP 3-way handshake 
# between two test ports.
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

CHASSIS_IP = "10.165.136.66"      # Chassis IP address or hostname
USERNAME = "XOA"                # Username
CLIENT_PORT = "0/0"
SERVER_PORT = "0/1"

CLIENT_MAC = "aaaa.0a0a.0a0a"
SERVER_MAC = "aaaa.0a0a.0a14"
CLIENT_IP = "10.10.10.10"
SERVER_IP = "10.10.10.20"
S_PORT = 6000
D_PORT = 22611

import scapy.all

#------------------------------
# tcp_handshake
#------------------------------
async def tcp_handshake(chassis: str, username: str, c_port_str: str, s_port_str: str, client_mac: str, server_mac: str, client_ip: str, server_ip: str, source_port_num: int, dest_port_num: int) -> None:
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # access the module and port on the tester
        _mid_c = int(c_port_str.split("/")[0])
        _pid_c = int(c_port_str.split("/")[1])
        _mid_s = int(s_port_str.split("/")[0])
        _pid_s = int(s_port_str.split("/")[1])
        c_module_obj = tester.modules.obtain(_mid_c)
        s_module_obj = tester.modules.obtain(_mid_s)

        # modules must be Chimera
        if isinstance(c_module_obj, modules.E100ChimeraModule):
            return
        if isinstance(s_module_obj, modules.E100ChimeraModule):
            return
        
        c_port_obj = c_module_obj.ports.obtain(_pid_c)
        s_port_obj = s_module_obj.ports.obtain(_pid_s)
        
        # reserve ports
        await mgmt.free_module(c_module_obj)
        await mgmt.free_module(s_module_obj)
        await mgmt.reserve_port(c_port_obj)
        await mgmt.reserve_port(s_port_obj)

        # port configuration
        await utils.apply(
                c_port_obj.comment.set(comment="TCP Client Port"),
                c_port_obj.tx_config.enable.set_on(),
                c_port_obj.latency_config.offset.set(offset=0),
                c_port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
                c_port_obj.tx_config.burst_period.set(burst_period=0),
                c_port_obj.tx_config.packet_limit.set(packet_count_limit=1),
                c_port_obj.max_header_length.set(max_header_length=128),
                c_port_obj.checksum.set(offset=0),
                c_port_obj.tx_config.delay.set(delay_val=0),
                c_port_obj.tpld_mode.set_normal(),
                c_port_obj.payload_mode.set_normal(),
                c_port_obj.rate.pps.set(port_rate_pps = 10)
            )
        await utils.apply(
                s_port_obj.comment.set(comment="TCP Server Port"),
                s_port_obj.tx_config.enable.set_on(),
                s_port_obj.latency_config.offset.set(offset=0),
                s_port_obj.latency_config.mode.set(mode=enums.LatencyMode.LAST2LAST),
                s_port_obj.tx_config.burst_period.set(burst_period=0),
                s_port_obj.tx_config.packet_limit.set(packet_count_limit=1),
                s_port_obj.max_header_length.set(max_header_length=128),
                s_port_obj.checksum.set(offset=0),
                s_port_obj.tx_config.delay.set(delay_val=0),
                s_port_obj.tpld_mode.set_normal(),
                s_port_obj.payload_mode.set_normal(),
                s_port_obj.rate.pps.set(port_rate_pps = 10)
            )

        # Base CLIENT TCP packet configuration
        client_tcp = headers.TCP()
        client_tcp.src_port = source_port_num
        client_tcp.dst_port = dest_port_num
        client_tcp.seq_num = 0
        client_tcp.ack_num = 0
        client_tcp.window = 64240
        client_tcp.header_length = int(len(str(client_tcp))/2)
        client_tcp.ack = 0
        client_tcp.syn = 0
        client_tcp.fin = 0
        client_ipv4 = headers.IPV4()
        client_ipv4.src = client_ip
        client_ipv4.dst = server_ip
        client_ipv4.total_length = int(len(str(client_tcp))/2) + int(len(str(client_ipv4))/2)
        client_ipv4.proto = headers.IPProtocol.TCP
        client_eth = headers.Ethernet()
        client_eth.src_mac = client_mac
        client_eth.dst_mac = server_mac
        client_eth.ethertype = headers.EtherType.IPv4

        # TCP SYN packet (from client to server)
        client_tcp.seq_num = 0
        client_tcp.ack_num = 0
        client_tcp.syn = 1
        client_tcp.ack = 0
        client_tcp.fin = 0
        syn_tcp_pkt = str(client_eth)+str(client_ipv4)+str(client_tcp)

        # TCP ACK packet (from client to server)
        # set syn bit = 0, set ack bit to 1
        client_tcp.seq_num = 1
        client_tcp.ack_num = 1
        client_tcp.syn = 0
        client_tcp.ack = 1
        client_tcp.fin = 0
        ack_tcp_pkt = str(client_eth)+str(client_ipv4)+str(client_tcp)

        # Base SERVER TCP packet configuration
        server_tcp = headers.TCP()
        server_tcp.src_port = source_port_num
        server_tcp.dst_port = dest_port_num
        server_tcp.seq_num = 0
        server_tcp.ack_num = 0
        server_tcp.window = 64240
        server_tcp.header_length = int(len(str(server_tcp))/2)
        server_tcp.ack = 0
        server_tcp.syn = 0
        server_tcp.fin = 0
        server_ipv4 = headers.IPV4()
        server_ipv4.src = server_ip
        server_ipv4.dst = client_ip
        server_ipv4.total_length = int(len(str(server_tcp))/2) + int(len(str(server_ipv4))/2)
        server_ipv4.proto = headers.IPProtocol.TCP
        servde_eth = headers.Ethernet()
        servde_eth.src_mac = server_mac
        servde_eth.dst_mac = client_mac
        servde_eth.ethertype = headers.EtherType.IPv4

        # TCP SYN-ACK packet (from server to client)
        # set syn and ack bits to 1
        server_tcp.seq_num = 0
        server_tcp.ack_num = 1
        server_tcp.syn = 1
        server_tcp.ack = 1
        server_tcp.fin = 0
        syn_ack_tcp_pkt = str(servde_eth)+str(server_ipv4)+str(server_tcp)
        
        # sent SYN out of client port
        await c_port_obj.tx_single_pkt.send.set(hex_data=Hex(syn_tcp_pkt))
        logging.info(f"{syn_tcp_pkt}")
        await asyncio.sleep(1)
        # sent SYN ACK out of server port
        await s_port_obj.tx_single_pkt.send.set(hex_data=Hex(syn_ack_tcp_pkt))
        logging.info(f"{syn_ack_tcp_pkt}")
        await asyncio.sleep(1)
        # sent ACK out of client port
        await c_port_obj.tx_single_pkt.send.set(hex_data=Hex(ack_tcp_pkt))
        logging.info(f"{ack_tcp_pkt}")
        await asyncio.sleep(1)

        # free ports
        await mgmt.free_port(c_port_obj)
        await mgmt.free_port(s_port_obj)

        # If you want to save the TCP handshake packets into a pcap, uncomment the lines below.
        # cap_packet_list = []
        # cap_packet_list.append(bytes.fromhex(syn_tcp_pkt))
        # cap_packet_list.append(bytes.fromhex(syn_ack_tcp_pkt))
        # cap_packet_list.append(bytes.fromhex(ack_tcp_pkt))
        # scapy.all.wrpcap(filename='tcp_handshake.pcap', pkt=cap_packet_list)

async def main():
    stop_event = asyncio.Event()
    try:
        await tcp_handshake(
            chassis=CHASSIS_IP,
            username=USERNAME,
            c_port_str=CLIENT_PORT,
            s_port_str=SERVER_PORT,
            client_mac=CLIENT_MAC,
            server_mac=SERVER_MAC,
            client_ip=CLIENT_IP,
            server_ip=SERVER_IP,
            source_port_num=S_PORT,
            dest_port_num=D_PORT
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())