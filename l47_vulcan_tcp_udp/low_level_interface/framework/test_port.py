import asyncio
import typing

from xoa_driver.lli import commands as cmd
from xoa_driver import lli
from xoa_driver import utils
from xoa_driver import enums

if typing.TYPE_CHECKING:
    from .l47test import TestCase
    from .config import PortInfo

class PassingParams(typing.NamedTuple):
    transport: "lli.TransportationHandler"
    module_id: int
    port_id: int
    cg_id: int

class TestPort:
    def __init__(self, transport: "lli.TransportationHandler", port_kind: "PortInfo", role: "enums.Role", test_case: "TestCase") -> None:
        self.transport = transport
        self.port_kind = port_kind
        self.role = role
        self.state = enums.L47PortState.OFF
        self.reservation_status = enums.ReservedStatus.RELEASED
        self.__test_case = test_case
        self.cg_id = self.__test_case.config.cg_id
        self.speed = self.__test_case.config.speed
        self.ip_ver = self.__test_case.config.ip_ver
        self.c_range = self.__test_case.config.c_range
        self.s_range = self.__test_case.config.s_range
        self.pe_number = self.__test_case.config.chassis_pe_num
        self.transport.subscribe(cmd.P4_STATE, self.__on_p_state)
        self.transport.subscribe(cmd.P_RESERVATION, self.__on_reservation_status)
    
    def __is_me(self, response) -> bool:
        kind = (
            response.header.module_index,
            response.header.port_index,
        )
        return self.port_kind == kind or response.values
    
    async def __on_p_state(self, response) -> None:
        if not self.__is_me(response):
            return None
        self.state = enums.L47PortState(response.values.state)
        
    async def __on_reservation_status(self, response) -> None:
        if not self.__is_me(response):
            return None
        self.reservation_status = enums.ReservedStatus(response.values.status)
    
    @property
    def is_reserved_by_me(self) -> bool:
        return self.reservation_status is enums.ReservedStatus.RESERVED_BY_YOU
    
    @property
    def params(self) -> "PassingParams":
        return PassingParams( 
            self.transport, 
            self.port_kind.module_id, 
            self.port_kind.port_id, 
            self.cg_id
        )
    
    async def prepare_port(self) -> None:
        (
            port_st,
            reservation
        ) = await utils.apply(
            cmd.P4_STATE(self.transport, *self.port_kind).get(),
            cmd.P_RESERVATION(self.transport, *self.port_kind).get()
        )
        self.state = enums.L47PortState(port_st.state)
        self.reservation_status = enums.ReservedStatus(reservation.status)
        if self.reservation_status is enums.ReservedStatus.RESERVED_BY_OTHER:
            await cmd.P_RESERVATION(self.transport, *self.port_kind).set_relinquish()
            reservation_status = (await cmd.P_RESERVATION(self.transport, *self.port_kind).get()).status
            while enums.ReservedStatus(reservation_status) is not enums.ReservedStatus.RELEASED:
                await asyncio.sleep(0.1)
                reservation_status = (await cmd.P_RESERVATION(self.transport, *self.port_kind).get()).status
        await cmd.P_RESERVATION(self.transport, *self.port_kind).set_reserve()
        await cmd.P_RESET(self.transport, *self.port_kind).set()
        await self.__wait_state(enums.L47PortState.OFF)
        await cmd.P4E_ALLOCATE(self.transport, *self.port_kind).set(self.pe_number)
    
    async def __wait_state(self, state: enums.L47PortState) -> None:
        while enums.L47PortState(self.state) is not state:
            await asyncio.sleep(0.1)
    
    async def start_traffic(self) -> None:
        await cmd.P4_TRAFFIC(self.transport, *self.port_kind).set_prepare()
        await self.__wait_state(enums.L47PortState.PREPARE_RDY)
        await cmd.P4_TRAFFIC(self.transport, *self.port_kind).set_prerun()
        await self.__wait_state(enums.L47PortState.PRERUN_RDY)
        await cmd.P4_TRAFFIC(self.transport, *self.port_kind).set_on()
        await self.__wait_state(enums.L47PortState.RUNNING)
    
    async def stop_traffic(self) -> None:
        await cmd.P4_TRAFFIC(self.transport, *self.port_kind).set_stop()
        await self.__wait_state(enums.L47PortState.STOPPED)
        await cmd.P4_TRAFFIC(self.transport, *self.port_kind).set_off()
    
    async def print_port_tatistics(self) -> str:
        
        async def __do_fetch(dir: str):
            (eth, ipv4, arp, _tcp, ipv6, ndp) = await utils.apply(
                getattr(cmd, f"P4_ETH_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
                getattr(cmd, f"P4_IPV4_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
                getattr(cmd, f"P4_ARP_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
                getattr(cmd, f"P4_TCP_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
                getattr(cmd, f"P4_IPV6_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
                getattr(cmd, f"P4_NDP_{dir}_COUNTERS")(self.transport, *self.port_kind).get(),
            )
            pkt = eth.packet_count
            ip = ipv4.packet_count
            arpreq = arp.arp_request_count
            arprep = arp.arp_reply_count
            tcp = _tcp.packet_count
            ip6 = ipv6.packet_count
            ndpreq = ndp.ndp_request_count
            ndprep = ndp.ndp_reply_count
            return (self.port_kind[1], dir, pkt, ip, arpreq, arprep, ip6, ndpreq, ndprep, tcp)
        results = await asyncio.gather(*[__do_fetch(dir) for dir in ("RX", "TX")])
        return "\n".join(
            [
                "\n%-5s %-3s %-8s %-8s %-8s %-8s %-8s %-8s %-8s %-8s" % ("Port", "Dir", "Pkts", "IP", "ARPREQ", "ARPREP", "IP6", "NDPREQ", "NDPREP", "TCP"),
                "\n".join("%-5s %-3s %-8s %-8s %-8s %-8s %-8s %-8s %-8s %-8s" % result for result in results )
            ]
        )
    
    async def pre_test(self) -> None:
        ip_attr_name = "" if self.ip_ver == enums.L47IPVersion.IPV4 else "IPV6_"
        await utils.apply(
            cmd.P4G_CREATE(*self.params).set(),
            cmd.P4G_IP_VERSION(*self.params).set(self.ip_ver),
            getattr(cmd, f"P4G_{ip_attr_name}CLIENT_RANGE")(*self.params).set(*self.c_range),
            getattr(cmd, f"P4G_{ip_attr_name}SERVER_RANGE")(*self.params).set(*self.s_range),
            cmd.P4G_ROLE(*self.params).set(self.role),
            cmd.P4_SPEEDSELECTION(self.transport, *self.port_kind).set(self.speed),
            cmd.P4_CLEAR_COUNTERS(self.transport, *self.port_kind).set(),
        )
        await self.__test_case.pre_test(self.params, self.role)
