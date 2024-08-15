
from dataclasses import dataclass
from enum import Enum

class BTHOpcode(Enum):
    # OpCodeValues
    # Code Bits [7-5] Connection Type
    #           [4-0] Message Type

    # Reliable Connection (RC)
    # [7-5] = 000
    RC_SEND_FIRST                  = 0 # /*0x00000000 */ "RC Send First " 
    RC_SEND_MIDDLE                 = 1 # /*0x00000001 */ "RC Send Middle "
    RC_SEND_LAST                   = 2 # /*0x00000010 */ "RC Send Last " 
    RC_SEND_LAST_IMM               = 3 # /*0x00000011 */ "RC Send Last Immediate "
    RC_SEND_ONLY                   = 4 # /*0x00000100 */ "RC Send Only "
    RC_SEND_ONLY_IMM               = 5 # /*0x00000101 */ "RC Send Only Immediate "
    RC_RDMA_WRITE_FIRST            = 6 # /*0x00000110 */ "RC RDMA Write First " 
    RC_RDMA_WRITE_MIDDLE           = 7 # /*0x00000111 */ "RC RDMA Write Middle "
    RC_RDMA_WRITE_LAST             = 8 # /*0x00001000 */ "RC RDMA Write Last "
    RC_RDMA_WRITE_LAST_IMM         = 9 # /*0x00001001 */ "RC RDMA Write Last Immediate "
    RC_RDMA_WRITE_ONLY             = 10 # /*0x00001010 */ "RC RDMA Write Only " 
    RC_RDMA_WRITE_ONLY_IMM         = 11 # /*0x00001011 */ "RC RDMA Write Only Immediate " 
    RC_RDMA_READ_REQUEST           = 12 # /*0x00001100 */ "RC RDMA Read Request " 
    RC_RDMA_READ_RESPONSE_FIRST    = 13 # /*0x00001101 */ "RC RDMA Read Response First " 
    RC_RDMA_READ_RESPONSE_MIDDLE   = 14 # /*0x00001110 */ "RC RDMA Read Response Middle " 
    RC_RDMA_READ_RESPONSE_LAST     = 15 # /*0x00001111 */ "RC RDMA Read Response Last " 
    RC_RDMA_READ_RESPONSE_ONLY     = 16 # /*0x00010000 */ "RC RDMA Read Response Only " 
    RC_ACKNOWLEDGE                 = 17 # /*0x00010001 */ "RC Acknowledge " 
    RC_ATOMIC_ACKNOWLEDGE          = 18 # /*0x00010010 */ "RC Atomic Acknowledge "
    RC_CMP_SWAP                    = 19 # /*0x00010011 */ "RC Compare Swap " 
    RC_FETCH_ADD                   = 20 # /*0x00010100 */ "RC Fetch Add "
    RC_SEND_LAST_INVAL             = 22 # /*0x00010110 */ "RC Send Last Invalidate "
    RC_SEND_ONLY_INVAL             = 23 # /*0x00010111 */ "RC Send Only Invalidate "

    # Reliable Datagram (RD)
    # [7-5] = 010
    RD_SEND_FIRST                  = 64 # /*0x01000000 */ "RD Send First "
    RD_SEND_MIDDLE                 = 65 # /*0x01000001 */ "RD Send Middle "
    RD_SEND_LAST                   = 66 # /*0x01000010 */ "RD Send Last "
    RD_SEND_LAST_IMM               = 67 # /*0x01000011 */ "RD Send Last Immediate "
    RD_SEND_ONLY                   = 68 # /*0x01000100 */ "RD Send Only "
    RD_SEND_ONLY_IMM               = 69 # /*0x01000101 */ "RD Send Only Immediate "
    RD_RDMA_WRITE_FIRST            = 70 # /*0x01000110 */ "RD RDMA Write First "
    RD_RDMA_WRITE_MIDDLE           = 71 # /*0x01000111 */ "RD RDMA Write Middle "
    RD_RDMA_WRITE_LAST             = 72 # /*0x01001000 */ "RD RDMA Write Last "
    RD_RDMA_WRITE_LAST_IMM         = 73 # /*0x01001001 */ "RD RDMA Write Last Immediate "
    RD_RDMA_WRITE_ONLY             = 74 # /*0x01001010 */ "RD RDMA Write Only "
    RD_RDMA_WRITE_ONLY_IMM         = 75 # /*0x01001011 */ "RD RDMA Write Only Immediate "
    RD_RDMA_READ_REQUEST           = 76 # /*0x01001100 */ "RD RDMA Read Request "
    RD_RDMA_READ_RESPONSE_FIRST    = 77 # /*0x01001101 */ "RD RDMA Read Response First "
    RD_RDMA_READ_RESPONSE_MIDDLE   = 78 # /*0x01001110 */ "RD RDMA Read Response Middle "
    RD_RDMA_READ_RESPONSE_LAST     = 79 # /*0x01001111 */ "RD RDMA Read Response Last "
    RD_RDMA_READ_RESPONSE_ONLY     = 80 # /*0x01010000 */ "RD RDMA Read Response Only "
    RD_ACKNOWLEDGE                 = 81 # /*0x01010001 */ "RD Acknowledge "
    RD_ATOMIC_ACKNOWLEDGE          = 82 # /*0x01010010 */ "RD Atomic Acknowledge "
    RD_CMP_SWAP                    = 83 # /*0x01010011 */ "RD Compare Swap "
    RD_FETCH_ADD                   = 84 # /*0x01010100 */ "RD Fetch Add "
    RD_RESYNC                      = 85 # /*0x01010101 */ "RD RESYNC "

    # Unreliable Datagram (UD)
    # [7-5] = 011
    UD_SEND_ONLY                  = 100 # /*0x01100100 */ "UD Send Only "
    UD_SEND_ONLY_IMM              = 101 # /*0x01100101 */ "UD Send Only Immediate "

    # Unreliable Connection (UC)
    # [7-5] = 001
    UC_SEND_FIRST                  = 32 # /*0x00100000 */ "UC Send First "
    UC_SEND_MIDDLE                 = 33 # /*0x00100001 */ "UC Send Middle  "
    UC_SEND_LAST                   = 34 # /*0x00100010 */ "UC Send Last "
    UC_SEND_LAST_IMM               = 35 # /*0x00100011 */ "UC Send Last Immediate "
    UC_SEND_ONLY                   = 36 # /*0x00100100 */ "UC Send Only "
    UC_SEND_ONLY_IMM               = 37 # /*0x00100101 */ "UC Send Only Immediate "
    UC_RDMA_WRITE_FIRST            = 38 # /*0x00100110 */ "UC RDMA Write First"
    UC_RDMA_WRITE_MIDDLE           = 39 # /*0x00100111 */ "UC RDMA Write Middle "
    UC_RDMA_WRITE_LAST             = 40 # /*0x00101000 */ "UC RDMA Write Last "
    UC_RDMA_WRITE_LAST_IMM         = 41 # /*0x00101001 */ "UC RDMA Write Last Immediate"
    UC_RDMA_WRITE_ONLY             = 42 # /*0x00101010 */ "UC RDMA Write Only "
    UC_RDMA_WRITE_ONLY_IMM         = 43 # /*0x00101011 */ "UC RDMA Write Only Immediate"

