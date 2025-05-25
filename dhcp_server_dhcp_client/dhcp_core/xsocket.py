# import available module
from enum import Enum
import queue
from xoa_driver import ports, enums
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex

class XSocket:
    class FilterType(Enum):
        DhcpClient = 0
        DhcpServer = 1
    
    class Error(Enum):
        Success = 0
        UnknownFailure = 1
    
    def __init__(self, port: ports.GenericL23Port, filter_type: FilterType) -> None:
        self.port               = port
        self.filter_type        = filter_type
        self.packet_list        = queue.Queue()
        self.__pc_offset        = 0
        
    async def start(self)-> Error:
        # reserve the port
        await mgmt.reserve_port(self.port)
        await self.port.capturer.state.set(enums.StartOrStop.STOP) # type: ignore
        
        # set a filter
        await self.__set_filter()
        
        # start the capture
        await self.port.capturer.state.set(enums.StartOrStop.START) # type: ignore
        return XSocket.Error.Success
    
    async def stop(self):
        # stop the capture
        await self.port.capturer.state.set(enums.StartOrStop.STOP) # type: ignore
    
    async def send_packet(self, packet: bytes) -> Error:
        # send the packet throug xmit
        packet += b'\x00\x00\x00\x00'
        await self.port.tx_single_pkt.send.set(hex_data=Hex(packet.hex())) # type: ignore
        return XSocket.Error.Success
    
    async def receive_packet(self) -> tuple[Error, bytes]:
        # check if there is any packet in the packet_list -> return the packet
        if not self.packet_list.empty():
            return (XSocket.Error.Success, self.packet_list.get())
        
        # 2-1 read status
        pc_stats = await self.port.capturer.stats.get()
        
        # 2-2 read packet from offset to the end
        for cap_idx in range(self.__pc_offset, pc_stats.packets):
            _packet_list = await self.port.capturer.obtain_captured()
            pc_packet_res = await _packet_list[cap_idx].packet.get()
            self.packet_list.put(bytes.fromhex(pc_packet_res.hex_data))
            
        # 2-3 if status == is_running
        if pc_stats.status == 0:
            self.__pc_offset = pc_stats.packets
        else:
            self.__pc_offset = 0
            await self.port.capturer.state.set(enums.StartOrStop.START) # type: ignore
        
        # 3- check if there is any packet in the packet_list and if there is any return it
        if not self.packet_list.empty():
            return (XSocket.Error.Success, self.packet_list.get())
        
        return (XSocket.Error.Success, b"")
            
    async def __set_filter_dhcp_req(self):
        # set filter that 1-ip.proto==0x11 2-udp.src==68 3-udp.dst==67
        # 1- POS 16 -> 0x00 00 00 00 00 00 00 FF  || 0x00 00 00 00 00 00 00 11
        # 2- POS 32 -> 0x00 00 FF FF FF FF 00 00  || 0x00 00 00 44 00 43 00 00
        
        filter_obj = await self.port.filters.create()
        await filter_obj.enable.set_off()
        # await enums.PF_INDICES(self.tester, self.module_id, self.port_id).set([0])
        # await enums.PF_ENABLE(self.tester, self.module_id, self.port_id, 0).set(enums.OnOff.OFF)
        
        match_term_obj_1 = await self.port.match_terms.create()
        match_term_obj_2 = await self.port.match_terms.create()
        await match_term_obj_1.protocol.set([enums.ProtocolOption.ETHERNET])
        await match_term_obj_2.protocol.set([enums.ProtocolOption.ETHERNET])
        # await enums.PM_INDICES(self.tester, self.module_id, self.port_id).set([0,1])
        # await enums.PM_PROTOCOL(self.tester, self.module_id, self.port_id, 0).set([enums.ProtocolOption.ETHERNET])
        # await enums.PM_PROTOCOL(self.tester, self.module_id, self.port_id, 1).set([enums.ProtocolOption.ETHERNET])
        
        # 1 - set match term 1
        await match_term_obj_1.position.set(byte_offset=16)
        await match_term_obj_1.match.set(mask=Hex('00000000000000FF'), value=Hex('0000000000000011'))
        # await enums.PM_POSITION(self.tester, self.module_id, self.port_id, 0).set(16)
        # await enums.PM_MATCH(self.tester, self.module_id, self.port_id, 0).set(mask='00000000000000FF', value='0000000000000011')
        
        # 2 - set match term 2
        await match_term_obj_2.position.set(byte_offset=32)
        await match_term_obj_2.match.set(mask=Hex('0000FFFFFFFF0000'), value=Hex('0000004400430000'))
        # await enums.PM_POSITION(self.tester, self.module_id, self.port_id, 1).set(32)
        # await enums.PM_MATCH(self.tester, self.module_id, self.port_id, 1).set(mask='0000FFFFFFFF0000', value='0000004400430000')
        
        # set filter comment and condition
        await filter_obj.comment.set("DHCP Request")
        await filter_obj.condition.set(0, 0, 0, 0, 3, 0)
        await filter_obj.enable.set_on()
        # await enums.PF_INDICES(self.tester, self.module_id, self.port_id).set([0])
        # await enums.PF_COMMENT(self.tester, self.module_id, self.port_id, 0).set("DHCP Request")
        # await enums.PF_CONDITION(self.tester, self.module_id, self.port_id, 0).set(0, 0, 0, 0, 3, 0)
        # await enums.PF_ENABLE(self.tester, self.module_id, self.port_id, 0).set(enums.OnOff.ON)
        
        # set the trigger and keep
        await self.port.capturer.trigger.set(
            start_criteria=enums.StartTrigger.ON, 
            start_criteria_filter=filter_obj.kind.index_id, 
            stop_criteria=enums.StopTrigger.FULL, 
            stop_criteria_filter=filter_obj.kind.index_id)
        await self.port.capturer.keep.set(kind=enums.PacketType.FILTER, index=filter_obj.kind.index_id, byte_count=-1)
        # await enums.PC_TRIGGER(self.tester, self.module_id, self.port_id).set(0, 0, 0, 0)
        # await enums.PC_KEEP(self.tester, self.module_id, self.port_id).set(enums.PacketType.FILTER, 0, -1)
    
    async def __set_filter_dhcp_res(self):
        # set filter that 1-ip.proto==0x11 2-udp.src==67 3-udp.dst==68
        # 1- POS 16 -> 0x00 00 00 00 00 00 00 FF  || 0x00 00 00 00 00 00 00 11
        # 2- POS 32 -> 0x00 00 FF FF FF FF 00 00  || 0x00 00 00 43 00 44 00 00

        filter_obj = await self.port.filters.create()
        await filter_obj.enable.set_off()
        # await enums.PF_INDICES(self.tester, self.module_id, self.port_id).set([0])
        # await enums.PF_ENABLE(self.tester, self.module_id, self.port_id, 0).set(enums.OnOff.OFF)
        
        match_term_obj_1 = await self.port.match_terms.create()
        match_term_obj_2 = await self.port.match_terms.create()
        await match_term_obj_1.protocol.set([enums.ProtocolOption.ETHERNET])
        await match_term_obj_2.protocol.set([enums.ProtocolOption.ETHERNET])

        # await enums.PM_INDICES(self.tester, self.module_id, self.port_id).set([0,1])
        # await enums.PM_PROTOCOL(self.tester, self.module_id, self.port_id, 0).set([enums.ProtocolOption.ETHERNET])
        # await enums.PM_PROTOCOL(self.tester, self.module_id, self.port_id, 1).set([enums.ProtocolOption.ETHERNET])
        
        # 1 - set match term 1
        await match_term_obj_1.position.set(byte_offset=16)
        await match_term_obj_1.match.set(mask=Hex('00000000000000FF'), value=Hex('0000000000000011'))
        # await enums.PM_POSITION(self.tester, self.module_id, self.port_id, 0).set(16)
        # await enums.PM_MATCH(self.tester, self.module_id, self.port_id, 0).set(mask='00000000000000FF', value='0000000000000011')
        
        # 2 - set match term 2
        await match_term_obj_2.position.set(byte_offset=32)
        await match_term_obj_2.match.set(mask=Hex('0000FFFFFFFF0000'), value=Hex('0000004300440000'))
        # await enums.PM_POSITION(self.tester, self.module_id, self.port_id, 1).set(32)
        # await enums.PM_MATCH(self.tester, self.module_id, self.port_id, 1).set(mask='0000FFFFFFFF0000', value='0000004300440000')
        
        # set filter comment and condition
        await filter_obj.comment.set("DHCP Response")
        await filter_obj.condition.set(0, 0, 0, 0, 3, 0)
        await filter_obj.enable.set_on()
        # await enums.PF_COMMENT(self.tester, self.module_id, self.port_id, 0).set("DHCP Response")
        # await enums.PF_CONDITION(self.tester, self.module_id, self.port_id, 0).set(0, 0, 0, 0, 3, 0)
        # await enums.PF_ENABLE(self.tester, self.module_id, self.port_id, 0).set(enums.OnOff.ON)
        
        # set the trigger and keep
        await self.port.capturer.trigger.set(
            start_criteria=enums.StartTrigger.ON, 
            start_criteria_filter=filter_obj.kind.index_id, 
            stop_criteria=enums.StopTrigger.FULL, 
            stop_criteria_filter=filter_obj.kind.index_id)
        await self.port.capturer.keep.set(kind=enums.PacketType.FILTER, index=filter_obj.kind.index_id, byte_count=-1)
        # await enums.PC_TRIGGER(self.tester, self.module_id, self.port_id).set(0, 0, 0, 0)
        # await enums.PC_KEEP(self.tester, self.module_id, self.port_id).set(enums.PacketType.FILTER, 0, -1)
    
    async def __set_filter(self):
        if self.filter_type == XSocket.FilterType.DhcpClient:
            await self.__set_filter_dhcp_res()
        elif self.filter_type == XSocket.FilterType.DhcpServer:
            await self.__set_filter_dhcp_req()
        else:
            print("Error: XSocket --> Wrong filter type!!!")
            exit(-1)
    
    
    
    