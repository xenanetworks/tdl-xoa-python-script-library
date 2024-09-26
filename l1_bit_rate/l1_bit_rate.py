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
CHASSIS_IP = "10.165.136.70"
USERNAME = "XOA"
TX_PORT = "0/4"
RX_PORT = "0/5"
FIXED_PACKET_SIZE_BYTE = 100

async def l1_bit_rate(chassis: str, username: str, tx_port_str: str, rx_port_str: str, fixed_packet_size_byte :int):

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
            stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=fixed_packet_size_byte, max_val=fixed_packet_size_byte)
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
        #     TX & RX Port Traffic Rate Statistics      #
        #################################################

        # get TX port IFG_min
        resp = await tx_port.interframe_gap.get()
        tx_ifg = resp.min_byte_count
        logging.info(f"{tx_port_str} TX port inter-frame gap: {tx_ifg} bytes")

        # get RX port IFG_min
        resp = await rx_port.interframe_gap.get()
        rx_ifg = resp.min_byte_count
        logging.info(f"{rx_port_str} RX port inter-frame gap: {rx_ifg} bytes")

        # get stream packet size
        resp = await stream.packet.length.get()
        tx_frame_size = resp.min_val
        logging.info(f"{tx_port_str} TX port frame size: {tx_frame_size} bytes")

        # calculate the TX effective port speed from nominal speed and reduction ppm
        resp = await tx_port.speed.current.get()
        tx_port_nominal_speed_Mbps = resp.port_speed
        resp = await tx_port.speed.reduction.get()
        tx_port_speed_reduction_ppm = resp.ppm
        tx_port_effective_speed = tx_port_nominal_speed_Mbps*(1 - tx_port_speed_reduction_ppm/1_000_000)*1_000_000
        logging.info(f"{tx_port_str} TX port effective speed: {tx_port_effective_speed/1_000_000_000} Gbps")

        # calculate the RX effective port speed from nominal speed and reduction ppm
        resp = await rx_port.speed.current.get()
        rx_port_nominal_speed_Mbps = resp.port_speed
        resp = await rx_port.speed.reduction.get()
        rx_port_speed_reduction_ppm = resp.ppm
        rx_port_effective_speed = rx_port_nominal_speed_Mbps*(1 - rx_port_speed_reduction_ppm/1_000_000)*1_000_000
        logging.info(f"{rx_port_str} RX port effective speed: {rx_port_effective_speed/1_000_000_000} Gbps")


        for i in range(10):
            # Query port-level traffic statistics
            tx_resp, rx_resp = await asyncio.gather(
                tx_port.statistics.tx.total.get(),
                rx_port.statistics.rx.total.get()
            )

            tx_bps_l2 = tx_resp.bit_count_last_sec
            tx_fps = tx_resp.packet_count_last_sec
            tx_byteps = tx_resp.packet_count_last_sec*fixed_packet_size_byte
            tx_bps_l1 = tx_fps*(tx_ifg+tx_frame_size)*8
            tx_rate_percent = tx_bps_l1/tx_port_effective_speed

            rx_bps_l2 = rx_resp.bit_count_last_sec
            rx_byteps = rx_resp.packet_count_last_sec*fixed_packet_size_byte
            rx_fps = rx_resp.packet_count_last_sec
            rx_bps_l1 = rx_fps*rx_ifg*8 + rx_bps_l2
            rx_rate_percent = rx_bps_l1/rx_port_effective_speed

            logging.info(f"{i}")
            logging.info(f"{tx_port_str} TX rate percentage (%) : {tx_rate_percent*100}%")
            logging.info(f"{tx_port_str} TX bits per second (L1): {tx_bps_l1} bps")
            logging.info(f"{tx_port_str} TX bits per second (L1): {tx_bps_l1} bps")
            logging.info(f"{tx_port_str} TX bits per second (L2): {tx_bps_l2} bps")
            logging.info(f"{tx_port_str} TX bytes per second    : {tx_byteps} bytes/s")
            logging.info(f"{tx_port_str} TX frames per second   : {tx_fps} pps")
            logging.info(f"{tx_port_str} RX rate percentage (%) : {rx_rate_percent*100}%")
            logging.info(f"{rx_port_str} RX bits per second (L1): {rx_bps_l1} bits/s")
            logging.info(f"{rx_port_str} RX bits per second (L2): {rx_bps_l2} bits/s")
            logging.info(f"{rx_port_str} RX bytes per second    : {rx_byteps} bytes/s")
            logging.info(f"{rx_port_str} RX frames per second   : {rx_fps} pps")

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
            rx_port_str=RX_PORT,
            fixed_packet_size_byte=FIXED_PACKET_SIZE_BYTE
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
