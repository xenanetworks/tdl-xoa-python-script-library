from xoa_driver import ports
from scapy.layers.l2 import Ether
from scapy.utils import mac2str
from scapy.layers.inet import IP, UDP
from scapy.layers.dhcp import BOOTP, DHCP
from scapy.packet import Packet
from .xsocket import XSocket
from typing import Dict, Tuple
from enum import Enum
import time
import random
import re

class DhcpSession:
    
    class Error(Enum):
        Success         = 0
        UnknownFailure  = 1
    
    class State(Enum):
        DISCOVER        = 0
        DISCOVER_SENT   = 1
        REQUEST         = 2
        REQUEST_SENT    = 3
        COMPLETED       = 4
        FAILED          = 5
    
    class OptType(Enum):
        PAD                     = 0
        SUBNET_MASK             = 1
        ROUTER                  = 3
        DOMAIN_NAME_SERVERS     = 6
        INTERFACE_MTU           = 26
        BROADCAST_ADDRESS       = 28
        REQUESTED_ADDRESS       = 50
        LEASE_TIME              = 51
        MESSAGE_TYPE            = 53
        DHCP_SERVER             = 54
        PARAMETER_REQUEST_LIST  = 55
        RENEWAL_TIME            = 58
        REBINDING_TIME          = 59
        CLASSLESS_ROUTE         = 121
        END                     = 255
    
    class MsgType(Enum):
        DISCOVER        = 1
        OFFER           = 2
        REQUEST         = 3
        DECLINE         = 4
        ACK             = 5
        NAK             = 6
        RELEASE         = 7
        INFORM          = 8
        LEASEQUERY      = 10
        LEASEUNASSIGNED = 11
        LEASEUNKNOWN    = 12
        LEASEACTIVE     = 13
        INVALID         = 255
    
    mac_address:                    str
    state:                          State
    discover_ip_src:                str
    discover_ip_dst:                str
    discover_xid:                   int
    
    __discover_max_num_retransmit:  int
    __discover_num_retransmit:      int
    __discover_last_sent:           float
    __discover_timeout:             float
    
    offered_dhcp_server_id:       int
    offered_ip_addr:              str
    offered_subnet_mask:          str
    offered_broadcast_addr:       str
    offered_router:               str
    offered_lease_time:           int
    
    
    
    def __init__(self, mac_address: str, transaction_id: int, max_num_retransmit: int, timeout_msec: int):
        self.mac_address                    = mac_address
        self.discover_xid                   = transaction_id
        
        self.state                          = DhcpSession.State.DISCOVER
        self.__discover_max_num_retransmit  = max_num_retransmit
        self.__discover_num_retransmit      = 0
        self.__discover_last_sent           = 0.0
        self.__discover_timeout             = timeout_msec/1000
        
        self.offered_dhcp_server_id       = 0
        self.offered_ip_addr              = ""
        self.offered_subnet_mask          = ""
        self.offered_broadcast_addr       = ""
        self.offered_router               = ""
        self.offered_lease_time           = 0
        
    ## Return (Error, Data)
    async def process_tx(self) -> Tuple[Error, bytes]:
        if self.state == DhcpSession.State.DISCOVER:
            if self.__discover_num_retransmit >= self.__discover_max_num_retransmit:
                self.state = DhcpSession.State.FAILED
                return (DhcpSession.Error.Success, b"")
            
            self.state = DhcpSession.State.DISCOVER_SENT
            self.__discover_last_sent = time.time()
            return (DhcpSession.Error.Success, self.__create_discovery_packet())
        
        elif self.state == DhcpSession.State.DISCOVER_SENT:
            if time.time() - self.__discover_last_sent > self.__discover_timeout:
                self.__discover_num_retransmit += 1
                self.state = DhcpSession.State.DISCOVER
            return (DhcpSession.Error.Success, b"")
            
        elif self.state == DhcpSession.State.REQUEST:
            if self.__discover_num_retransmit >= self.__discover_max_num_retransmit:
                self.state = DhcpSession.State.FAILED
                return (DhcpSession.Error.Success, b"")
            
            self.state = DhcpSession.State.REQUEST_SENT
            self.__discover_last_sent = time.time()
            return (DhcpSession.Error.Success, self.__create_request_packet())
                
        elif self.state == DhcpSession.State.REQUEST_SENT:
            if time.time() - self.__discover_last_sent > self.__discover_timeout:
                self.__discover_num_retransmit += 1
                self.state = DhcpSession.State.REQUEST
            return (DhcpSession.Error.Success, b"")
                
        elif self.state == DhcpSession.State.COMPLETED:
            return (DhcpSession.Error.Success, b"")
        elif self.state == DhcpSession.State.FAILED:
            return (DhcpSession.Error.Success, b"")
        else:
            return (DhcpSession.Error.UnknownFailure, b"")
    
    async def process_rx(self, data :bytes):
        if self.state == DhcpSession.State.DISCOVER:
            return
        elif self.state == DhcpSession.State.DISCOVER_SENT:
            ret_error = self.__parse_offer_packet(data)
            if ret_error == DhcpSession.Error.Success:
                self.__discover_num_retransmit = 0
                self.state = DhcpSession.State.REQUEST
            else:
                self.state = DhcpSession.State.FAILED
        elif self.state == DhcpSession.State.REQUEST:
            return
        elif self.state == DhcpSession.State.REQUEST_SENT:
            ret_error = self.__parse_ack_packet(data)
            if ret_error == DhcpSession.Error.Success:
                self.state = DhcpSession.State.COMPLETED
            else:
                self.state = DhcpSession.State.FAILED
        elif self.state == DhcpSession.State.COMPLETED:
            pass
        elif self.state == DhcpSession.State.FAILED:
            pass
        else:
            pass
        
    
    def __create_discovery_packet(self) -> bytes:
        ethernet = Ether(dst='ff:ff:ff:ff:ff:ff', src=self.mac_address, type=0x0800)
        ip = IP(src='0.0.0.0', dst='255.255.255.255')
        udp = UDP(sport=68, dport=67)
        bootp = BOOTP(op=1, chaddr=[mac2str(self.mac_address)], xid=self.discover_xid, flags=0x0000)        
        dhcp = DHCP(options=[   ('message-type', 'discover'), 
                                ('param_req_list', DhcpSession.OptType.SUBNET_MASK.value, DhcpSession.OptType.BROADCAST_ADDRESS.value, DhcpSession.OptType.ROUTER.value),
                                'end'])
        
        packet = ethernet / ip / udp / bootp / dhcp
        return bytes(packet)
    
    def __create_request_packet(self) -> bytes:
        ethernet = Ether(dst='ff:ff:ff:ff:ff:ff', src=self.mac_address, type=0x0800)
        ip = IP(src='0.0.0.0', dst='255.255.255.255')
        udp = UDP(sport=68, dport=67)
        bootp = BOOTP(op=1, chaddr=[mac2str(self.mac_address)], xid=self.discover_xid, flags=0x0000)        
        dhcp = DHCP(options=[   ('message-type', 'request'), 
                                ('server_id', self.offered_dhcp_server_id),
                                ('requested_addr', self.offered_ip_addr),
                                ('param_req_list', DhcpSession.OptType.SUBNET_MASK.value, DhcpSession.OptType.BROADCAST_ADDRESS.value, DhcpSession.OptType.ROUTER.value),
                                'end'])
        
        packet = ethernet / ip / udp / bootp / dhcp
        return bytes(packet)
    
    def __parse_offer_packet(self, data: bytes) -> Error:
        packet = Ether(data)
        if DHCP in packet and BOOTP in packet:
            if DhcpSession.__get_dhcp_message_type(packet) != DhcpSession.MsgType.OFFER.value:
                return DhcpSession.Error.UnknownFailure
            dst_macaddress = ':'.join(f'{byte:02x}' for byte in packet[BOOTP].chaddr[:6])
            if dst_macaddress.lower() != self.mac_address:
                return DhcpSession.Error.UnknownFailure
                
            self.offered_ip_addr = packet[BOOTP].yiaddr
            for option in packet[DHCP].options:
                if option[0] == 'subnet_mask':
                    self.offered_subnet_mask = option[1]
                elif option[0] == 'router':
                    self.offered_router = option[1]
                elif option[0] == 'server_id':
                    self.offered_dhcp_server_id = option[1]
                elif option[0] == 'end':
                    break
            return DhcpSession.Error.Success
        return DhcpSession.Error.UnknownFailure

    def __parse_ack_packet(self, data: bytes) -> Error:
        packet = Ether(data)
        if DHCP in packet and BOOTP in packet:
            if DhcpSession.__get_dhcp_message_type(packet) != DhcpSession.MsgType.ACK.value:
                return DhcpSession.Error.UnknownFailure
            
            dst_macaddress = ':'.join(f'{byte:02x}' for byte in packet[BOOTP].chaddr[:6])
            if dst_macaddress.lower() != self.mac_address:
                return DhcpSession.Error.UnknownFailure
                
            self.offered_ip_addr = packet[BOOTP].yiaddr
            for option in packet[DHCP].options:
                if option[0] == 'subnet_mask':
                    self.offered_subnet_mask = option[1]
                elif option[0] == 'router':
                    self.offered_router = option[1]
                elif option[0] == 'server_id':
                    self.offered_dhcp_server_id = option[1]
                elif option[0] == 'end':
                    break
            return DhcpSession.Error.Success
        return DhcpSession.Error.UnknownFailure
    
    @staticmethod
    def __get_dhcp_message_type(packet: Packet):
        if packet.haslayer(DHCP):
            for option in packet[DHCP].options:
                if option[0] == 'message-type':
                    return option[1]
        return None

