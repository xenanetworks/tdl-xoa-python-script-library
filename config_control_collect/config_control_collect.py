################################################################
#
#        Collecting Statistics and Save Into CSV File
#
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, headers, cli
from xoa_driver.misc import Hex
import logging
import csv
import time
import os

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "192.168.126.194"		# Chassis IP address is used to establish connection.
USERNAME = "Xena"	        # Username lets others know who is using the chassis/module/port.
PASSWORD = "xena"					# Chassis log-in password. Default is "xena".
TCP_PORT = 22606					# Chassis TCP port number for connection establishment. Default is 22606.
ENABLE_COMM_LOGGING = False			# Enable low-level communication trace logging (the communication between the client and the chassis).
RESULTDIR_PREFIX = "results"        # The prefix of the statistics log file name. The current timestamp will be appended to the prefix.

DURATION = 30                       # Duration of the statistics collection in seconds.

XPCONF_FILES = [
    {"1/0": "ACY-1-0.xpc"},
    {"1/1": "ACY-1-1.xpc"},
    {"1/3": "ACY-1-3.xpc"},
    {"1/4": "ACY-1-4.xpc"},
]                                   # The .xconf file path to load the configuration. 
                                    # If it is an empty string, no configuration will be loaded.

PORT_PAIRS = [
    {"tx": "1/0", "rx": "1/1"},
    {"tx": "1/1", "rx": "1/0"},
    {"tx": "1/3", "rx": "1/4"},
    {"tx": "1/4", "rx": "1/3"},
]									# Describe your Tx-Rx pairs here. The port indices are in the format <module_index>/<port_index>. 
									# Note that bidirectional traffic bewteen two ports are considered as two Tx-Rx pairs.

DELAY_AFTER_RESET = 5               # Delay in seconds after resetting a module/port to wait for it to be ready for next operation.

#---------------------------
# Help functions
#---------------------------
def get_module_and_port_objs(port_str: str, chassis_obj: testers.L23Tester):
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = chassis_obj.modules.obtain(_mid)
    if isinstance(module_obj, modules.E100ChimeraModule):
        logging.error("This example is not supported by Chimera Module")
        return None, None
    port_obj = module_obj.ports.obtain(_pid)
    return module_obj, port_obj


