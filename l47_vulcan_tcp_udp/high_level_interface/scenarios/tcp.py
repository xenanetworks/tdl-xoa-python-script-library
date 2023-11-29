import asyncio
import typing
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver.misc import ConnectionGroup
from . import fetch_func
from xoa_driver.misc import Hex

class TestCaseTCP:
    def __init__(self, config) -> None:
        self.config = config
    
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        """Configuration of CG for all TestCases"""
        # Using apply for batch commands
        await utils.apply(
            # TCP scenario
            cg.layer4_protocol.set_tcp(),
            # Load profile
            cg.load_profile.shape.set(*self.config.lp),
            cg.load_profile.time_scale.set_msecs(),
            cg.l3.diffserv.type.set_fixed(),
            cg.l3.diffserv.value.set(Hex("00")),
            cg.tcp.mss.type.set_fixed(),
            cg.tcp.rwnd.size.set(65535),
            cg.tcp.rwnd.scaling.set_yes(3),
            cg.tcp.ack.duplicate_thresholds.set(3),
            cg.tcp.rto.syn_value.set(3000, 32, 3),
            cg.tcp.rto.value.set_dynamic(2000, 32, 3),
            cg.tcp.cwnd.congestion_mode.set_reno(),
            ##use 100% speed
            cg.raw.utilization.set(1000000),
            cg.raw.tx.during_ramp.set(enums.YesNo.YES, enums.YesNo.YES),
            cg.l2.mac.client.set_dont_embed_ip("00DEAD010101")
        )
    
    async def post_test(self, test_resources) -> None:
        est_conn = 0
        async def __do(tp) -> typing.Tuple[str, int]:
            return await asyncio.gather(
                tp.print_port_tatistics(),
                fetch_func.established_tcp_total(tp.port)
            )
        result = await asyncio.gather(*[ __do(tp) for tp in test_resources.values() ])
        est_conn = sum( r[1] for r in result)
        print(*[r[0] for r in result], sep="\n")
        print(
            "\nGetting TCP stats",
            f"Requested conns: {self.config.c_conns}, established: {est_conn / 2:.0f}",
            sep="\n"
        )

class TcThroughput(TestCaseTCP):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.rxpps_max = 0
    
    async def do_test(self, test_resources) -> None:
        rxpps = sum( 
            await asyncio.gather(*[fetch_func.eth_rx_counter(tp.port) for tp in test_resources.values()]) 
        )
        if rxpps > self.rxpps_max:
            self.rxpps_max = rxpps
    
    async def post_test(self, test_resources) -> None:
        await super().post_test(test_resources)
        print("Max average Rx rate %d pps" % (self.rxpps_max))


class TCP_CC_1B(TcThroughput):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.tcp.mss.fixed_value.set(1460),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_both(),
            cg.raw.payload.type.set_fixed(),
            cg.raw.payload.total_length.set_finite(1),
            cg.raw.payload.content.set(0, 1, Hex("12")),
            cg.raw.payload.repeat_length.set(1),
            cg.raw.download_request.server_must_wait.set_yes(),
            cg.raw.download_request.content.set(1, Hex("42")),
            cg.raw.payload.rx_length.set_finite(1), 
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.lifetime.set_msecs(self.config.lp.duration),
            cg.raw.connection.repetitions.set_infinite(0),
        )


class TCP_Throughput_64B(TcThroughput):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.close_condition.set_none(),
            cg.raw.download_request.server_must_wait.set_yes(),
            cg.raw.connection.repetitions.set_finite(300),
            cg.raw.payload.repeat_length.set(64),
            cg.raw.payload.total_length.set_finite(64),
            ####  TCP protocol setup
            cg.tcp.cwnd.congestion_mode.set_new_reno(),
            cg.tcp.rwnd.scaling.set_yes(3),
            cg.tcp.rwnd.size.set(65535),
            cg.tcp.mss.type.set_fixed(),
            cg.tcp.mss.fixed_value.set(1460),
            cg.tcp.ack.duplicate_thresholds.set(3),
            cg.tcp.rto.value.set_dynamic(200, 32, 3),
            cg.tcp.rto.syn_value.set(2000, 32, 3),
            ###  Raw mode , upload
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_download(),
            cg.raw.payload.type.set_fixed(),
            cg.raw.payload.total_length.set_finite(64)
        )


class TCP_Throughput_800B(TcThroughput):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.tcp.mss.fixed_value.set(800),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_both(),
            cg.raw.payload.type.set_fixed(),
            cg.raw.payload.total_length.set_infinite(99999999999),
            cg.raw.payload.content.set(0, 800, Hex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
            cg.raw.payload.repeat_length.set(800),
            cg.raw.download_request.server_must_wait.set_yes(),
            cg.raw.download_request.content.set(40, Hex("474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a")),
            cg.raw.payload.rx_length.set_infinite(4096), 
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.lifetime.set_msecs(self.config.lp.duration),
            cg.raw.connection.repetitions.set_infinite(0),
        )

class TCP_Throughput_1460B(TcThroughput):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.tcp.mss.fixed_value.set(1460),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_both(),
            cg.raw.payload.type.set_increment(),
            cg.raw.payload.total_length.set_infinite(9999999999),

            cg.raw.payload.repeat_length.set(1460),
            cg.raw.download_request.server_must_wait.set_yes(),
            cg.raw.download_request.content.set(40, Hex("474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a")),
            cg.raw.payload.rx_length.set_infinite(4096),
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.lifetime.set_msecs(self.config.lp.duration),
            cg.raw.connection.repetitions.set_infinite(0),
        )

class TcCps(TestCaseTCP):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.max_estab = 0
        self.min_estab = self.config.c_conns / 5
    
    async def do_test(self, test_resources) -> None:
        estab = await fetch_func.established_tcp_rate(test_resources[enums.Role.CLIENT].port)
        if estab > self.max_estab:
            self.max_estab = estab
        if estab < self.min_estab and abs(estab-self.min_estab)/self.min_estab < 0.2:
            self.min_estab = estab

    async def post_test(self, test_resources) -> None:
        with open("./1.txt", "w") as fh_write:
            fh_write.writelines([str(self.max_estab), ' ', str(self.min_estab)])
        await super().post_test(test_resources)

class TCP_Cps_1B(TcCps):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.tcp.mss.fixed_value.set(1460),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_upload(),
            cg.raw.payload.type.set_fixed(),
            cg.raw.payload.total_length.set_finite(1),
            cg.raw.payload.content.set(0, 1, Hex("12")),
            cg.raw.payload.repeat_length.set(1),
            cg.raw.payload.rx_length.set_finite(1),
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.lifetime.set_msecs(1),
            cg.raw.connection.repetitions.set_infinite(0),
        )


class TCP_Cps_800B(TcCps):
    async def pre_test(self, cg: ConnectionGroup, port_role: "enums.Role") -> None:
        await super().pre_test(cg, port_role)
        await utils.apply(
            cg.tcp.mss.fixed_value.set(800),
            cg.test_application.set_raw(),
            cg.raw.test_scenario.set_upload(),
            cg.raw.payload.type.set_fixed(),
            cg.raw.payload.total_length.set_finite(800),
            cg.raw.payload.content.set(0, 800, Hex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
            cg.raw.payload.repeat_length.set(800),
            cg.raw.payload.rx_length.set_finite(800),
            cg.raw.connection.incarnation.set_immortal(),
            cg.raw.connection.lifetime.set_msecs(1),
            cg.raw.connection.repetitions.set_infinite(0),
        )