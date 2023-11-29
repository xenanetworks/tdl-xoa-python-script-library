from xoa_driver.lli import commands as cmd

async def established_tcp_total(transpor, m_id: int, p_id: int, cg_id: int) -> int:
    rate = await cmd.P4G_TCP_STATE_TOTAL(transpor, m_id, p_id, cg_id).get()
    return rate.established


async def eth_rx_counter(transpor, m_id: int, p_id: int,) -> int:
    counter = await cmd.P4_ETH_RX_COUNTERS(transpor, m_id, p_id).get()
    return counter.packet_count


async def established_tcp_rate(transpor, m_id: int, p_id: int, cg_id: int) -> int:
    rate = await cmd.P4G_TCP_STATE_RATE(transpor, m_id, p_id, cg_id).get()
    return rate.established


async def established_udp_total(transpor, m_id: int, p_id: int, cg_id: int) -> int:
    rate = await cmd.P4G_UDP_STATE_TOTAL(transpor, m_id, p_id, cg_id).get()
    return rate.opened