#-----------------------------------------
# Load Port Config & Statistics Collection
#-----------------------------------------
async def config_control_collect(
        chassis: str, 
        username: str, 
        password: str = "xena", 
        tcp_port: int = 22606, 
        debug_logging: bool = False,
        port_pairs: list[dict[str, str]] = [],
        xpc_files: list[dict[str, str]] = [],
        duration = 60,
        delay_after_reset: int = 5,
        resultdir_prefix: str = "results"):
    
    config_file_dir = os.path.join(os.path.dirname(__file__), "xpc_files")
    logfile_creation_time = time.strftime("%Y%m%d_%H%M%S")
    result_dir = os.path.join(os.path.dirname(__file__), f"{resultdir_prefix}_{logfile_creation_time}")
    logfile_path = os.path.join(result_dir, f"log_{logfile_creation_time}.log")
    statsfile_path = os.path.join(result_dir, f"statistics_{logfile_creation_time}.csv")

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename=logfile_path, mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Xena tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password=password, port=tcp_port, enable_logging=debug_logging) as chassis_obj:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        #################################################
        #                  Port Config                  #
        #################################################
        # Load port configurations if any
        if len(xpc_files) > 0:
            logging.info(f"Loading port configurations from .xpc files")
            for pp in xpc_files:
                for port_str, xpc_file in pp.items():
                    if xpc_file == "":
                        continue
                    module_obj, port_obj = get_module_and_port_objs(port_str, chassis_obj)
                    if module_obj is None or port_obj is None:
                        logging.error(f"Failed to get module or port object for port {port_str}")
                        continue
                    logging.info(f"Loading port {port_str} configuration from {xpc_file}")
                    await mgmt.release_module(module=module_obj)
                    await mgmt.reserve_port(port=port_obj, force=True, reset=True)
                    await asyncio.sleep(1)  # wait for a while after resetting the port
                    await cli.port_config_from_file(port=port_obj, path=os.path.join(config_file_dir, xpc_file))
                    logging.info(f"Port {port_str} configuration loaded")
                    await asyncio.sleep(1)  # wait for a while to let the module/port apply the configuration
        else:
            logging.info(f"No .xpc file provided. Skip loading port configuration.")
        
        await asyncio.sleep(delay_after_reset)  # wait for a while to let the module/port apply the configuration

        #################################################
        #                  Port Config Sync             #
        #################################################
        # stream data structure list to save stream related objects and info
        tx_port_obj_set = set()
        rx_port_obj_set = set()
        stream_struct_list = []
        for port_pair in port_pairs:
            tx_port_str = port_pair["tx"]
            rx_port_str = port_pair["rx"]

            x, y = get_module_and_port_objs(tx_port_str, chassis_obj)
            if x is None or y is None:
                logging.error(f"Failed to get module or port object for Tx port {tx_port_str}")
                continue
            tx_module_obj, tx_port_obj = x, y
            x, y = get_module_and_port_objs(rx_port_str, chassis_obj)
            if x is None or y is None:
                logging.error(f"Failed to get module or port object for Rx port {rx_port_str}")
                continue
            rx_module_obj, rx_port_obj = x, y

            # Synchronize the streams, filters, and histogram (datasets) on ports from the chassis to the client side
            await tx_port_obj.streams.server_sync()
            await rx_port_obj.filters.server_sync()
            await tx_port_obj.datasets.server_sync()
            await rx_port_obj.datasets.server_sync()

            # Save the tx/rx port objects to a set to avoid duplicate processing
            tx_port_obj_set.add(tx_port_obj)
            rx_port_obj_set.add(rx_port_obj)

            logging.info(f"Tx Port {tx_port_str} --> Rx Port {rx_port_str} synced.")
            logging.info(f"  Tx Port {tx_port_str} has {len(tx_port_obj.streams)} streams.")
            # logging.info(f"  Rx Port {rx_port_str} has {len(rx_port_obj.filters)} filters.")
            # logging.info(f"  Tx Port {tx_port_str} has {len(tx_port_obj.datasets)} histograms.")
            logging.info(f"  Rx Port {rx_port_str} has {len(rx_port_obj.datasets)} histograms.")
            
            rx_port_filter_idx_list = []
            for filter_obj in rx_port_obj.filters:
                rx_port_filter_idx_list.append(filter_obj.idx)
            # logging.info((f"Rx Port {rx_port_str} Filter Indices: {rx_port_filter_idx_list}"))

            rx_port_histogram_idx_list = []
            for dataset_obj in rx_port_obj.datasets:
                rx_port_histogram_idx_list.append(dataset_obj.idx)
            logging.info((f"Rx Port {rx_port_str} Histogram Indices: {rx_port_histogram_idx_list}"))

            # read tx port imix config
            frame_sizes = []
            resp = await tx_port_obj.mix.lengths[0].get()
            frame_sizes.append(resp.frame_size)
            resp = await tx_port_obj.mix.lengths[1].get()
            frame_sizes.append(resp.frame_size)
            frame_sizes.extend([64, 70, 78, 92, 256, 496, 512, 570, 576, 594, 1438, 1518])
            resp = await tx_port_obj.mix.lengths[14].get()
            frame_sizes.append(resp.frame_size)
            resp = await tx_port_obj.mix.lengths[15].get()
            frame_sizes.append(resp.frame_size)

            weights = []
            resp = await tx_port_obj.mix.weights.get()
            weights.append(resp.weight_56_bytes)
            weights.append(resp.weight_60_bytes)
            weights.append(resp.weight_64_bytes)
            weights.append(resp.weight_70_bytes)
            weights.append(resp.weight_78_bytes)
            weights.append(resp.weight_92_bytes)
            weights.append(resp.weight_256_bytes)
            weights.append(resp.weight_496_bytes)
            weights.append(resp.weight_512_bytes)
            weights.append(resp.weight_570_bytes)
            weights.append(resp.weight_576_bytes)
            weights.append(resp.weight_594_bytes)
            weights.append(resp.weight_1438_bytes)
            weights.append(resp.weight_1518_bytes)
            weights.append(resp.weight_9216_bytes)
            weights.append(resp.weight_16360_bytes)

            # calculate average frame size
            avg_frame_size = 0
            for w, s in zip(weights, frame_sizes):
                avg_frame_size += w * s
            avg_frame_size = int(avg_frame_size / sum(weights))

            # query each stream on the tx port
            for stream_obj in tx_port_obj.streams:
                stream_index = stream_obj.idx
                resp = await stream_obj.tpld_id.get()
                stream_tpld_id = resp.test_payload_identifier
                resp = await stream_obj.comment.get()
                stream_comment = resp.comment
                logging.info((f"Tx Port {tx_port_str}: Stream {stream_index} with TPLD ID {stream_tpld_id}"))

                # read the tx/rx port IFG for L2-to-L1 rate conversion
                resp = await tx_port_obj.interframe_gap.get()
                tx_port_ifg = resp.min_byte_count
                resp = await rx_port_obj.interframe_gap.get()
                rx_port_ifg = resp.min_byte_count

                # read the tx stream packet size
                resp = await stream_obj.packet.length.get()
                resp.length_type
                resp.min_val
                resp.max_val
                if resp.length_type == enums.LengthType.FIXED:
                    pkt_size = resp.min_val
                elif resp.length_type == enums.LengthType.MIX:
                    pkt_size = avg_frame_size
                else:
                    pkt_size = int((resp.min_val + resp.max_val) / 2)

                # Create the data structure to save the stream related objects and info
                stream_struct_list.append(
                    {
                        "tx_module_obj": tx_module_obj,
                        "tx_port_str": tx_port_str,
                        "tx_port_obj": tx_port_obj,
                        "tx_port_ifg": tx_port_ifg,
                        "stream_index": stream_index,
                        "stream_tpld_id": stream_tpld_id,
                        "stream_comment": stream_comment,
                        "pkt_size": pkt_size,
                        "rx_module_obj": rx_module_obj,
                        "rx_port_str": rx_port_str,
                        "rx_port_obj": rx_port_obj,
                        "rx_port_ifg": rx_port_ifg,
                        "rx_port_filter_idx_list": rx_port_filter_idx_list,
                        "rx_port_histogram_idx_list": rx_port_histogram_idx_list,
                    }
                )

        #################################################
        #                  Start Traffic                #
        #################################################
        logging.info(f"Starting traffic on all Tx ports")
        # clear port statistics on all involved ports
        for port_obj in tx_port_obj_set.union(rx_port_obj_set):
            await port_obj.statistics.tx.clear.set()
            await port_obj.statistics.rx.clear.set()
            logging.info(f"Cleared statistics on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")

            # enable al streams on the tx port
            for stream_obj in port_obj.streams:
                await stream_obj.enable.set_on()
            logging.info(f"Enabled all streams on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
        
        # start histogram on all involved ports
        for rx_port_obj in rx_port_obj_set:
            for histogram_obj in rx_port_obj.datasets:
                await histogram_obj.enable.set_on()
            logging.info(f"Started histograms on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")

        # start traffic on all tx ports
        for tx_port_obj in tx_port_obj_set:
            await tx_port_obj.traffic.state.set_start()
            logging.info(f"Started traffic on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}")


        #################################################
        #                  Statistics                   #
        #################################################
        # Each port can have two roles, Tx and Rx. 
        # On the Tx role, we use the stream index to identify the stream and collect statistics.
        # On the Rx role, we use the TPLD ID to identify the stream and collect statistics.
        logging.info(f"Collecting statistics for {duration} seconds")
        
        # Prepare the CSV file
        field = ["Timestamp", "SrcPort", "SID", "DestPort", "TID", "StreamDescription", "TxL1Bps", "TxBps", "TxBytesps", "TxFps", "TxBytes", "TxFrames", "RxL1Bps", "RxBps", "RxBytesps", "RxFps", "RxBytes", "RxFrames", "RxOversizePackets", "RxUndersizePackets", "RxJabberPackets", "RxFcsErrors", "RxLossPcks", "RxMisErr", "RxPldErr", "LatencyCurr", "LatencyCurrMin", "LatencyCurrMax", "LatencyAvg", "LatencyMin", "LatencyMax", "JitterCurr", "JitterCurrMin", "JitterCurrMax", "JitterAvg", "JitterMin", "JitterMax"]

        with open(statsfile_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(field)

            # Every second, collect statistics from all streams on all ports
            for tick in range(duration+5):  # add a few seconds after the duration to collect any final statistics
                if tick >= duration:
                    # stop traffic after the duration
                    logging.info(f"Stopping traffic on all Tx ports")
                    for tx_port_obj in tx_port_obj_set:
                        await tx_port_obj.traffic.state.set_stop()
                        logging.info(f"Stopped traffic on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}")
                    # stop histogram on all involved ports
                    for rx_port_obj in rx_port_obj_set:
                        for histogram_obj in rx_port_obj.datasets:
                            await histogram_obj.enable.set_off()
                        logging.info(f"Stopped histograms on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                
                # The time string for this batch of statistics
                batch_time = time.strftime("%Y%m%d-%H%M%S")

                # First construct commands to query all streams on all ports
                commands =[]
                for stream_struct in stream_struct_list:
                    tx_port_obj: ports.GenericL23Port = stream_struct["tx_port_obj"]
                    rx_port_obj: ports.GenericL23Port = stream_struct["rx_port_obj"]
                    my_stream = tx_port_obj.streams.obtain(stream_struct["stream_index"])
                    tx_port_str: str = stream_struct["tx_port_str"]
                    rx_port_str: str = stream_struct["rx_port_str"]
                    stream_tpld_id: int = stream_struct["stream_tpld_id"]
                    stream_comment: str = stream_struct["stream_comment"]
                    rx_port_ifg: int = stream_struct["rx_port_ifg"]

                    # Query stream TxBps, TxFps, TxBytes, TxFrames
                    commands.append(tx_port_obj.statistics.tx.obtain_from_stream(my_stream).get())
                    # Query stream RxBps, RxBytesps, RxFps, RxBytes, RxFrames
                    commands.append(rx_port_obj.statistics.rx.access_tpld(stream_tpld_id).traffic_ext.get())
                    # Query stream LatencyCurr, LatencyCurrMin, LatencyCurrMax, LatencyAvg, LatencyMin, LatencyMax
                    commands.append(rx_port_obj.statistics.rx.access_tpld(stream_tpld_id).latency.get())    
                    # Query stream JitterCurr, JitterCurrMin, JitterCurrMax, JitterAvg, JitterMin, JitterMax
                    commands.append(rx_port_obj.statistics.rx.access_tpld(stream_tpld_id).jitter.get())
                    # Query stream RxLossPcks, RxMisErr, RxPldErr
                    commands.append(rx_port_obj.statistics.rx.access_tpld(stream_tpld_id).errors.get())
                    # Query port-level RxFcsErrors, RxOversizePackets, RxUndersizePackets, RxJabberPackets
                    commands.append(rx_port_obj.statistics.rx.total_ext.get())

                # Send the commands and get the responses
                responses = await asyncio.gather(*commands)
                stream_stat_list = []
                
                for i in range(0, len(responses), 6):
                    stream_stat_list.append(responses[i:i + 6])
                for stream_stat, stream_struct in zip(stream_stat_list, stream_struct_list):
                    csv_row_data = []
                    tx_port_ifg = stream_struct["tx_port_ifg"]
                    rx_port_ifg = stream_struct["rx_port_ifg"]
                    pkt_size = stream_struct["pkt_size"]
                    csv_row_data.append(batch_time) # Timestamp
                    _tx_port_str = f"P-{stream_struct['tx_port_str'].replace('/', '-')}"
                    csv_row_data.append(_tx_port_str) # SrcPort
                    csv_row_data.append(stream_struct["stream_index"]) # SID
                    _rx_port_str = f"P-{stream_struct['rx_port_str'].replace('/', '-')}"
                    csv_row_data.append(_rx_port_str) # DestPort
                    csv_row_data.append(stream_struct["stream_tpld_id"]) # TID
                    csv_row_data.append(stream_struct["stream_comment"]) # StreamDescription

                    logging.info(f"timestamp: {batch_time}, tx_port_str: {_tx_port_str}, stream_index: {stream_struct['stream_index']}, rx_port_str: {_rx_port_str}, stream_tpld_id: {stream_struct['stream_tpld_id']}, stream_comment: {stream_struct['stream_comment']}")

                    tx_bps = stream_stat[0].bit_count_last_sec
                    tx_fps = stream_stat[0].packet_count_last_sec
                    tx_bytes = stream_stat[0].byte_count_since_cleared
                    tx_frames = stream_stat[0].packet_count_since_cleared
                    tx_l1_bps = tx_fps * (tx_port_ifg + pkt_size)*8
                    csv_row_data.append(tx_l1_bps) # TxL1Bps
                    csv_row_data.append(tx_bps) # TxBps
                    csv_row_data.append(int(tx_bps / 8)) # TxBytesps
                    csv_row_data.append(tx_fps) # TxFps
                    csv_row_data.append(tx_bytes) # TxBytes
                    csv_row_data.append(tx_frames) # TxFrames

                    rx_bps = stream_stat[1].bit_count_last_sec
                    rx_bytesps = stream_stat[1].byte_count_last_sec
                    rx_fps = stream_stat[1].packet_count_last_sec
                    rx_bytes = stream_stat[1].byte_count_since_cleared
                    rx_frames = stream_stat[1].packet_count_since_cleared
                    rx_l1_bps = rx_fps * (rx_port_ifg + pkt_size)*8
                    csv_row_data.append(rx_l1_bps) # RxL1Bps
                    csv_row_data.append(rx_bps) # RxBps
                    csv_row_data.append(rx_bytesps) # RxBytesps
                    csv_row_data.append(rx_fps) # RxFps
                    csv_row_data.append(rx_bytes) # RxBytes
                    csv_row_data.append(rx_frames) # RxFrames

                    rx_oversize = stream_stat[5].oversize_count
                    rx_undersize = stream_stat[5].undersize_count
                    rx_jabber = stream_stat[5].jabber_count
                    rx_fcs_errors = stream_stat[5].fcs_error_count
                    csv_row_data.append(rx_oversize) # RxOversizePackets
                    csv_row_data.append(rx_undersize) # RxUndersizePackets
                    csv_row_data.append(rx_jabber) # RxJabberPackets
                    csv_row_data.append(rx_fcs_errors) # RxFcsErrors

                    rx_loss = stream_stat[4].non_incre_seq_event_count
                    rx_misorder = stream_stat[4].swapped_seq_misorder_event_count
                    rx_payload_err = stream_stat[4].non_incre_payload_packet_count
                    csv_row_data.append(rx_loss) # RxLossPcks
                    csv_row_data.append(rx_misorder) # RxMisErr
                    csv_row_data.append(rx_payload_err) # RxPldErr

                    rx_latency_curr = stream_stat[2].avg_last_sec
                    rx_latency_curr_min = stream_stat[2].min_last_sec
                    rx_latency_curr_max = stream_stat[2].max_last_sec
                    rx_latency_avg = stream_stat[2].avg_val
                    rx_latency_min = stream_stat[2].min_val
                    rx_latency_max = stream_stat[2].max_val
                    csv_row_data.append(rx_latency_curr) # LatencyCurr
                    csv_row_data.append(rx_latency_curr_min) # LatencyCurrMin
                    csv_row_data.append(rx_latency_curr_max) # LatencyCurrMax
                    csv_row_data.append(rx_latency_avg) # LatencyAvg
                    csv_row_data.append(rx_latency_min) # LatencyMin
                    csv_row_data.append(rx_latency_max) # LatencyMax

                    rx_jitter_curr = stream_stat[3].avg_last_sec
                    rx_jitter_curr_min = stream_stat[3].min_last_sec
                    rx_jitter_curr_max = stream_stat[3].max_last_sec
                    rx_jitter_avg = stream_stat[3].avg_val
                    rx_jitter_min = stream_stat[3].min_val
                    rx_jitter_max = stream_stat[3].max_val
                    csv_row_data.append(rx_jitter_curr) # JitterCurr
                    csv_row_data.append(rx_jitter_curr_min) # JitterCurrMin
                    csv_row_data.append(rx_jitter_curr_max) # JitterCurrMax
                    csv_row_data.append(rx_jitter_avg) # JitterAvg
                    csv_row_data.append(rx_jitter_min) # JitterMin
                    csv_row_data.append(rx_jitter_max) # JitterMax

                    writer.writerow(csv_row_data)

                logging.info(f"Collected statistics (#{tick+1})")
                await asyncio.sleep(1)
        

        #################################################
        #      Histogram & Filter Traffic               #
        #################################################
        logging.info(f"Collecting Histogram and Filter statistics")
        for stream_struct in stream_struct_list:
            tx_port_obj: ports.GenericL23Port = stream_struct["tx_port_obj"]
            rx_port_obj: ports.GenericL23Port = stream_struct["rx_port_obj"]

            # for histogram in tx_port_obj.datasets:
            #     resp = await histogram.samples.get()
            #     resp.packet_counts
            #     logging.info(f"Tx Port {stream_struct['tx_port_str']}: Histogram {histogram.idx} Samples: {resp.packet_counts}")

            for histogram in rx_port_obj.datasets:
                resp = await histogram.samples.get()
                resp.packet_counts
                logging.info(f"Rx Port {stream_struct['rx_port_str']}: Histogram {histogram.idx} Samples: {resp.packet_counts}")

            for filter in rx_port_obj.filters:
                resp = await filter.comment.get()
                filter_description = resp.comment
                resp = await rx_port_obj.statistics.rx.obtain_filter_statistics_ext(filter.idx).get()
                filter_bps = resp.bit_count_last_sec
                filter_bytesps = resp.byte_count_last_sec
                filter_fps = resp.packet_count_last_sec
                filter_bytes = resp.byte_count_since_cleared
                filter_frames = resp.packet_count_since_cleared
                logging.info(f"Rx Port {stream_struct['rx_port_str']}: Filter {filter.idx}, '{filter_description}' Rx L2 Bits/s: {filter_bps} bps, Rx Bytes/s: {filter_bytesps} Bps, Rx Frames/s: {filter_fps} fps, Rx Bytes: {filter_bytes} bytes, Rx Frames: {filter_frames} frames")

        return


#---------------------------
# main
#---------------------------
async def main():
    stop_event = asyncio.Event()
    try:
        await config_control_collect(
            chassis=CHASSIS_IP,
            username=USERNAME,
            password=PASSWORD,
            tcp_port=TCP_PORT,
            debug_logging=ENABLE_COMM_LOGGING,
            port_pairs=PORT_PAIRS,
            xpc_files=XPCONF_FILES,
            duration=DURATION,
            delay_after_reset=DELAY_AFTER_RESET,
            resultdir_prefix=RESULTDIR_PREFIX
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
