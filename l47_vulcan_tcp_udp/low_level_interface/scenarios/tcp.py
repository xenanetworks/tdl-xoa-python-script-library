import asyncio
import typing
from xoa_driver.lli import commands as cmd
from xoa_driver import utils
from xoa_driver import enums
from . import fetch_func
from xoa_driver.misc import Hex


class TestCaseTCP:
    def __init__(self, config) -> None:
        self.config = config
    
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        """Configuration of CG for all TestCases"""
        # Using apply for batch commands
        await utils.apply(
            # TCP scenario
            cmd.P4G_L4_PROTOCOL(*port_params).set_tcp(),
            cmd.P4G_LP_SHAPE(*port_params).set(*self.config.lp),
            # Load profile
            cmd.P4G_LP_TIME_SCALE(*port_params).set_msecs(),
            cmd.P4G_IP_DS_TYPE(*port_params).set_fixed(),
            cmd.P4G_IP_DS_VALUE(*port_params).set(Hex("00")),
            cmd.P4G_TCP_MSS_TYPE(*port_params).set_fixed(),
            cmd.P4G_TCP_WINDOW_SIZE(*port_params).set(65535),
            cmd.P4G_TCP_WINDOW_SCALING(*port_params).set_yes(3),
            cmd.P4G_TCP_DUP_THRES(*port_params).set(3),
            cmd.P4G_TCP_SYN_RTO(*port_params).set(3000, 32, 3),
            cmd.P4G_TCP_RTO(*port_params).set_dynamic(2000, 32, 3),
            cmd.P4G_TCP_CONGESTION_MODE(*port_params).set_reno(),
            ##use 100% speed
            cmd.P4G_RAW_UTILIZATION(*port_params).set(1000000),
            cmd.P4G_RAW_TX_DURING_RAMP(*port_params).set(enums.YesNo.YES, enums.YesNo.YES),
            cmd.P4G_L2_CLIENT_MAC(*port_params).set_dont_embed_ip(Hex("00DEAD010101")),
        )
    
    async def post_test(self, test_resources) -> None:
        est_conn = 0
        async def __do(tp) -> typing.Tuple[str, int]:
            return await asyncio.gather(
                tp.print_port_tatistics(),
                fetch_func.established_tcp_total(*tp.params)
            )
        result = await asyncio.gather(*[ __do(tp) for tp in test_resources.values() ])
        est_conn = sum(r[1] for r in result)
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
            await asyncio.gather(*[ fetch_func.eth_rx_counter(*tp.params[:3]) for tp in test_resources.values()]) 
        )
        if rxpps > self.rxpps_max:
            self.rxpps_max = rxpps
    
    async def post_test(self, test_resources) -> None:
        await super().post_test(test_resources)
        print("Max average Rx rate %d pps" % (self.rxpps_max))