class DhcpClient:
    class Error(Enum):
        Success         = 0
        UnknownFailure  = 1
    
    def __init__(self, port: ports.GenericL23Port):
        self.port = port
        self.__xsocket              = XSocket(self.port, XSocket.FilterType.DhcpClient)
        self.concurrent_requests    = 10 # the number of concurrent dhcp sessions that can be processed at the same time
        
    @staticmethod   
    def __is_valid_mac_address(mac: str):
        regex = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if re.match(regex, mac):
            return True
        else:
            return False
    
    async def get_dhcp_addresses(self, base_hw_address: str, num_requests: int, max_num_retransmit: int, timeout_msec: int) -> Tuple[Error, Dict[str, DhcpSession], int, int]:
        """As a DHCP Client, it sends a set of DHCP requests toward DHCP server in order to get a list of IP addresses
        :param: base_hw_address: the base mac address for sending the DHCP Requests. The first 3 bytes will be used as a base and the rest will be chosen randomly
        :param: num_requests: Number of DHCP requests to be sent
        :param: max_num_retransmit: Maximum number of retransmition for each Request should be sent before being considered as a failure
        :param: timeout_msec: Retransmition timeout in miliseconds for each Request 
        :rtype: typing.Tuple[Error, typing.Dict[str, DhcpSession], int, int]: It returns a tuple that contains [Error, Dict[mac_address, successful_sessions], num_success, num_failure]
        """
        
        if not DhcpClient.__is_valid_mac_address(base_hw_address):
            return (DhcpClient.Error.UnknownFailure, {}, 0, 0)
        
        base_hw_address = base_hw_address.lower()
        
        ret_err = await self.__xsocket.start()
        if ret_err != XSocket.Error.Success:
            return (DhcpClient.Error.UnknownFailure, {}, 0, 0)
        
        current_xid = random.randint(0, 2**24)
        
        process_dict:   Dict[str, DhcpSession] = {}
        processed_dict: Dict[str, DhcpSession] = {}
        
        tot_num_sessions    = 0
        num_processed       = 0
        while num_processed < num_requests:
            ret_error, data = await self.__xsocket.receive_packet()
            if ret_error == XSocket.Error.Success and data and len(data) != 0:
                # process RX packet
                packet = Ether(data)
                dst_mac = packet[Ether].dst.lower()
                if dst_mac in process_dict:
                    await process_dict[dst_mac].process_rx(data)
            
            while len(process_dict) < self.concurrent_requests and tot_num_sessions < num_requests: # create sessions as much as concurrent_requests allows
                current_xid = (current_xid + 1) % 2**24
                first_three_bytes = base_hw_address[:8]
                last_three_bytes = format(current_xid, '06x')
                session_mac = first_three_bytes + ':' + last_three_bytes[:2] + ':' + last_three_bytes[2:4] + ':' + last_three_bytes[4:]
                session_mac = session_mac.lower()
                process_dict[session_mac] = DhcpSession(session_mac, current_xid, max_num_retransmit, timeout_msec)
                tot_num_sessions += 1
            
            delete_list = []
            for src_mac, session in process_dict.items():
                ret_err, data = await session.process_tx()
                if ret_err == DhcpSession.Error.Success and data and len(data):
                    await self.__xsocket.send_packet(data)
                
                if session.state.value >= DhcpSession.State.COMPLETED.value:
                    processed_dict[src_mac] = session
                    num_processed += 1
                    delete_list.append(src_mac)
            
            for key in delete_list:
                del process_dict[key]
                
        
        await self.__xsocket.stop()
        
        num_success = 0
        num_failure = 0
        success_dict: Dict[str, DhcpSession] = {}
        for session in processed_dict.values():
            if session.state == DhcpSession.State.COMPLETED:
                num_success += 1
                success_dict[session.mac_address] = session
            elif session.state == DhcpSession.State.FAILED:
                num_failure += 1
            else:
                print("Unexpected state for DhcpSession")
                return (DhcpClient.Error.UnknownFailure, {}, 0, 0)
        
        return (DhcpClient.Error.Success, success_dict, num_success, num_failure)