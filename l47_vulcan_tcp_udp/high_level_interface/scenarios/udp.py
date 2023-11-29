import asyncio
import typing
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver import misc
from . import fetch_func
from xoa_driver.misc import Hex
import ipaddress

class TestCaseUDP:
    def __init__(self, config) -> None:
        self.config = config
    
    async def pre_test(self, cg: misc.ConnectionGroup, port_role: "enums.Role") -> None:
        """Configuration of CG for all TestCases"""
        packet_size_future = (
            cg.udp.packet_size.value.set(self.config.udp_size)
            if self.config.udp_type == enums.MSSType.FIXED 
            else cg.udp.packet_size.range_limits.set(1, 1472)
        )
        await utils.apply(
            # TCP scenario
            cg.layer4_protocol.set_udp(),
            # Load profile
            cg.load_profile.shape.set(*self.config.lp),
            cg.load_profile.time_scale.set_msecs(),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_both(),
            # UDP packet size = fixed, 800 bytes (excl. ETH, IP, UDP headers) max = 1472
            cg.udp.packet_size.type.set(self.config.udp_type),
            packet_size_future,
            cg.l2.mac.client.set_dont_embed_ip("00DEAD010101"),
            cg.raw.payload.type.set_increment(),
            cg.raw.payload.total_length.set_infinite(0),
            # Using 100% of the port speed.
            cg.raw.utilization.set(1000000),
            cg.raw.tx.during_ramp.set(enums.YesNo.YES, enums.YesNo.YES),
            cg.raw.connection.incarnation.set_once()
        )
    
    async def do_test(self, test_resources) -> None:
        return None
    
    async def post_test(self, test_resources) -> None:
        est_conn = 0
        pps_sum = 0
        async def __do(tp) -> typing.Tuple[str, int, int]:
            return await asyncio.gather(
                tp.print_port_tatistics(),
                fetch_func.established_udp_total(tp.port),
                fetch_func.eth_rx_counter(tp.port)
            )
        result = await asyncio.gather(*[ __do(tp) for tp in test_resources.values() ])
        est_conn = sum( r[1] for r in result)
        pps_sum = sum( r[2] for r in result)
        pps = pps_sum / self.config.lp.duration * 1000
        print(*[r[0] for r in result], sep="\n")
        print(
            f"\nRequested conns: {self.config.c_conns}, established: {est_conn/2:.0f}",
            f"UDP {self.config.udp_type.name}/{self.config.udp_size}B average Rx rate {pps} pps",
            sep="\n"
        )


class UdpSNat(TestCaseUDP):
    async def pre_only_client(self, cg: misc.ConnectionGroup) -> None:
        await cg.l2.mac.client.set_embed_ip("04F4A0000001")
    
    async def pre_only_server(self, cg: misc.ConnectionGroup) -> None:
        await utils.apply(
            cg.l2.mac.server.set(mac_address=Hex("04F4A0000000"), mode=enums.EmbedIP.EMBED_IP),
            cg.l2.address_resolve.set_yes(),
            cg.l2.gateway.use.set_yes(),
            cg.l3.nat.set_on(),
            cg.l2.gateway.ipv4.set(self.config.s_startip, Hex("04F4A0000000"))
        )
    
    async def pre_test(self, cg: misc.ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        if port_role is enums.Role.CLIENT:
            await self.pre_only_client(cg)
        else:
            await self.pre_only_server(cg)


class UdpDNat(TestCaseUDP):
    async def pre_only_client(self, cg: misc.ConnectionGroup) -> None:
        await utils.apply(
            cg.l3.ipv4.server_range.set(ipaddress.IPv4Address("16.0.254.254"), 1, 5000, 1),
            cg.l2.mac.client.set_dont_embed_ip("00DEAD020202"),
            cg.l2.gateway.ipv4.set(ipaddress.IPv4Address("16.0.254.254"), Hex("00DEAD010101")),
        )
    
    async def pre_only_server(self, cg: misc.ConnectionGroup) -> None:
        await utils.apply(
            cg.l2.mac.server.set_dont_embed_ip(Hex("00DEAD010101")),
            cg.l2.gateway.ipv4.set(ipaddress.IPv4Address("172.0.254.254"), Hex("00DEAD020202"))
        )
    
    async def pre_test(self, cg: misc.ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        specific_port_fut = (
            self.pre_only_client(cg)
            if port_role is enums.Role.CLIENT 
            else self.pre_only_server(cg)
        )
        all_fut = utils.apply(
            cg.l2.address_resolve.set_yes(),
            cg.l2.gateway.use.set_yes()
        )
        await asyncio.gather(all_fut, specific_port_fut)