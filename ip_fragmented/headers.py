from ipaddress import IPv4Address, IPv6Address
from binascii import hexlify
from xoa_driver.misc import Hex

####################################
#           Ethernet               #
####################################
class Ethernet:
    def __init__(self):
        self.dst_mac = "0000.0000.0000"
        self.src_mac = "0000.0000.0000"
        self.ethertype = "0800"
    
    def __str__(self):
        _dst_mac = self.dst_mac.replace(".", "")
        _src_mac = self.src_mac.replace(".", "")
        _ethertype = self.ethertype
        return f"{_dst_mac}{_src_mac}{_ethertype}".upper()
    

####################################
#           ARP                    #
####################################
class ARP:
    def __init__(self):
        self.hardware_type: str = "0001"
        self.protocol_type: str = "0800"
        self.hardware_size: str = "06"
        self.protocol_size: str = "04"
        self.opcode: str = "0001"
        self.sender_mac = "0000.0000.0000"
        self.sender_ip: IPv4Address = IPv4Address("0.0.0.0")
        self.target_mac = "0000.0000.0000"
        self.target_ip: IPv4Address = IPv4Address("0.0.0.0")
    
    def __str__(self):
        _hardware_type = self.hardware_type
        _protocol_type = self.protocol_type
        _hardware_size = self.hardware_size
        _protocol_size = self.protocol_size
        _sender_mac = self.sender_mac.replace(".", "")
        _sender_ip = hexlify(IPv4Address(self.sender_ip).packed).decode()
        _target_mac = self.target_mac.replace(".", "")
        _target_ip = hexlify(IPv4Address(self.target_ip).packed).decode()
        return f"{_hardware_type}{_protocol_type}{_hardware_size}{_protocol_size}{_sender_mac}{_sender_ip}{_target_mac}{_target_ip}".upper()

####################################
#           IPv4                   #
####################################
class IPV4:
    def __init__(self):
        self.version = 4
        self.header_length = 5
        self.dscp = 0
        self.ecn = 0
        self.total_length = 42
        self.identification = "0000"
        self.flags = 0
        self.offset = 0
        self.ttl = 255
        self.proto = 255
        self.checksum = "0000"
        self.src = "0.0.0.0"
        self.dst = "0.0.0.0"

    def __str__(self):
        _ver = '{:01X}'.format(self.version)
        _header_length = '{:01X}'.format(self.header_length)
        _dscp_ecn = '{:02X}'.format((self.dscp<<2)+self.ecn)
        _total_len = '{:04X}'.format(self.total_length)
        _ident = self.identification
        _flag_offset = '{:04X}'.format((self.flags<<13)+self.offset)
        _ttl = '{:02X}'.format(self.ttl)
        _proto = '{:02X}'.format(self.proto)
        _check = self.checksum
        _src = hexlify(IPv4Address(self.src).packed).decode()
        _dst = hexlify(IPv4Address(self.dst).packed).decode()
        return f"{_ver}{_header_length}{_dscp_ecn}{_total_len}{_ident}{_flag_offset}{_ttl}{_proto}{_check}{_src}{_dst}".upper()

####################################
#           IPv6                   #
####################################
class IPV6:
    def __init__(self):
        self.version = 6
        self.traff_class = 8
        self.flow_label = 0
        self.payload_length = 0
        self.next_header = "11"
        self.hop_limit = 1
        self.src = "2000::2"
        self.dst = "2000::100"

    def __str__(self):
        _ver = '{:01X}'.format(self.version)
        _traff_class = '{:01X}'.format(self.traff_class)
        _flow_label = '{:06X}'.format(self.flow_label)
        _payload_len = '{:04X}'.format(self.payload_length)
        _next_header = self.next_header
        _hop_limit = '{:02X}'.format(self.hop_limit)
        _src = hexlify(IPv6Address(self.src).packed).decode()
        _dst = hexlify(IPv6Address(self.dst).packed).decode()
        return f"{_ver}{_traff_class}{_flow_label}{_payload_len}{_next_header}{_hop_limit}{_src}{_dst}".upper()

####################################
#           UDP                    #
####################################
class UDP:
    def __init__(self):
        self.src_port = 0
        self.dst_port = 0
        self.length = 0
        self.checksum = 0

    def __str__(self):
        _src_port = '{:04X}'.format(self.src_port)
        _dst_port = '{:04X}'.format(self.dst_port)
        _length = '{:04X}'.format(self.length)
        _checksum = '{:04X}'.format(self.checksum)
        return f"{_src_port}{_dst_port}{_length}{_checksum}".upper()

####################################
#           TCP                    #
####################################
class TCP:
    def __init__(self):
        self.src_port = 0
        self.dst_port = 0
        self.seq_num = 0
        self.ack_num = 0
        self.header_length = 20
        """Aka. Data Offset (bytes)"""
        self.RSRVD = 0
        """Reserved 000"""
        self.ae = 0
        """Accurate ECN"""
        self.cwr = 0
        """Congestion Window Reduced"""
        self.ece = 0
        """ECN-Echo"""
        self.urg = 0
        """Urgent"""
        self.ack = 0
        """Acknowledgment"""
        self.psh = 0
        """Push"""
        self.rst = 0
        """Rest"""
        self.syn = 0
        """Sync"""
        self.fin = 0
        """Fin"""
        self.window = 0
        self.checksum = 0
        self.urgent_pointer = 0

    def __str__(self):
        _src_port = '{:04X}'.format(self.src_port)
        _dst_port = '{:04X}'.format(self.dst_port)
        _seq_num = '{:08X}'.format(self.seq_num)
        _ack_num = '{:08X}'.format(self.ack_num)
        if self.header_length % 4 != 0:
            raise Exception("Header Length field (bytes) must be multiple of 4")
        _header_length = '{:01X}'.format(int(self.header_length/4))
        _flags = 0
        _flags += (self.RSRVD<<9)
        _flags += (self.ae<<8)
        _flags += (self.cwr<<7)
        _flags += (self.ece<<6)
        _flags += (self.urg<<5)
        _flags += (self.ack<<4)
        _flags += (self.psh<<3)
        _flags += (self.rst<<2)
        _flags += (self.syn<<1)
        _flags += (self.fin<<0)
        _flags = '{:03X}'.format(_flags)
        _window = '{:04X}'.format(self.window)
        _checksum = '{:04X}'.format(self.checksum)
        _urgent_pointer = '{:04X}'.format(self.urgent_pointer)

        return f"{_src_port}{_dst_port}{_seq_num}{_ack_num}{_header_length}{_flags}{_window}{_checksum}{_urgent_pointer}".upper()