################################################################
#
#                   L1 BIT RATE
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port for TX and another one for RX
# 3. Create a simple stream on TX port with 100% rate
# 4. Start traffic on TX port
# 5. Read RX and TX L2 traffic statistics
# 6. Calculate L1 traffic rate based on L2 statistics
# 7. Stop traffic
# 
# As to traffic rate statistics, you can only get L2 statistics 
# from the commands, including bits per second (bps) and frames per second (fps). 
# Use the following equation to calculate L1 bits per second.
# 
# * On TX side: ``l1_bit_per_sec = l2_fps * (interframe_gap + frame_size) * 8``
# * On RX side: ``l1_bit_per_sec = l2_fps * interframe_gap * 8 + l2_bit_per_sec``
# 
# > Note: The **inter-frame gap on both TX and RX sides must be the same**, 
# otherwise the calculated L1 bps values will be different.
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import ipaddress
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "XOA"
TX_PORT = "0/0"
RX_PORT = "0/1"

async def l1_bit_rate(chassis: str, username: str, tx_port_str: str, rx_port_str: str):

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        # Access module index 0 on the tester
        _mid_tx = int(tx_port_str.split("/")[0])
        _pid_tx = int(tx_port_str.split("/")[1])
        _mid_rx = int(rx_port_str.split("/")[0])
        _pid_rx = int(rx_port_str.split("/")[1])
        tx_module = tester.modules.obtain(_mid_tx)
        rx_module = tester.modules.obtain(_mid_rx)

        if isinstance(tx_module, modules.ModuleChimera):
            return None
        if isinstance(rx_module, modules.ModuleChimera):
            return None

        # Get the port object on module
        tx_port = tx_module.ports.obtain(_pid_tx)
        rx_port = rx_module.ports.obtain(_pid_rx)

        await mgmt.reserve_port(tx_port)
        await mgmt.reset_port(tx_port)
        await mgmt.reserve_port(rx_port)
        await mgmt.reset_port(rx_port)

        await asyncio.sleep(5)

        # Configure TX Port
        await utils.apply(
            tx_port.comment.set(comment="my tx port"),
            tx_port.interframe_gap.set(min_byte_count=20),
            tx_port.loop_back.set(mode=enums.LoopbackMode.NONE),
        )

        # Create a stream on the tx port
        # Stream index is automatically assigned
        stream = await tx_port.streams.create()
        stream_index = stream.idx
        logging.info(f"TX stream index: {stream_index}")

        # Simple batch configure the stream on the TX port
        await utils.apply(
            stream.tpld_id.set(test_payload_identifier=stream_index),
            stream.enable.set_on(),
            stream.comment.set(comment="my stream"),
            stream.rate.fraction.set(1_000_000),
            stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000)
        )
        
        # Configure RX Port
        await utils.apply(
            rx_port.comment.set(comment="my rx port"),
            rx_port.interframe_gap.set(min_byte_count=20),
            tx_port.loop_back.set(mode=enums.LoopbackMode.NONE),
        )

        # Batch clear statistics
        await asyncio.gather(
            tx_port.statistics.tx.clear.set(),
            tx_port.statistics.rx.clear.set()
        )
        
        # Start traffic on the TX port
        await tx_port.traffic.state.set_start()

        await asyncio.sleep(1)

        #################################################
        #         TX Port Traffic Rate Statistics       #
        #################################################

        resp = await tx_port.interframe_gap.get()
        tx_ifg = resp.min_byte_count
        logging.info(f"TX port inter-frame gap: {tx_ifg} bytes")

        resp = await stream.packet.length.get()
        tx_frame_size = resp.min_val
        logging.info(f"TX port frame size: {tx_frame_size} bytes")

        resp = await rx_port.interframe_gap.get()
        rx_ifg = resp.min_byte_count
        logging.info(f"RX port inter-frame gap: {rx_ifg} bytes")

        for i in range(10):
            # Query port-level traffic statistics
            resp1, resp2 = await asyncio.gather(
                tx_port.statistics.tx.total.get(),
                rx_port.statistics.rx.total.get()
            )
            # resp = await tx_port.statistics.tx.total.get()

            tx_bps_l2 = resp1.bit_count_last_sec
            tx_fps = resp1.packet_count_last_sec
            tx_bps_l1 = tx_fps*(tx_ifg+tx_frame_size)*8

            logging.info("*"*(i+1))
            logging.info(f"TX bits per second (L1): {tx_bps_l1} bps")
            logging.info(f"TX bits per second (L2): {tx_bps_l2} bps")
            logging.info(f"TX frames per second: {tx_fps} fps")

            # resp = await rx_port.statistics.rx.total.get()
            
            rx_bps_l2 = resp2.bit_count_last_sec
            rx_fps = resp2.packet_count_last_sec
            rx_bps_l1 = rx_fps*rx_ifg*8 + rx_bps_l2

            logging.info(f"RX bits per second (L1): {rx_bps_l1} bps")
            logging.info(f"RX bits per second (L2): {rx_bps_l2} bps")
            logging.info(f"RX frames per second: {rx_fps} fps")

            await asyncio.sleep(1)

        # Stop traffic on the TX port
        await tx_port.traffic.state.set_stop()

        #################################################
        #                  Release                      #
        #################################################
        # Release the ports
        await tx_port.reservation.set_release()
        await rx_port.reservation.set_release()

async def main():
    stop_event = asyncio.Event()
    try:
        await l1_bit_rate(
            chassis=CHASSIS_IP,
            username=USERNAME,
            tx_port_str=TX_PORT,
            rx_port_str=RX_PORT
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
