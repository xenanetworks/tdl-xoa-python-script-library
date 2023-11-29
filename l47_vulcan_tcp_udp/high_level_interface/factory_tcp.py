from .framework.l47test import L47Test
from .scenarios import tcp

async def tcpCC_1B():
    async with L47Test(tcp.TCP_CC_1B) as tcp_1B:
        await tcp_1B.pre_test()
        await tcp_1B.do_test()
        await tcp_1B.post_test()

async def tcpThroughput_800B() -> None:
    async with L47Test(tcp.TCP_Throughput_800B) as tcp_800B:
        await tcp_800B.pre_test()
        await tcp_800B.do_test()
        await tcp_800B.post_test()

async def tcpThroughput_1460B() -> None:
    async with L47Test(tcp.TCP_Throughput_1460B) as tcp_1460B:
        await tcp_1460B.pre_test()
        await tcp_1460B.do_test()
        await tcp_1460B.post_test()

async def tcpCps_1B() -> None:
    async with L47Test(tcp.TCP_Cps_1B) as tcp_1B:
        await tcp_1B.pre_test()
        await tcp_1B.do_test(True, True)
        await tcp_1B.post_test()

async def tcpCps_800B() -> None:
    async with L47Test(tcp.TCP_Cps_800B) as tcp_800B:
        await tcp_800B.pre_test()
        await tcp_800B.do_test(True, True)
        await tcp_800B.post_test()

async def tcp_64B() -> None:
    async with L47Test(tcp.TCP_Throughput_64B) as tcp_64B:
        await tcp_64B.pre_test()
        await tcp_64B.do_test()
        await tcp_64B.post_test()