@dataclass
class BTH:
    """BASE TRANSPORT HEADER (BTH) - 12 BYTES
    
    Base Transport Header contains the fields for IBA transports.
    """
    opcode: BTHOpcode = BTHOpcode.RC_SEND_FIRST
    """OpCode indicates the IBA packet type. It also
    specifies which extension headers follow the BTH
    """
    se = 0
    """Solicited Event, this bit indicates that an event
    should be generated by the responder
    """
    migreq = 0
    """This bit is used to communicate migration state
    """
    padcnt = 1
    """Pad Count indicates how many extra bytes are added
    to the payload to align to a 4 byte boundary
    """
    tver = 0
    """Transport Header Version indicates the version of
    the IBA Transport Headers
    """ 
    pkey = 65535
    """Partition Key indicates which logical Partition is
    associated with this packet
    """
    reserved = 7
    """Reserved
    """
    destqp = 2
    """Destination QP indicates the Work Queue Pair Number
    (QP) at the destination
    """
    ackreq = 0
    """Acknowledge Request, this bit is used to indicate
    that an acknowledge (for this packet) should be
    scheduled by the responder
    """
    reserved_7bits = 0
    """Reserved
    """
    psn =0
    """Packet Sequence Number is used to detect a missing
    or duplicate Packet
    """

    def __str__(self):
        _opcode = '{:02X}'.format(self.opcode.value)
        _combo_1 = '{:02X}'.format((self.se<<7)+(self.migreq<<6)+(self.padcnt<<4)+self.tver)
        _pk = '{:04X}'.format(self.pkey)
        _reserved = '{:02X}'.format(self.reserved)
        _qp = '{:06X}'.format(self.destqp)
        _combo_2 = '{:02X}'.format((self.ackreq<<7)+self.reserved_7bits)
        _ps = '{:06X}'.format(self.psn)
        return f"{_opcode}{_combo_1}{_pk}{_reserved}{_qp}{_combo_2}{_ps}".upper()

@dataclass
class RETH:
    """RDMA EXTENDED TRANSPORT HEADER (RETH) - 16 BYTES

    RDMA Extended Transport Header contains the additional transport fields
    for RDMA operations. The RETH is present in only the first (or only)
    packet of an RDMA Request as indicated by the Base Transport Header
    OpCode field.
    """
    va = 0
    """Virtual Address of the RDMA operation
    """
    r_key = 0
    """Remote Key that authorizes access for the RDMA operation
    """
    dma_len = 0
    """DMA Length indicates the length (in Bytes) of the DMA operation.
    """

    def __str__(self):
        _va = '{:016X}'.format(self.va)
        _r_key = '{:08X}'.format(self.r_key)
        _dma_len = '{:08X}'.format(self.dma_len)
        return f"{_va}{_r_key}{_dma_len}".upper()

