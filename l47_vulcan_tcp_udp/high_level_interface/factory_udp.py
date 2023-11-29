from .framework.l47test import L47Test
from .scenarios import udp

async def conntrack_udp_throughput():
    async with L47Test(udp.TestCaseUDP) as udpthroughput:
        await udpthroughput.pre_test()
        await udpthroughput.do_test()
        await udpthroughput.post_test()


async def conntrack_snat_throughput():
    async with L47Test(udp.UdpSNat) as udpthroughput:
        await udpthroughput.pre_test()
        await udpthroughput.do_test()
        await udpthroughput.post_test()



async def conntrack_dnat_throughput():
    async with L47Test(udp.UdpDNat) as udpthroughput:
        await udpthroughput.pre_test()
        await udpthroughput.do_test()
        await udpthroughput.post_test()
