# import available module
from xoa_driver import utils
from xoa_driver.lli import commands as cmd
from xoa_driver.lli import TransportationHandler
from enum import Enum
from typing import List
import queue



class XSocket:
    class FilterType(Enum):
        DhcpClient = 0
        DhcpServer = 1
    
    class Error(Enum):
        Success             = 0
        UnknownFailure      = 1
        
    chassis_handler:    TransportationHandler
    module_id:          int
    port_id:            int
    filter_type:        FilterType
    packet_list:        queue.Queue
    __pc_offset:        int
    
    def __init__(self, chassis_handler: TransportationHandler, module_id: int, port_id: int, filter_type: FilterType) -> None:
        self.chassis_handler    = chassis_handler
        self.module_id          = module_id
        self.port_id            = port_id
        self.filter_type        = filter_type
        self.packet_list        = queue.Queue()
        self.__pc_offset        = 0
        
    async def start(self)-> Error:
        await cmd.P_RESERVATION(self.chassis_handler, self.module_id, self.port_id).set(operation=cmd.ReservedAction.RESERVE)
        
        await cmd.P_CAPTURE(self.chassis_handler, self.module_id, self.port_id).set(cmd.StartOrStop.STOP)
        
        # set a filter
        await self.__set_filter()
        
        # start the capture
        await cmd.P_CAPTURE(self.chassis_handler, self.module_id, self.port_id).set(cmd.StartOrStop.START)
        return XSocket.Error.Success
    
    async def stop(self):
        # stop the capture
        await cmd.P_CAPTURE(self.chassis_handler, self.module_id, self.port_id).set(cmd.StartOrStop.STOP)
    
    async def send_packet(self, packet: bytes) -> Error:
        # send the packet throug xmit
        packet += b'\x00\x00\x00\x00'
        await cmd.P_XMITONE(self.chassis_handler, self.module_id, self.port_id).set(packet.hex())
        return XSocket.Error.Success
    
    async def receive_packet(self) -> tuple[Error, bytes]:
        # check if there is any packet in the packet_list -> return the packet
        if not self.packet_list.empty():
            return [XSocket.Error.Success, self.packet_list.get()]
        
        # 2-1 read status
        pc_stats = await cmd.PC_STATS(self.chassis_handler, self.module_id, self.port_id).get()
        
        # 2-2 read packet from offset to the end
        for cap_idx in range(self.__pc_offset, pc_stats.packets):
            pc_packet_res = await cmd.PC_PACKET(self.chassis_handler, self.module_id, self.port_id, cap_idx).get()
            self.packet_list.put(bytes.fromhex(pc_packet_res.hex_data))
            
        # 2-3 if status == is_running
        if pc_stats.status == 0:
            self.__pc_offset = pc_stats.packets
        else:
            self.__pc_offset = 0
            await cmd.P_CAPTURE(self.chassis_handler, self.module_id, self.port_id).set(cmd.StartOrStop.START)
        
        # 3- check if there is any packet in the packet_list and if there is any return it
        if not self.packet_list.empty():
            return [XSocket.Error.Success, self.packet_list.get()]
        
        return [XSocket.Error.Success, None]
            
    async def __set_filter_dhcp_req(self):
        # set filter that 1-ip.proto==0x11 2-udp.src==68 3-udp.dst==67
        # 1- POS 16 -> 0x00 00 00 00 00 00 00 FF  || 0x00 00 00 00 00 00 00 11
        # 2- POS 32 -> 0x00 00 FF FF FF FF 00 00  || 0x00 00 00 44 00 43 00 00
        
        await cmd.PF_INDICES(self.chassis_handler, self.module_id, self.port_id).set([0])
        await cmd.PF_ENABLE(self.chassis_handler, self.module_id, self.port_id, 0).set(cmd.OnOff.OFF)
        
        await cmd.PM_INDICES(self.chassis_handler, self.module_id, self.port_id).set([0,1])
        await cmd.PM_PROTOCOL(self.chassis_handler, self.module_id, self.port_id, 0).set([cmd.ProtocolOption.ETHERNET])
        await cmd.PM_PROTOCOL(self.chassis_handler, self.module_id, self.port_id, 1).set([cmd.ProtocolOption.ETHERNET])
        
        # 1
        await cmd.PM_POSITION(self.chassis_handler, self.module_id, self.port_id, 0).set(16)
        await cmd.PM_MATCH(self.chassis_handler, self.module_id, self.port_id, 0).set(mask='00000000000000FF', value='0000000000000011')
        
        # 2
        await cmd.PM_POSITION(self.chassis_handler, self.module_id, self.port_id, 1).set(32)
        await cmd.PM_MATCH(self.chassis_handler, self.module_id, self.port_id, 1).set(mask='0000FFFFFFFF0000', value='0000004400430000')
        
        await cmd.PF_INDICES(self.chassis_handler, self.module_id, self.port_id).set([0])
        await cmd.PF_COMMENT(self.chassis_handler, self.module_id, self.port_id, 0).set("DHCP Request")
        await cmd.PF_CONDITION(self.chassis_handler, self.module_id, self.port_id, 0).set(0, 0, 0, 0, 3, 0)
        await cmd.PF_ENABLE(self.chassis_handler, self.module_id, self.port_id, 0).set(cmd.OnOff.ON)
        
        await cmd.PC_TRIGGER(self.chassis_handler, self.module_id, self.port_id).set(0, 0, 0, 0)
        await cmd.PC_KEEP(self.chassis_handler, self.module_id, self.port_id).set(cmd.PacketType.FILTER, 0, -1)
    
    async def __set_filter_dhcp_res(self):
        # set filter that 1-ip.proto==0x11 2-udp.src==67 3-udp.dst==68
        # 1- POS 16 -> 0x00 00 00 00 00 00 00 FF  || 0x00 00 00 00 00 00 00 11
        # 2- POS 32 -> 0x00 00 FF FF FF FF 00 00  || 0x00 00 00 43 00 44 00 00
        await cmd.PF_INDICES(self.chassis_handler, self.module_id, self.port_id).set([0])
        await cmd.PF_ENABLE(self.chassis_handler, self.module_id, self.port_id, 0).set(cmd.OnOff.OFF)
        
        await cmd.PM_INDICES(self.chassis_handler, self.module_id, self.port_id).set([0,1])
        
        await cmd.PM_PROTOCOL(self.chassis_handler, self.module_id, self.port_id, 0).set([cmd.ProtocolOption.ETHERNET])
        await cmd.PM_PROTOCOL(self.chassis_handler, self.module_id, self.port_id, 1).set([cmd.ProtocolOption.ETHERNET])
        
        # 1
        await cmd.PM_POSITION(self.chassis_handler, self.module_id, self.port_id, 0).set(16)
        await cmd.PM_MATCH(self.chassis_handler, self.module_id, self.port_id, 0).set(mask='00000000000000FF', value='0000000000000011')
        
        # 2
        await cmd.PM_POSITION(self.chassis_handler, self.module_id, self.port_id, 1).set(32)
        await cmd.PM_MATCH(self.chassis_handler, self.module_id, self.port_id, 1).set(mask='0000FFFFFFFF0000', value='0000004300440000')
        
        await cmd.PF_COMMENT(self.chassis_handler, self.module_id, self.port_id, 0).set("DHCP Response")
        await cmd.PF_CONDITION(self.chassis_handler, self.module_id, self.port_id, 0).set(0, 0, 0, 0, 3, 0)
        await cmd.PF_ENABLE(self.chassis_handler, self.module_id, self.port_id, 0).set(cmd.OnOff.ON)
        
        await cmd.PC_TRIGGER(self.chassis_handler, self.module_id, self.port_id).set(0, 0, 0, 0)
        await cmd.PC_KEEP(self.chassis_handler, self.module_id, self.port_id).set(cmd.PacketType.FILTER, 0, -1)
    
    async def __set_filter(self):
        if self.filter_type == XSocket.FilterType.DhcpClient:
            await self.__set_filter_dhcp_res()
        elif self.filter_type == XSocket.FilterType.DhcpServer:
            await self.__set_filter_dhcp_req()
        else:
            print("Error: XSocket --> Wrong filter type!!!")
            exit(-1)
    
    
    
    