@dataclass
class AETH:
    """ACK EXTENDED TRANSPORT HEADER (AETH) - 4 BYTES

    ACK Extended Transport Header contains the additional transport fields
    for ACK packets. The AETH is only in Acknowledge, RDMA READ Response
    First, RDMA READ Response Last, and RDMA READ Response Only packets
    as indicated by the Base Transport Header OpCode field.
    """
    syndrome = 0
    """Syndrome indicates if this is an ACK or NAK
    packet plus additional information about the
    ACK or NAK
    """
    msn = 0
    """Message Sequence Number indicates the sequence
    number of the last message completed at the
    responder
    """

    def __str__(self):
        _syndrome = '{:02X}'.format(self.syndrome)
        _msn = '{:06X}'.format(self.msn)
        return f"{_syndrome}{_msn}".upper()

@dataclass
class RDETH:
    """RELIABLE DATAGRAM EXTENDED TRANSPORT HEADER (RDETH) - 4 BYTES

    Reliable Datagram Extended Transport Header contains the additional
    transport fields for reliable datagram service. The RDETH is only
    in Reliable Datagram packets as indicated by the Base Transport Header
    OpCode field.
    """

    reserved = 0
    """Reserved
    """
    ee_context = 0
    """EE-Context indicates which End-to-End Context
    should be used for this Reliable Datagram packet
    """

    def __str__(self):
        _reserved = '{:02X}'.format(self.reserved)
        _ee_context = '{:06X}'.format(self.ee_context)
        return f"{_reserved}{_ee_context}".upper()

@dataclass
class DETH:
    """DATAGRAM EXTENDED TRANSPORT HEADER (DETH) - 8 BYTES

    Datagram Extended Transport Header contains the additional transport
    fields for datagram service. The DETH is only in datagram packets if
    indicated by the Base Transport Header OpCode field.
    """
    q_key = 0
    """Queue Key is required to authorize access to the receive queue
    """
    reserved = 0
    """Reserved
    """
    src_qp = 0
    """Source QP indicates the Work Queue Pair Number (QP) at the source.
    """

    def __str__(self):
        _q_key = '{:08X}'.format(self.q_key)
        _reserved = '{:02X}'.format(self.reserved)
        _src_qp = '{:06X}'.format(self.src_qp)
        return f"{_q_key}{_reserved}{_src_qp}".upper()

@dataclass
class IB:
    bth = BTH()
    reth = RETH()
    aeth = AETH()
    rdeth = RDETH()
    deth = DETH()

    def __str__(self):
        if self.bth.opcode == BTHOpcode.RC_SEND_FIRST or self.bth.opcode == BTHOpcode.RC_SEND_MIDDLE or self.bth.opcode == BTHOpcode.RC_SEND_LAST:
            return str(self.bth)
        if self.bth.opcode == BTHOpcode.RC_RDMA_WRITE_FIRST:
            return str(self.bth)+str(self.reth)
        if self.bth.opcode == BTHOpcode.RC_RDMA_WRITE_MIDDLE or self.bth.opcode == BTHOpcode.RC_RDMA_WRITE_LAST:
            return str(self.bth)
        if self.bth.opcode == BTHOpcode.RC_RDMA_READ_RESPONSE_FIRST or self.bth.opcode == BTHOpcode.RC_RDMA_READ_RESPONSE_LAST:
            return str(self.bth)+str(self.aeth)
        if self.bth.opcode == BTHOpcode.RC_RDMA_READ_RESPONSE_MIDDLE:
            return str(self.bth)
        if self.bth.opcode == BTHOpcode.RD_SEND_FIRST or self.bth.opcode == BTHOpcode.RD_SEND_MIDDLE or self.bth.opcode == BTHOpcode.RD_SEND_LAST:
            return str(self.bth)+str(self.rdeth)+str(self.deth)
        if self.bth.opcode == BTHOpcode.RD_RDMA_WRITE_FIRST:
            return str(self.bth)+str(self.rdeth)+str(self.deth)+str(self.reth)
        if self.bth.opcode == BTHOpcode.RD_RDMA_WRITE_MIDDLE or self.bth.opcode == BTHOpcode.RD_RDMA_WRITE_LAST:
            return str(self.bth)+str(self.rdeth)+str(self.deth)
        if self.bth.opcode == BTHOpcode.RD_RDMA_READ_RESPONSE_FIRST or self.bth.opcode == BTHOpcode.RD_RDMA_READ_RESPONSE_LAST:
            return str(self.bth)+str(self.rdeth)+str(self.aeth)
        if self.bth.opcode == BTHOpcode.RD_RDMA_READ_RESPONSE_MIDDLE:
            return str(self.bth)+str(self.rdeth)
        if self.bth.opcode == BTHOpcode.UD_SEND_ONLY:
            return str(self.bth)+str(self.deth)

    
    
    
        
    
        
    
        
    

    

