################################################################
#
#        config_control_collect.py
#
# author: leonard.yu@teledyne.com
################################################################

import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver.hlfuncs import mgmt, cli
import logging
import csv
import time
import os
import json

# *************************************************************************************
# function: get_module_and_port_objs
# *************************************************************************************
def get_module_and_port_objs(port_str: str, chassis_obj: testers.L23Tester):
    """Get module and port objects from chassis.

    :param port_str: Port string in the format 'module/port'
    :type port_str: str
    :param chassis_obj: Chassis object
    :type chassis_obj: testers.L23Tester
    """
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = chassis_obj.modules.obtain(_mid)
    if isinstance(module_obj, modules.E100ChimeraModule):
        logging.error("This example is not supported by Chimera Module")
        return None, None
    port_obj = module_obj.ports.obtain(_pid)
    return module_obj, port_obj


# *************************************************************************************
# class: XenaConfigControlCollect
# description: This class provides an automated framework to collect traffic statistics 
# from multiple port pairs and save the statistics into a CSV file 
# and histograms into separate CSV files.
# *************************************************************************************
class XenaConfigControlCollect:
    """This class provides an automated framework to collect traffic statistics from multiple port pairs and save the statistics into a CSV file and histograms into separate CSV files.
    """
    def __init__(self, stop_event: asyncio.Event):
        self.config_file = ""
        self.chassis: str = "0.0.0.0"
        self.username: str = "xoa"
        self.password: str = "xena"
        self.tcp_port: int = 22606
        self.debug_logging: bool = False
        self.port_pairs: list[dict[str, str]] = []
        self.xpc_files: list[dict[str, str]] = []
        self.duration: int = 60
        self.delay_after_reset: int = 5
        self.waiting_time: int = 30
        self.delay_to_query: int = 5
        self.resultdir_prefix: str = "results"
        self.stop_event: asyncio.Event = stop_event
        self.tx_port_obj_set = set()
        self.rx_port_obj_set = set()
        self.stream_struct_list = []

    def load_config(self, config_file: str = "config.json"):
        self.config_file = os.path.join(os.path.dirname(__file__), config_file)
        with open(self.config_file) as f:
            config = json.load(f)
            self.chassis = config.get("chassis", self.chassis)
            self.username = config.get("username", self.username)
            self.password = config.get("password", self.password)
            self.tcp_port = config.get("tcp_port", self.tcp_port)
            self.debug_logging = config.get("debug_logging", self.debug_logging)
            self.port_pairs = config.get("port_pairs", self.port_pairs)
            self.xpc_files = config.get("xpc_files", self.xpc_files)
            self.duration = config.get("duration", self.duration)
            self.delay_after_reset = config.get("delay_after_reset", self.delay_after_reset)
            self.waiting_time = config.get("waiting_time", self.waiting_time)
            self.delay_to_query = config.get("delay_to_query", self.delay_to_query)
            self.resultdir_prefix = config.get("resultdir_prefix", self.resultdir_prefix)

        self.config_file_dir = os.path.join(os.path.dirname(__file__), "xpc_files")
        self.logfile_creation_time = time.strftime("%Y%m%d_%H%M%S")
        self.histogram_date = time.strftime("%m_%d_%Y")
        self.result_dir = os.path.join(os.path.dirname(__file__), f"{self.resultdir_prefix}_{self.logfile_creation_time}")
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

        self.logfile_path = os.path.join(self.result_dir, f"log_{self.logfile_creation_time}.log")
        self.statsfile_path = os.path.join(self.result_dir, f"statistics_{self.logfile_creation_time}.csv")

        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename=self.logfile_path, mode="a+"),
                logging.StreamHandler()]
            )
        
        logging.info(f"===============================================")
        logging.info(f"===============================================")
        logging.info(f"Configuration loaded from {self.config_file}")
        logging.info(f"Chassis: {self.chassis}, Username: {self.username}, TCP Port: {self.tcp_port}")
        logging.info(f"Port Pairs (Tx/Rx): {self.port_pairs}")
        logging.info(f"Port Config Files: {self.xpc_files}")
        logging.info(f"Test Duration: {self.duration} seconds")
        logging.info(f"Delay After Reset: {self.delay_after_reset} seconds")
        logging.info(f"Waiting Time Before Start Traffic: {self.waiting_time} seconds")
        logging.info(f"Delay Before Query Statistics: {self.delay_to_query} seconds")
        logging.info(f"===============================================")
        logging.info(f"===============================================")

        
    async def start(self):
        # Establish connection to a Xena tester using Python context manager
        # The connection will be automatically terminated when it is out of the block
        async with testers.L23Tester(host=self.chassis, username=self.username, password=self.password, port=self.tcp_port, enable_logging=self.debug_logging) as chassis_obj:
            logging.info(f"===================================")
            logging.info(f"{'Connect to chassis:':<20}{self.chassis}")
            logging.info(f"{'Username:':<20}{self.username}")

            #################################################
            #                  Port Config                  #
            #################################################
            # Load port configurations if any
            if len(self.xpc_files) > 0:
                logging.info(f"Loading port configurations from .xpc files")
                for pp in self.xpc_files:
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
                        await cli.port_config_from_file(port=port_obj, path=os.path.join(self.config_file_dir, xpc_file))
                        logging.info(f"Port {port_str} configuration loaded")
                        await asyncio.sleep(1)  # wait for a while to let the module/port apply the configuration
            else:
                logging.info(f"No .xpc file provided. Skip loading port configuration.")

            await asyncio.sleep(self.delay_after_reset)  # wait for a while to let the module/port apply the configuration

            #################################################
            #                  Port Config Sync             #
            #################################################
            # stream data structure list to save stream related objects and info
            for port_pair in self.port_pairs:
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
                self.tx_port_obj_set.add(tx_port_obj)
                self.rx_port_obj_set.add(rx_port_obj)

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
                for tx_stream_obj in tx_port_obj.streams:
                    tx_stream_index = tx_stream_obj.idx
                    resp = await tx_stream_obj.tpld_id.get()
                    tx_stream_tpld_id = resp.test_payload_identifier
                    resp = await tx_stream_obj.comment.get()
                    tx_stream_comment = resp.comment
                    logging.info((f"Tx Port {tx_port_str}: Stream {tx_stream_index} with TPLD ID {tx_stream_tpld_id}"))

                    # resp = await rx_stream_obj.comment.get()
                    # rx_stream_comment = resp.comment
                    # logging.info((f"Rx Port {rx_port_str}: Stream {tx_stream_index} with TPLD ID {tx_stream_tpld_id}"))

                    # read the tx/rx port IFG for L2-to-L1 rate conversion
                    resp = await tx_port_obj.interframe_gap.get()
                    tx_port_ifg = resp.min_byte_count
                    resp = await rx_port_obj.interframe_gap.get()
                    rx_port_ifg = resp.min_byte_count

                    # read the tx stream packet size
                    resp = await tx_stream_obj.packet.length.get()
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
                    self.stream_struct_list.append(
                        {
                            "tx_module_obj": tx_module_obj,
                            "tx_port_str": tx_port_str,
                            "tx_port_obj": tx_port_obj,
                            "tx_port_ifg": tx_port_ifg,
                            "stream_index": tx_stream_index,
                            "stream_tpld_id": tx_stream_tpld_id,
                            "stream_comment": tx_stream_comment,
                            # "rx_stream_comment": rx_stream_comment,
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
            logging.info(f"Waiting for {self.waiting_time} seconds before starting traffic...")
            await asyncio.sleep(self.waiting_time)

            logging.info(f"Starting traffic on all Tx ports")
            # clear port statistics on all involved ports
            for port_obj in self.tx_port_obj_set.union(self.rx_port_obj_set):
                await port_obj.statistics.tx.clear.set()
                await port_obj.statistics.rx.clear.set()
                logging.info(f"Cleared statistics on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")

                # enable al streams on the tx port
                for tx_stream_obj in port_obj.streams:
                    await tx_stream_obj.enable.set_on()
                logging.info(f"Enabled all streams on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
            
            # start histogram on all involved ports
            for rx_port_obj in self.rx_port_obj_set:
                for histogram_obj in rx_port_obj.datasets:
                    await histogram_obj.enable.set_on()
                logging.info(f"Started histograms on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")

            # start traffic on all tx ports
            for tx_port_obj in self.tx_port_obj_set:
                await tx_port_obj.traffic.state.set_start()
                logging.info(f"Started traffic on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}")
            

            #################################################
            #                  Statistics                   #
            #################################################
            # Each port can have two roles, Tx and Rx. 
            # On the Tx role, we use the stream index to identify the stream and collect statistics.
            # On the Rx role, we use the TPLD ID to identify the stream and collect statistics.
            await asyncio.sleep(self.delay_to_query)  # wait for a while before querying statistics
            logging.info(f"Collecting statistics for {self.duration} seconds")
            
            # Prepare the CSV file
            field = ["Timestamp", "SrcPort", "SID", "DestPort", "TID", "StreamDescription", "TxL1Bps", "TxBps", "TxBytesps", "TxFps", "TxBytes", "TxFrames", "RxL1Bps", "RxBps", "RxBytesps", "RxFps", "RxBytes", "RxFrames", "RxOversizePackets", "RxUndersizePackets", "RxJabberPackets", "RxFcsErrors", "RxLossPcks", "RxMisErr", "RxPldErr", "LatencyCurr", "LatencyCurrMin", "LatencyCurrMax", "LatencyAvg", "LatencyMin", "LatencyMax", "JitterCurr", "JitterCurrMin", "JitterCurrMax", "JitterAvg", "JitterMin", "JitterMax"]

            # Collect statistics every second
            with open(self.statsfile_path, 'w+', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(field)

                for tick in range(self.duration+5):
                    if tick >= self.duration:
                        # stop traffic after the duration
                        logging.info(f"Stopping traffic on all Tx ports")
                        for tx_port_obj in self.tx_port_obj_set:
                            await tx_port_obj.traffic.state.set_stop()
                            logging.info(f"Stopped traffic on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}")
                        # stop histogram on all involved ports
                        for rx_port_obj in self.rx_port_obj_set:
                            for histogram_obj in rx_port_obj.datasets:
                                await histogram_obj.enable.set_off()
                            logging.info(f"Stopped histograms on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")

                    # The time string for this batch of statistics
                    batch_time = time.strftime("%Y%m%d-%H%M%S")

                    # First construct commands to query all streams on all ports
                    commands =[]
                    for stream_struct in self.stream_struct_list:
                        tx_port_obj: ports.GenericL23Port = stream_struct["tx_port_obj"]
                        rx_port_obj: ports.GenericL23Port = stream_struct["rx_port_obj"]
                        my_stream = tx_port_obj.streams.obtain(stream_struct["stream_index"])
                        tx_port_str: str = stream_struct["tx_port_str"]
                        rx_port_str: str = stream_struct["rx_port_str"]
                        tx_stream_tpld_id: int = stream_struct["stream_tpld_id"]
                        tx_stream_comment: str = stream_struct["stream_comment"]
                        # rx_stream_comment: str = stream_struct["rx_stream_comment"]
                        rx_port_ifg: int = stream_struct["rx_port_ifg"]

                        # Query stream TxBps, TxFps, TxBytes, TxFrames
                        commands.append(tx_port_obj.statistics.tx.obtain_from_stream(my_stream).get())
                        # Query stream RxBps, RxBytesps, RxFps, RxBytes, RxFrames
                        commands.append(rx_port_obj.statistics.rx.access_tpld(tx_stream_tpld_id).traffic_ext.get())
                        # Query stream LatencyCurr, LatencyCurrMin, LatencyCurrMax, LatencyAvg, LatencyMin, LatencyMax
                        commands.append(rx_port_obj.statistics.rx.access_tpld(tx_stream_tpld_id).latency.get())    
                        # Query stream JitterCurr, JitterCurrMin, JitterCurrMax, JitterAvg, JitterMin, JitterMax
                        commands.append(rx_port_obj.statistics.rx.access_tpld(tx_stream_tpld_id).jitter.get())
                        # Query stream RxLossPcks, RxMisErr, RxPldErr
                        commands.append(rx_port_obj.statistics.rx.access_tpld(tx_stream_tpld_id).errors.get())
                        # Query port-level RxFcsErrors, RxOversizePackets, RxUndersizePackets, RxJabberPackets
                        commands.append(rx_port_obj.statistics.rx.total_ext.get())

                    # Send the commands and get the responses
                    responses = await asyncio.gather(*commands)
                    stream_stat_list = []
                    
                    for i in range(0, len(responses), 6):
                        stream_stat_list.append(responses[i:i + 6])
                    for stream_stat, stream_struct in zip(stream_stat_list, self.stream_struct_list):
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

                        rx_oversize = stream_stat[5].oversize_count if stream_stat[5].oversize_count >= 0 else "N/A"
                        rx_undersize = stream_stat[5].undersize_count if stream_stat[5].undersize_count >= 0 else "N/A"
                        rx_jabber = stream_stat[5].jabber_count if stream_stat[5].jabber_count >= 0 else "N/A"
                        rx_fcs_errors = stream_stat[5].fcs_error_count if stream_stat[5].fcs_error_count >= 0 else "N/A"
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

                        rx_latency_curr = stream_stat[2].avg_last_sec if (stream_stat[2].avg_last_sec != -1 or stream_stat[2].avg_last_sec != -2147483648) else "N/A"
                        rx_latency_curr_min = stream_stat[2].min_last_sec if (stream_stat[2].min_last_sec != -1 or stream_stat[2].min_last_sec != -2147483648) else "N/A"
                        rx_latency_curr_max = stream_stat[2].max_last_sec if (stream_stat[2].max_last_sec != -1 or stream_stat[2].max_last_sec != -2147483648) else "N/A"
                        rx_latency_avg = stream_stat[2].avg_val if (stream_stat[2].avg_val != -1 or stream_stat[2].avg_val != -2147483648) else "N/A"
                        rx_latency_min = stream_stat[2].min_val if (stream_stat[2].min_val != -1 or stream_stat[2].min_val != -2147483648) else "N/A"
                        rx_latency_max = stream_stat[2].max_val if (stream_stat[2].max_val != -1 or stream_stat[2].max_val != -2147483648) else "N/A"
                        csv_row_data.append(rx_latency_curr) # LatencyCurr
                        csv_row_data.append(rx_latency_curr_min) # LatencyCurrMin
                        csv_row_data.append(rx_latency_curr_max) # LatencyCurrMax
                        csv_row_data.append(rx_latency_avg) # LatencyAvg
                        csv_row_data.append(rx_latency_min) # LatencyMin
                        csv_row_data.append(rx_latency_max) # LatencyMax

                        rx_jitter_curr = stream_stat[3].avg_last_sec if (stream_stat[3].avg_last_sec != -1 or stream_stat[3].avg_last_sec != -2147483648) else "N/A"
                        rx_jitter_curr_min = stream_stat[3].min_last_sec if (stream_stat[3].min_last_sec != -1 or stream_stat[3].min_last_sec != -2147483648) else "N/A"
                        rx_jitter_curr_max = stream_stat[3].max_last_sec if (stream_stat[3].max_last_sec != -1 or stream_stat[3].max_last_sec != -2147483648) else "N/A"
                        rx_jitter_avg = stream_stat[3].avg_val if stream_stat[3].avg_val != -1 else "N/A"
                        rx_jitter_min = stream_stat[3].min_val if stream_stat[3].min_val != -1 else "N/A"
                        rx_jitter_max = stream_stat[3].max_val if stream_stat[3].max_val != -1 else "N/A"
                        csv_row_data.append(rx_jitter_curr) # JitterCurr
                        csv_row_data.append(rx_jitter_curr_min) # JitterCurrMin
                        csv_row_data.append(rx_jitter_curr_max) # JitterCurrMax
                        csv_row_data.append(rx_jitter_avg) # JitterAvg
                        csv_row_data.append(rx_jitter_min) # JitterMin
                        csv_row_data.append(rx_jitter_max) # JitterMax

                        writer.writerow(csv_row_data)

                    await asyncio.sleep(1)  # wait for 1 second before the next query
                    logging.info(f"Statistics collection iteration {tick+1} completed.")
            

            # Save histogram data to CSV files
            for stream_struct in self.stream_struct_list:
                tx_port_obj: ports.GenericL23Port = stream_struct["tx_port_obj"]
                rx_port_obj: ports.GenericL23Port = stream_struct["rx_port_obj"]

                stream_dscr = stream_struct["stream_comment"]

                for histogram_obj in rx_port_obj.datasets:

                    # Get port index
                    _port_str = f"P{tx_port_obj.kind.port_id}"

                    _title = ""
                    _type = ""
                    resp = await histogram_obj.source.get()
                    if resp.source_type == enums.SourceType.RX_LATENCY:
                        _title = "RX Latency Distribution (ns)"
                        _type = "Latency"
                    elif resp.source_type == enums.SourceType.RX_JITTER:
                        _title = "RX Jitter Distribution (ns)"
                        _type = "Jitter"
                    else:
                        _title = "RX Distribution"
                        _type = "Other"

                    _tpld_id = resp.identity

                    # Get X axis data
                    resp = await histogram_obj.range.get()
                    _start = resp.start
                    _step = resp.step
                    _bucket_count = resp.bucket_count
                    csv_x_data = []
                    csv_x_data.append("X (start):")
                    csv_x_data.append(-1)
                    for i in range(_bucket_count-1):
                        csv_x_data.append(_start + i * _step)
                    csv_x_data[-1] = csv_x_data[-1] + 2*_step

                    # Get Y axis data
                    csv_y_data = []
                    csv_y_data.append("Y (packets):")
                    resp = await histogram_obj.samples.get()
                    csv_y_data.extend(resp.packet_counts)
                    # extend the Y axis data to match the X axis data length with 0s
                    csv_y_data.extend([0] * (_bucket_count - len(resp.packet_counts)))

                    histogram_path = os.path.join(self.result_dir, f"{_port_str}-Histogram {_type} data {self.histogram_date} {stream_dscr}.csv")
                    with open(histogram_path, 'w+', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([_title])
                        writer.writerow(csv_x_data)
                        writer.writerow(csv_y_data)

                    logging.info(f"Port {_port_str}: Histogram {histogram_obj.idx} ('{_title}' TPLD ID {_tpld_id}) saved to {histogram_path}")

    async def stop(self):
        return

# *************************************************************************************
# main function
# *************************************************************************************
async def main():
    stop_event = asyncio.Event()
    try:
        ccc = XenaConfigControlCollect(stop_event)
        ccc.load_config(config_file="config2.json")
        await ccc.start()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping...")
    finally:
        await ccc.stop()
        print("Exiting...")

if __name__ == "__main__":
    asyncio.run(main())