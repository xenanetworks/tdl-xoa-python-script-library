import asyncio
import typing
from xoa_driver.lli import commands as cmd
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver import misc
from . import fetch_func
from xoa_driver.misc import Hex
import ipaddress

class TestCaseUDP:
    def __init__(self, config) -> None:
        self.config = config
    
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        """Configuration of CG for all TestCases"""
        packet_size_future = (
            cmd.P4G_UDP_PACKET_SIZE_VALUE(*port_params).set(self.config.udp_size)
            if self.config.udp_type == enums.MSSType.FIXED 
            else cmd.P4G_UDP_PACKET_SIZE_MINMAX(*port_params).set(1, 1472)
        )
        await utils.apply(
            cmd.P4G_L4_PROTOCOL(*port_params).set_udp(),
            # Load profile
            cmd.P4G_LP_SHAPE(*port_params).set(*self.config.lp),
            cmd.P4G_LP_TIME_SCALE(*port_params).set_msecs(),
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_both(),
            # UDP packet size = fixed, 800 bytes (excl. ETH, IP, UDP headers) max = 1472
            cmd.P4G_UDP_PACKET_SIZE_TYPE(*port_params).set(self.config.udp_type),
            packet_size_future,
            cmd.P4G_L2_CLIENT_MAC(*port_params).set_dont_embed_ip("00DEAD010101"),
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_increment(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_infinite(0),
            # Using 100% of the port speed.
            cmd.P4G_RAW_UTILIZATION(*port_params).set(1000000),
            cmd.P4G_RAW_TX_DURING_RAMP(*port_params).set(enums.YesNo.YES, enums.YesNo.YES),
            # UDP streams live until the end of the test
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_once(),
        )
    
    async def do_test(self, test_resources) -> None:
        return None
    
    async def post_test(self, test_resources) -> None:
        est_conn = 0
        pps_sum = 0
        async def __do(tp) -> typing.Tuple[str, int, int]:
            return await asyncio.gather(
                tp.print_port_tatistics(),
                fetch_func.established_udp_total(*tp.port.params),
                fetch_func.eth_rx_counter(*tp.port.params)
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
    async def pre_only_client(self, port_params) -> None:
        await cmd.P4G_L2_CLIENT_MAC(*port_params).set_embed_ip("04F4A0000001")
    
    async def pre_only_server(self, port_params) -> None:
        await utils.apply(
            cmd.P4G_L2_SERVER_MAC(*port_params).set_embed_ip("04F4A0000000"),
            cmd.P4G_L2_USE_ADDRESS_RES(*port_params).set_yes(),
            cmd.P4G_L2_USE_GW(*port_params).set_yes(),
            cmd.P4G_NAT(*port_params).set_on(),
            cmd.P4G_L2_GW(*port_params).set(self.config.s_startip, Hex("04F4A0000000"))
        )
    
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        if port_role is enums.Role.CLIENT:
            await self.pre_only_client(port_params)
        else:
            await self.pre_only_server(port_params)


class UdpDNat(TestCaseUDP):
    async def pre_only_client(self, port_params) -> None:
        await utils.apply(
            cmd.P4G_SERVER_RANGE(*port_params).set(ipaddress.IPv4Address("16.0.254.254"), 1, 5000, 1),
            cmd.P4G_L2_CLIENT_MAC(*port_params).set_dont_embed_ip(Hex("00DEAD020202")),
            cmd.P4G_L2_GW(*port_params).set(ipaddress.IPv4Address("16.0.254.254"), Hex("00DEAD010101")),
        )
    
    async def pre_only_server(self, port_params) -> None:
        await utils.apply(
            cmd.P4G_L2_SERVER_MAC(*port_params).set_dont_embed_ip("00DEAD010101"),
            cmd.P4G_L2_GW(*port_params).set(ipaddress.IPv4Address("172.0.254.254"), Hex("00DEAD020202"))
        )
    
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        specific_port_fut = (
            self.pre_only_client(port_params)
            if port_role is enums.Role.CLIENT 
            else self.pre_only_server(port_params)
        )
        all_fut = utils.apply(
            cmd.P4G_L2_USE_ADDRESS_RES(*port_params).set_yes(),
            cmd.P4G_L2_USE_GW(*port_params).set_yes()
        )
        await asyncio.gather(all_fut, specific_port_fut)