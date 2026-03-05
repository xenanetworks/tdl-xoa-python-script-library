################################################################
#
#                   TRAFFIC & LIVE STATISTICS
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve port
# 3. Create two streams on the port
# 4. Start traffic
# 5. Collect live statistics
# 
################################################################

import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import Hex
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------

CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "xoa"
PORT1 = "3/0"
PORT2 = "3/1"

TRAFFIC_DURATION = 10 # seconds

#---------------------------
# statistics_background_task
#---------------------------
async def statistics_background_task(
        port1: ports.GenericL23Port, 
        port2: ports.GenericL23Port, 
        duration: int,
        stop_event: asyncio.Event
    ) -> None:

    # collect statistics
    logging.info(f"Collecting statistics..")

    count = 0

    while not stop_event.is_set():
        (p1_tx, p1_rx, p2_tx, p2_rx) = await asyncio.gather(
            port1.statistics.tx.obtain_from_stream(0).get(),
            port1.statistics.rx.access_tpld(1).traffic.get(),
            port2.statistics.tx.obtain_from_stream(0).get(),
            port2.statistics.rx.access_tpld(0).traffic.get(),
        )
        logging.info(f"#"*count)
        logging.info(f"Port 1")
        logging.info(f"  TX(tid=0).Byte_Count: {p1_tx.byte_count_since_cleared}")
        logging.info(f"  TX(tid=0).Packet_Count: {p1_tx.packet_count_since_cleared}")
        logging.info(f"  RX(tid=1).Byte_Count: {p1_rx.byte_count_since_cleared}")
        logging.info(f"  RX(tid=1).Packet_Count: {p1_rx.packet_count_since_cleared}")

        logging.info(f"Port 2")
        logging.info(f"  TX(tid=1).Byte_Count: {p2_tx.byte_count_since_cleared}")
        logging.info(f"  TX(tid=1).Packet_Count: {p2_tx.packet_count_since_cleared}")
        logging.info(f"  RX(tid=0).Byte_Count: {p2_rx.byte_count_since_cleared}")
        logging.info(f"  RX(tid=0).Packet_Count: {p2_rx.packet_count_since_cleared}")

        count+=1
        await asyncio.sleep(1.0)

        if count >= duration:
            stop_event.set()

#---------------------------
# final_statistic_fetcher
#---------------------------
async def final_statistic_fetcher(
        port1: ports.GenericL23Port, 
        port2: ports.GenericL23Port
    ) -> None:

    (p1_tx, p1_rx, p2_tx, p2_rx) = await asyncio.gather(
        port1.statistics.tx.obtain_from_stream(0).get(),
        port1.statistics.rx.access_tpld(1).traffic.get(),
        port2.statistics.tx.obtain_from_stream(0).get(),
        port2.statistics.rx.access_tpld(0).traffic.get(),
    )

    logging.info(f"Frame Loss (TX-RX)")
    logging.info(f"  Port 1->Port 2 (tid=0): {p1_tx.packet_count_since_cleared - p2_rx.packet_count_since_cleared}")
    logging.info(f"  Port 2->Port 1 (tid=1): {p2_tx.packet_count_since_cleared - p1_rx.packet_count_since_cleared}")


