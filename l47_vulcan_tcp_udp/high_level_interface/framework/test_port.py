import asyncio
import typing
from xoa_driver import ports
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver.misc import Hex

if typing.TYPE_CHECKING:
    from .l47test import TestCase

class TestPort:
    def __init__(self, port: "ports.PortL47", role: "enums.Role", test_case: "TestCase") -> None:
        self.port = port
        self.role = role
        self.state = self.port.info.traffic_state
        self.reservation_status = self.port.info.reservation
        self.__test_case = test_case
        self.speed = self.__test_case.config.speed
        self.ip_ver = self.__test_case.config.ip_ver
        self.c_range = self.__test_case.config.c_range
        self.s_range = self.__test_case.config.s_range
        self.pe_number = self.__test_case.config.chassis_pe_num
        self.port.on_state_change(self.__on_p_state)
        self.port.on_reservation_change(self.__on_reservation_status)

    async def __on_p_state(self, port: "ports.PortL47", v) -> None:
        self.state = enums.L47PortState(v.state)
    
    async def __on_reservation_status(self, port: "ports.PortL47", v) -> None:
        self.reservation_status = enums.ReservedStatus(v.status)
    
    async def prepare_port(self) -> None:
        if self.reservation_status is enums.ReservedStatus.RESERVED_BY_OTHER:
            await self.port.reservation.set_relinquish()
            while self.reservation_status is not enums.ReservedStatus.RELEASED:
                await asyncio.sleep(0.01) 
        await self.port.reservation.set_reserve() 
        await self.port.reset.set()
        await self.__wait_state(enums.L47PortState.OFF)
        await self.port.packet_engine.allocate.set(self.pe_number)
    
    async def __wait_state(self, state: enums.L47PortState) -> None:
        while enums.L47PortState(self.state) is not state:
            await asyncio.sleep(0.1)
    
    async def start_traffic(self) -> None:
        await self.port.traffic.set_prepare()
        await self.__wait_state(enums.L47PortState.PREPARE_RDY)
        await self.port.traffic.set_prerun()
        await self.__wait_state(enums.L47PortState.PRERUN_RDY)
        await self.port.traffic.set_on()
        await self.__wait_state(enums.L47PortState.RUNNING)
    
    async def stop_traffic(self) -> None:
        await self.port.traffic.set_stop()
        await self.__wait_state(enums.L47PortState.STOPPED)
        await self.port.traffic.set_off()
    
    async def print_port_tatistics(self) -> str:
        async def __do_fetch(dir: str):
            (eth, ipv4, arp, _tcp, ipv6, ndp) = await utils.apply(
                getattr(self.port.counters.eth, dir).get(),
                getattr(self.port.counters.ipv4, dir).get(),
                getattr(self.port.counters.arp, dir).get(),
                getattr(self.port.counters.tcp, dir).get(),
                getattr(self.port.counters.ipv6, dir).get(),
                getattr(self.port.counters.ndp, dir).get(),
            )
            pkt = eth.packet_count
            ip = ipv4.packet_count
            arpreq = arp.arp_request_count
            arprep = arp.arp_reply_count
            tcp = _tcp.packet_count
            ip6 = ipv6.packet_count
            ndpreq = ndp.ndp_request_count
            ndprep = ndp.ndp_reply_count
            return (self.port.kind.port_id, dir.upper(), pkt, ip, arpreq, arprep, ip6, ndpreq, ndprep, tcp)
        results = await asyncio.gather(*[__do_fetch(dir) for dir in ("rx", "tx")])
        return "\n".join(
            [
                "\n%-5s %-3s %-8s %-8s %-8s %-8s %-8s %-8s %-8s %-8s" % ("Port", "Dir", "Pkts", "IP", "ARPREQ", "ARPREP", "IP6", "NDPREQ", "NDPREP", "TCP"),
                "\n".join("%-5s %-3s %-8s %-8s %-8s %-8s %-8s %-8s %-8s %-8s" % result for result in results )
            ]
        )
    
    async def pre_test(self) -> None:
        cg = await self.port.connection_groups.create()
        await cg.l3.ip_version.set(self.ip_ver)
        
        ip_attr_name = "ipv4" if self.ip_ver == enums.L47IPVersion.IPV4 else "ipv6"
        attr_l3_ip = getattr(cg.l3, ip_attr_name)
        await utils.apply(
            attr_l3_ip.client_range.set(*self.c_range),
            attr_l3_ip.server_range.set(*self.s_range),
            cg.role.set(self.role),
            self.port.speed_selection.set(speed=self.speed),
            self.port.counters.clear.set(),
        )
        await self.__test_case.pre_test(cg, self.role)
