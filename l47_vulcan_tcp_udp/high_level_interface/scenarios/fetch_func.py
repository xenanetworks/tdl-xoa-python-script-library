from xoa_driver import ports

async def established_tcp_total(port: ports.PortL47) -> int:
    cg = port.connection_groups.obtain(0)
    rate = await cg.tcp.counters.state.total.get()
    return rate.established


async def eth_rx_counter(port: ports.PortL47) -> int:
    counter = await port.counters.eth.rx.get()
    return counter.packet_count


async def established_tcp_rate(port: ports.PortL47) -> int:
    cg = port.connection_groups.obtain(0)
    rate = await cg.tcp.counters.state.rate.get()
    return rate.established


async def established_udp_total(port: ports.PortL47) -> int:
    cg = port.connection_groups.obtain(0)
    rate = await cg.udp.counters.state.total.get()
    return rate.opened