#---------------------------
# traffic_control
#---------------------------
async def traffic_control(
        chassis: str, 
        username: str, 
        port1_str: str, 
        port2_str: str, 
        duration: int, 
        stop_event: asyncio.Event
    ):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester instance and establish connection
    logging.info(f"===================================")
    logging.info(f"{'Connect to chassis:':<20}{chassis}")
    logging.info(f"{'Username:':<20}{username}")
    tester_obj = await testers.L23Tester(host=chassis, username=username)

    # access the port objects
    module_obj_1, module_obj_2 = await mgmt.obtain_modules_by_ids(tester_obj, [port1_str, port2_str])    
    port_obj_1, port_obj_2 = await mgmt.obtain_ports_by_ids(tester_obj, [port1_str, port2_str])

    # commands which used in this example are not applicable to Chimera Module
    if isinstance(port_obj_1, ports.E100ChimeraPort) or isinstance(port_obj_2, ports.E100ChimeraPort):
        logging.error("This script example is not applicable to Chimera Module.")
        return None

    await mgmt.release_modules(modules=[module_obj_1, module_obj_2], should_release_ports=False)
    await mgmt.reserve_ports(ports=[port_obj_1, port_obj_2], force=True, reset=True)

    await asyncio.sleep(5)

    # Create one stream on the port
    logging.info(f"Creating a stream on port {port1_str}")
    my_stream1 = await port_obj_1.streams.create()
    # Create one stream on the port
    logging.info(f"Creating a stream on port {port2_str}")
    my_stream2 = await port_obj_2.streams.create()

    logging.info(f"Configuring streams..")

    eth = headers.Ethernet()
    eth.dst_mac = "AA:AA:AA:AA:AA:AA"
    eth.src_mac = "BB:BB:BB:BB:BB:BB"
    eth.ethertype = headers.EtherType.VLAN
    vlan = headers.VLAN()
    vlan.id = 100
    header_data1 = f'{str(eth)}{str(vlan)}'

    eth = headers.Ethernet()
    eth.dst_mac = "BB:BB:BB:BB:BB:BB"
    eth.src_mac = "AA:AA:AA:AA:AA:AA"
    eth.ethertype = headers.EtherType.VLAN
    vlan = headers.VLAN()
    vlan.id = 100
    header_data2 = f'{str(eth)}{str(vlan)}'

    await asyncio.gather(
        # Create the TPLD index of stream
        my_stream1.tpld_id.set(0),
        # Configure the packet size
        my_stream1.packet.length.set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000),
        my_stream1.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.VLAN
                ]),
        # Enable streams
        my_stream1.enable.set_on(),
        # Configure the stream rate
        # my_stream1.rate.fraction.set(stream_rate_ppm=100000),
        # my_stream1.rate.l2bps.set(l2_bps=1e9),
        my_stream1.rate.pps.set(stream_rate_pps=1000),
        # my_stream.packet.limit.set(packet_count=10000),
        my_stream1.packet.header.data.set(hex_data=Hex(header_data1)),

        my_stream2.tpld_id.set(1),
        # Configure the packet size
        my_stream2.packet.length.set(length_type=enums.LengthType.INCREMENTING, min_val=100, max_val=1000),
        my_stream2.packet.header.protocol.set(segments=[
                enums.ProtocolOption.ETHERNET,
                enums.ProtocolOption.VLAN
                ]),
        # Enable streams
        my_stream2.enable.set_on(),
        # Configure the stream rate
        # my_stream2.rate.fraction.set(stream_rate_ppm=100000),
        # my_stream2.rate.l2bps.set(l2_bps=1e9),
        my_stream2.rate.pps.set(stream_rate_pps=1000),
        # my_stream2.packet.limit.set(packet_count=10000),
        my_stream2.packet.header.data.set(hex_data=Hex(header_data2)),
    )
    await asyncio.sleep(1)

    # clear port statistics
    logging.info(f"Clearing statistics")
    await asyncio.gather(
        port_obj_1.statistics.tx.clear.set(),
        port_obj_1.statistics.rx.clear.set(),
        port_obj_2.statistics.tx.clear.set(),
        port_obj_2.statistics.rx.clear.set()
    )

    # start traffic on the ports
    logging.info(f"Starting traffic")
    await asyncio.gather(
        port_obj_1.traffic.state.set_start(),
        port_obj_2.traffic.state.set_start()
    )

    # let traffic runs for 10 seconds
    logging.info(f"Wait for {duration} seconds...")

    # spawn a Task to wait until 'event' is set.
    asyncio.create_task(statistics_background_task(port_obj_1, port_obj_2, duration, stop_event))
    await stop_event.wait()

    # stop traffic on the Tx port
    logging.info(f"Stopping traffic..")
    await asyncio.gather(
        port_obj_1.traffic.state.set_stop(),
        port_obj_2.traffic.state.set_stop()
    )
    await asyncio.sleep(2)

    # final statistics
    await final_statistic_fetcher(port_obj_1, port_obj_2)

    # free ports
    logging.info(f"Free ports")
    await mgmt.release_ports(ports=[port_obj_1, port_obj_2])

    # done
    logging.info(f"Test done")

async def main():
    stop_event = asyncio.Event()
    try:
        await traffic_control(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port1_str=PORT1,
            port2_str=PORT2,
            duration=TRAFFIC_DURATION,
            stop_event=stop_event
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())