class TCP_CC_1B(TcThroughput):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        await utils.apply(
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(1460),
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_both(),
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_fixed(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_finite(1),
            cmd.P4G_RAW_PAYLOAD(*port_params).set(0, 1, Hex("12")),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(1),
            cmd.P4G_RAW_HAS_DOWNLOAD_REQ(*port_params).set_yes(),
            cmd.P4G_RAW_DOWNLOAD_REQUEST(*port_params).set(1, Hex("42")),
            cmd.P4G_RAW_RX_PAYLOAD_LEN(*port_params).set_finite(1),
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            ##############need modify  lp="5000 30000 35000 30000"
            cmd.P4G_RAW_CONN_LIFETIME(*port_params).set_msecs(self.config.lp.duration),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_infinite(0),
        )


class TCP_Throughput_64B(TcThroughput):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        await utils.apply(
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            cmd.P4G_RAW_CLOSE_CONN(*port_params).set_none(),
            cmd.P4G_RAW_HAS_DOWNLOAD_REQ(*port_params).set_yes(),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_finite(300),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(64),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_finite(64),
            ####TCP protocol setup
            cmd.P4G_TCP_CONGESTION_MODE(*port_params).set_new_reno(),
            cmd.P4G_TCP_WINDOW_SCALING(*port_params).set_yes(3),
            cmd.P4G_TCP_WINDOW_SIZE(*port_params).set(65535),
            cmd.P4G_TCP_MSS_TYPE(*port_params).set_fixed(),
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(1460),
            cmd.P4G_TCP_DUP_THRES(*port_params).set(3),
            cmd.P4G_TCP_RTO(*port_params).set_dynamic(200, 32, 3),
            cmd.P4G_TCP_SYN_RTO(*port_params).set(2000, 32, 3),
            ###  Raw mode , uoload
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_download(),
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_fixed(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_finite(64),
        )


class TCP_Throughput_800B(TcThroughput):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        await utils.apply(
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(800),
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_both(),
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_fixed(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_infinite(99999999999),
            cmd.P4G_RAW_PAYLOAD(*port_params).set(0, 800, Hex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(800),
            cmd.P4G_RAW_HAS_DOWNLOAD_REQ(*port_params).set_yes(),
            cmd.P4G_RAW_DOWNLOAD_REQUEST(*port_params).set(40, Hex("474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a")),
            cmd.P4G_RAW_RX_PAYLOAD_LEN(*port_params).set_infinite(4096),
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            cmd.P4G_RAW_CONN_LIFETIME(*port_params).set_msecs(self.config.lp.duration),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_infinite(0),
        )

class TCP_Throughput_1460B(TcThroughput):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        
        await utils.apply(
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(1460),
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_both(),
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_increment(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_infinite(9999999999),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(1460),
            
            cmd.P4G_RAW_HAS_DOWNLOAD_REQ(*port_params).set_yes(),
            cmd.P4G_RAW_DOWNLOAD_REQUEST(*port_params).set(40, Hex("474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a")),
            cmd.P4G_RAW_RX_PAYLOAD_LEN(*port_params).set_infinite(4096),
            
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            cmd.P4G_RAW_CONN_LIFETIME(*port_params).set_msecs(self.config.lp.duration),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_infinite(0),
        )

class TcCps(TestCaseTCP):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.max_estab = 0
        self.min_estab = self.config.c_conns / 5
    
    async def do_test(self, test_resources) -> None:
        estab = await fetch_func.established_tcp_rate(*test_resources[enums.Role.CLIENT].params)
        if estab > self.max_estab:
            self.max_estab = estab
        if estab < self.min_estab and abs(estab-self.min_estab)/self.min_estab < 0.2:
            self.min_estab = estab

    async def post_test(self, test_resources) -> None:
        with open("./1.txt", "w") as fh_write:
            fh_write.writelines([str(self.max_estab), ' ', str(self.min_estab)])
        await super().post_test(test_resources)

class TCP_Cps_1B(TcCps):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        await utils.apply(
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(1460),
            ###  Raw mode , uoload
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_upload(),
            ### paylod setup ,download 1B ,upload 1B 
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_fixed(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_finite(1),
            cmd.P4G_RAW_PAYLOAD(*port_params).set(0, 1, Hex("12")),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(1),
            cmd.P4G_RAW_RX_PAYLOAD_LEN(*port_params).set_finite(1),
            ###IMMORTAL :after the connection lifetime,close the connection, and a new connection use a new port  
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            ### one connection lifetime ,should close connection as soon as possible
            cmd.P4G_RAW_CONN_LIFETIME(*port_params).set_msecs(1),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_infinite(0),
        )


class TCP_Cps_800B(TcCps):
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None:
        await super().pre_test(port_params, port_role)
        await utils.apply(
            cmd.P4G_TCP_MSS_VALUE(*port_params).set(800),
            ###  Raw mode , uoload
            cmd.P4G_TEST_APPLICATION(*port_params).set_raw(),
            cmd.P4G_RAW_TEST_SCENARIO(*port_params).set_upload(),
            ### paylod setup,upload 600B 
            cmd.P4G_RAW_PAYLOAD_TYPE(*port_params).set_fixed(),
            cmd.P4G_RAW_PAYLOAD_TOTAL_LEN(*port_params).set_finite(800),
            cmd.P4G_RAW_PAYLOAD(*port_params).set(0, 800, Hex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
            cmd.P4G_RAW_PAYLOAD_REPEAT_LEN(*port_params).set(800),
            cmd.P4G_RAW_RX_PAYLOAD_LEN(*port_params).set_finite(800),
            ###IMMORTAL :after the connection lifetime,close the connection, and a new connection use a new port  
            cmd.P4G_RAW_CONN_INCARNATION(*port_params).set_immortal(),
            ### one connection lifetime ,should close connection as soon as possible
            cmd.P4G_RAW_CONN_LIFETIME(*port_params).set_msecs(1),
            cmd.P4G_RAW_CONN_REPETITIONS(*port_params).set_infinite(0),
        )