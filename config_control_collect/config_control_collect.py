################################################################
#
#        config_control_collect.py
#
# author: leonard.yu@teledyne.com
# version: v8
################################################################

import asyncio
from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver.hlfuncs import mgmt, cli
import logging
import csv
from datetime import datetime
from time import sleep
import os
import json
import sys

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
        self.test_duration: int = 60
        self.delay_after_reset: int = 30
        self.pre_traffic_interval: int = 5
        self.post_traffic_interval: int = 5
        self.resultdir_prefix: str = "results"
        self.stop_event: asyncio.Event = stop_event
        self.tx_port_obj_set = set()
        self.rx_port_obj_set = set()
        self.stream_struct_list = []
        self.stats_data = []
        self.histogram_data = dict()
        self.chassis_obj: testers.L23Tester

    def load_test_config(self, config_file: str = "config.json"):
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
            self.test_duration = config.get("test_duration", self.test_duration)
            self.delay_after_reset = config.get("delay_after_reset", self.delay_after_reset)
            self.pre_traffic_interval = config.get("pre_traffic_interval", self.pre_traffic_interval)
            self.post_traffic_interval = config.get("post_traffic_interval", self.post_traffic_interval)
            self.resultdir_prefix = config.get("resultdir_prefix", self.resultdir_prefix)

        self.config_file_dir = os.path.join(os.path.dirname(__file__), "xpc_files")
        curr_time = datetime.now()
        self.logfile_creation_time = curr_time.strftime("%Y%m%d_%H%M%S")
        self.histogram_timestamp = curr_time.strftime("%m_%d_%Y")
        self.result_dir = os.path.join(os.path.dirname(__file__), f"{self.resultdir_prefix}_{self.logfile_creation_time}")
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

        self.log_path = os.path.join(self.result_dir, f"log_{self.logfile_creation_time}.log")

        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename=self.log_path, mode="a+"),
                logging.StreamHandler()]
            )
        
        logging.info(f"===============================================")
        logging.info(f"===============================================")
        logging.info(f"Configuration loaded from {self.config_file}")
        logging.info(f"Chassis: {self.chassis}, Username: {self.username}, TCP Port: {self.tcp_port}")
        logging.info(f"Port Pairs (Tx/Rx): {self.port_pairs}")
        logging.info(f"Port Config Files: {self.xpc_files}")
        logging.info(f"Test Traffic Duration: {self.test_duration} seconds")
        logging.info(f"Delay After Port Reset: {self.delay_after_reset} seconds")
        logging.info(f"Pre Traffic Interval: {self.pre_traffic_interval} seconds")
        logging.info(f"Post Traffic Interval: {self.post_traffic_interval} seconds")
        logging.info(f"Result Directory Prefix: {self.resultdir_prefix}")
        logging.info(f"===============================================")
        logging.info(f"===============================================")

    async def connect(self):
        self.chassis_obj = await testers.L23Tester(
            host=self.chassis,
            username=self.username,
            password=self.password,
            port=self.tcp_port,
            enable_logging=self.debug_logging
        )

    async def load_port_config(self):
        # Establish connection to a Xena tester using Python context manager
        # The connection will be automatically terminated when it is out of the block
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{self.chassis}")
        logging.info(f"{'Username:':<20}{self.username}")

        #################################################
        #             Load Port Config                  #
        #################################################
        # Load port configurations if any
        if len(self.xpc_files) > 0:
            logging.info(f"Loading port configurations from .xpc files...")
            for pp in self.xpc_files:
                for port_str, xpc_file in pp.items():
                    if xpc_file == "":
                        continue
                    module_obj, port_obj = get_module_and_port_objs(port_str, self.chassis_obj)
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

        # Wait for a while before starting traffic. This is because some DUTs may need more time to get ready after port reset.
        # Port reset happens during port reservation and loading port configuration from .xpc file.
        logging.info(f"Waiting for {self.delay_after_reset} seconds after port reset/configuration...")
        await asyncio.sleep(self.delay_after_reset)  

        #################################################
        #                Stream Data Struct             #
        #################################################
        # stream data structure list to save stream related objects and info
        for port_pair in self.port_pairs:
            tx_port_str = port_pair["tx"]
            rx_port_str = port_pair["rx"]

            x, y = get_module_and_port_objs(tx_port_str, self.chassis_obj)
            if x is None or y is None:
                logging.error(f"Failed to get module or port object for Tx port {tx_port_str}")
                continue
            tx_module_obj, tx_port_obj = x, y
            x, y = get_module_and_port_objs(rx_port_str, self.chassis_obj)
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
            
            rx_port_filter_idx_list = []
            for filter_obj in rx_port_obj.filters:
                rx_port_filter_idx_list.append(filter_obj.idx)
            rx_port_filter_idx_list.sort()

            rx_port_histogram_idx_list = []
            for dataset_obj in rx_port_obj.datasets:
                rx_port_histogram_idx_list.append(dataset_obj.idx)
            rx_port_histogram_idx_list.sort()

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
                logging.info((f"  Tx Port {tx_port_str}: Stream {tx_stream_index} with TPLD ID {tx_stream_tpld_id}"))

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
                        "pkt_size": pkt_size,
                        "rx_module_obj": rx_module_obj,
                        "rx_port_str": rx_port_str,
                        "rx_port_obj": rx_port_obj,
                        "rx_port_ifg": rx_port_ifg,
                        "rx_port_filter_idx_list": rx_port_filter_idx_list,
                        "rx_port_histogram_idx_list": rx_port_histogram_idx_list,
                    }
                )
    
    async def prepare_data_storage(self):
        # Prepare the CSV file header row
        field = ["Timestamp (Rx)", "SrcPort", "SID", "DestPort", "TID", "StreamDescription", "TxL1Bps", "TxBps", "TxBytesps", "TxFps", "TxBytes", "TxFrames", "RxL1Bps", "RxBps", "RxBytesps", "RxFps", "RxBytes", "RxFrames", "RxOversizePackets", "RxUndersizePackets", "RxJabberPackets", "RxFcsErrors", "RxLossPcks", "RxMisErr", "RxPldErr", "LatencyCurr", "LatencyCurrMin", "LatencyCurrMax", "LatencyAvg", "LatencyMin", "LatencyMax", "JitterCurr", "JitterCurrMin", "JitterCurrMax", "JitterAvg", "JitterMin", "JitterMax"]
        
        self.stats_data.append(field)

        # Prepare histogram data structures
        for stream_struct_list in self.stream_struct_list:
            tx_port_obj: ports.GenericL23Port = stream_struct_list["tx_port_obj"]
            rx_port_obj: ports.GenericL23Port = stream_struct_list["rx_port_obj"]

            for histogram_obj in tx_port_obj.datasets:
                _histogram_dict = {}
                _histogram_dict["port_str"] = f"P{tx_port_obj.kind.port_id}"
                resp = await histogram_obj.source.get()
                if resp.source_type == enums.SourceType.RX_LATENCY:
                    _histogram_dict["title"] = "RX Latency Distribution (ns)"
                    _histogram_dict["type"] = "Latency"
                elif resp.source_type == enums.SourceType.RX_JITTER:
                    _histogram_dict["title"] = "RX Jitter Distribution (ns)"
                    _histogram_dict["type"] = "Jitter"
                else:
                    _histogram_dict["title"] = "RX Distribution"
                    _histogram_dict["type"] = "Other"

                _histogram_dict["tpld_id"] = resp.identity

                # Get X axis data
                resp = await histogram_obj.range.get()
                _start = resp.start
                _step = resp.step
                _bucket_count = resp.bucket_count
                _histogram_dict["bucket_count"] = _bucket_count
                _histogram_dict["x_axis"] = []
                
                _histogram_dict["x_axis"].append("X (start):")
                _histogram_dict["x_axis"].append(-1)
                for i in range(_bucket_count-1):
                    _histogram_dict["x_axis"].append(_start + i * _step)
                _histogram_dict["x_axis"][-1] = _histogram_dict["x_axis"][-1] + 2*_step

                # Get Y axis data
                _histogram_dict["y_axis"] = []
                _histogram_dict["y_axis"].append("Y (packets):")
                resp = await histogram_obj.samples.get()
                _packet_counts = resp.packet_counts
                _histogram_dict["y_axis"].extend(_packet_counts)
                # extend the Y axis data to match the X axis data length with 0s
                _histogram_dict["y_axis"].extend([0] * (_bucket_count - len(resp.packet_counts)))
                _histogram_dict["packet_counts"] = _packet_counts

                # Save the histogram dict to the main histogram data dict
                self.histogram_data[f"p{tx_port_obj.kind.port_id}-{_histogram_dict['type'].lower()}"] = _histogram_dict

    async def run(self):
            await self.connect()
            await self.load_port_config()
            await self.prepare_data_storage()
            logging.info(f"Clear statistics and enable streams/histograms...")
            # clear port statistics on all involved ports
            for port_obj in self.tx_port_obj_set.union(self.rx_port_obj_set):
                await port_obj.statistics.tx.clear.set()
                await port_obj.statistics.rx.clear.set()
                logging.info(f"  Cleared statistics on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")

                # enable all streams on the tx port
                for tx_stream_obj in port_obj.streams:
                    await tx_stream_obj.enable.set_on()
                logging.info(f"  Enabled all streams on Port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
            
            # start histogram on all involved ports
            for rx_port_obj in self.rx_port_obj_set:
                for histogram_obj in rx_port_obj.datasets:
                    await histogram_obj.enable.set_on()
                logging.info(f"  Enabled histogram {histogram_obj.idx} on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")

            # Wait for pre-traffic interval
            await asyncio.sleep(self.pre_traffic_interval)
            statistics_duration = self.pre_traffic_interval + self.test_duration + self.post_traffic_interval
            logging.info(f"Collecting statistics for {statistics_duration} seconds")

            try:
                for tick in range(statistics_duration):
                    await self.query_statistics()
                    logging.info(f"Statistics collection #{tick} completed.")
                    if tick == self.pre_traffic_interval-1:
                        await self.start_traffic()
                    if tick == self.pre_traffic_interval + self.test_duration-1:
                        await self.stop_traffic()
                    # wait for 1 second before the next query
                    await asyncio.sleep(1.000)
            except asyncio.CancelledError:
                logging.error(f"Statistics collection cancelled.")
                await self.stop_traffic()
                await asyncio.sleep(self.post_traffic_interval)
                await self.query_statistics()
            finally:
                # Stop histogram on all involved ports
                for rx_port_obj in self.rx_port_obj_set:
                    for histogram_obj in rx_port_obj.datasets:
                        await histogram_obj.enable.set_off()
                    logging.info(f"Disabled histogram {histogram_obj.idx} on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                await self.save_data()
                await self.disconnect()

    async def save_data(self):
        # Save the collected statistics data into a CSV file
        self.stream_stats_path = os.path.join(self.result_dir, f"statistics_{self.logfile_creation_time}.csv")
        with open(self.stream_stats_path, 'w+', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for row in self.stats_data:
                writer.writerow(row)
        logging.info(f"statistics_{self.logfile_creation_time}.csv saved.")
        
        for _, histogram_dict in self.histogram_data.items():
            _port_str = histogram_dict["port_str"]
            _type = histogram_dict["type"]
            _title = histogram_dict["title"]
            histogram_path = os.path.join(self.result_dir, f"{_port_str}-Histogram {_type} data {self.histogram_timestamp} {_title}.csv")
            with open(histogram_path, 'w+', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([_title])
                writer.writerow(histogram_dict["x_axis"])
                writer.writerow(histogram_dict["y_axis"])
            logging.info(f"{_port_str}-Histogram {_type} data {self.histogram_timestamp} {_title}.csv saved.")
        
        logging.info(f"All data saved to directory: {self.result_dir}")


    async def query_statistics(self):
        # The time string for this batch of statistics
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

            # Query histogram data
            for i in stream_struct["rx_port_histogram_idx_list"]:
                histogram_obj = rx_port_obj.datasets.obtain(i)
                commands.append(histogram_obj.samples.get())

        # Send the commands and get the responses
        responses = await asyncio.gather(*commands)
        test_data_list = []

        # The timestamp in the statistics log is the time when the data is received.
        curr_time = datetime.now()
        batch_time = curr_time.strftime("%Y%m%d-%H%M%S.%f")

        for i in range(0, len(responses), 8):
            test_data_list.append(responses[i:i + 8])
        for test_data, stream_struct in zip(test_data_list, self.stream_struct_list):
            # Clear the stats data row for this stream
            _stats_data_row = []
            tx_port_ifg = stream_struct["tx_port_ifg"]
            rx_port_ifg = stream_struct["rx_port_ifg"]
            pkt_size = stream_struct["pkt_size"]
            _stats_data_row.append(batch_time) # Timestamp
            _tx_port_str = f"P-{stream_struct['tx_port_str'].replace('/', '-')}"
            _stats_data_row.append(_tx_port_str) # SrcPort
            _stats_data_row.append(stream_struct["stream_index"]) # SID
            _rx_port_str = f"P-{stream_struct['rx_port_str'].replace('/', '-')}"
            _stats_data_row.append(_rx_port_str) # DestPort
            _stats_data_row.append(stream_struct["stream_tpld_id"]) # TID
            _stats_data_row.append(stream_struct["stream_comment"]) # StreamDescription

            tx_bps = test_data[0].bit_count_last_sec
            tx_fps = test_data[0].packet_count_last_sec
            tx_bytes = test_data[0].byte_count_since_cleared
            tx_frames = test_data[0].packet_count_since_cleared
            tx_l1_bps = tx_fps * (tx_port_ifg + pkt_size)*8
            _stats_data_row.append(tx_l1_bps) # TxL1Bps
            _stats_data_row.append(tx_bps) # TxBps
            _stats_data_row.append(int(tx_bps / 8)) # TxBytesps
            _stats_data_row.append(tx_fps) # TxFps
            _stats_data_row.append(tx_bytes) # TxBytes
            _stats_data_row.append(tx_frames) # TxFrames

            rx_bps = test_data[1].bit_count_last_sec
            rx_bytesps = test_data[1].byte_count_last_sec
            rx_fps = test_data[1].packet_count_last_sec
            rx_bytes = test_data[1].byte_count_since_cleared
            rx_frames = test_data[1].packet_count_since_cleared
            rx_l1_bps = rx_fps * (rx_port_ifg + pkt_size)*8
            _stats_data_row.append(rx_l1_bps) # RxL1Bps
            _stats_data_row.append(rx_bps) # RxBps
            _stats_data_row.append(rx_bytesps) # RxBytesps
            _stats_data_row.append(rx_fps) # RxFps
            _stats_data_row.append(rx_bytes) # RxBytes
            _stats_data_row.append(rx_frames) # RxFrames

            rx_oversize = test_data[5].oversize_count if test_data[5].oversize_count >= 0 else "N/A"
            rx_undersize = test_data[5].undersize_count if test_data[5].undersize_count >= 0 else "N/A"
            rx_jabber = test_data[5].jabber_count if test_data[5].jabber_count >= 0 else "N/A"
            rx_fcs_errors = test_data[5].fcs_error_count if test_data[5].fcs_error_count >= 0 else "N/A"
            _stats_data_row.append(rx_oversize) # RxOversizePackets
            _stats_data_row.append(rx_undersize) # RxUndersizePackets
            _stats_data_row.append(rx_jabber) # RxJabberPackets
            _stats_data_row.append(rx_fcs_errors) # RxFcsErrors

            rx_loss = test_data[4].non_incre_seq_event_count if test_data[4].non_incre_seq_event_count != -1 else "N/A"
            rx_misorder = test_data[4].swapped_seq_misorder_event_count if test_data[4].swapped_seq_misorder_event_count != -1 else "N/A"
            rx_payload_err = test_data[4].non_incre_payload_packet_count if test_data[4].non_incre_payload_packet_count != -1 else "N/A"
            _stats_data_row.append(rx_loss) # RxLossPcks
            _stats_data_row.append(rx_misorder) # RxMisErr
            _stats_data_row.append(rx_payload_err) # RxPldErr

            rx_latency_curr = test_data[2].avg_last_sec if (test_data[2].avg_last_sec != -1 and test_data[2].avg_last_sec != -2147483648) else "N/A"
            rx_latency_curr_min = test_data[2].min_last_sec if (test_data[2].min_last_sec != -1 and test_data[2].min_last_sec != -2147483648) else "N/A"
            rx_latency_curr_max = test_data[2].max_last_sec if (test_data[2].max_last_sec != -1 and test_data[2].max_last_sec != -2147483648) else "N/A"
            rx_latency_avg = test_data[2].avg_val if (test_data[2].avg_val != -1 and test_data[2].avg_val != -2147483648) else "N/A"
            rx_latency_min = test_data[2].min_val if (test_data[2].min_val != -1 and test_data[2].min_val != -2147483648) else "N/A"
            rx_latency_max = test_data[2].max_val if (test_data[2].max_val != -1 and test_data[2].max_val != -2147483648) else "N/A"
            _stats_data_row.append(rx_latency_curr) # LatencyCurr
            _stats_data_row.append(rx_latency_curr_min) # LatencyCurrMin
            _stats_data_row.append(rx_latency_curr_max) # LatencyCurrMax
            _stats_data_row.append(rx_latency_avg) # LatencyAvg
            _stats_data_row.append(rx_latency_min) # LatencyMin
            _stats_data_row.append(rx_latency_max) # LatencyMax

            rx_jitter_curr = test_data[3].avg_last_sec if (test_data[3].avg_last_sec != -1 and test_data[3].avg_last_sec != -2147483648) else "N/A"
            rx_jitter_curr_min = test_data[3].min_last_sec if (test_data[3].min_last_sec != -1 and test_data[3].min_last_sec != -2147483648) else "N/A"
            rx_jitter_curr_max = test_data[3].max_last_sec if (test_data[3].max_last_sec != -1 and test_data[3].max_last_sec != -2147483648) else "N/A"
            rx_jitter_avg = test_data[3].avg_val if (test_data[3].avg_val != -1 and test_data[3].avg_val != -2147483648) else "N/A"
            rx_jitter_min = test_data[3].min_val if (test_data[3].min_val != -1 and test_data[3].min_val != -2147483648) else "N/A"
            rx_jitter_max = test_data[3].max_val if (test_data[3].max_val != -1 and test_data[3].max_val != -2147483648) else "N/A"
            _stats_data_row.append(rx_jitter_curr) # JitterCurr
            _stats_data_row.append(rx_jitter_curr_min) # JitterCurrMin
            _stats_data_row.append(rx_jitter_curr_max) # JitterCurrMax
            _stats_data_row.append(rx_jitter_avg) # JitterAvg
            _stats_data_row.append(rx_jitter_min) # JitterMin
            _stats_data_row.append(rx_jitter_max) # JitterMax

            # Append the stream stats data row to the stats data
            self.stats_data.append(_stats_data_row)

            # Save histogram data into memory for later saving to CSV files
            rx_port_obj: ports.GenericL23Port = stream_struct["rx_port_obj"]

            _histogram_dict = self.histogram_data[f"p{rx_port_obj.kind.port_id}-latency"]                    
            _pkt_cnt = test_data[6].packet_counts
            _y_data = ["Y (packets):"]
            _y_data.extend(_pkt_cnt)
            _y_data.extend([0] * (_histogram_dict["bucket_count"] - len(_pkt_cnt)))
            _histogram_dict["y_axis"] = _y_data

            _histogram_dict = self.histogram_data[f"p{rx_port_obj.kind.port_id}-jitter"]                    
            _pkt_cnt = test_data[7].packet_counts
            _y_data = ["Y (packets):"]
            _y_data.extend(_pkt_cnt)
            _y_data.extend([0] * (_histogram_dict["bucket_count"] - len(_pkt_cnt)))
            _histogram_dict["y_axis"] = _y_data

    async def statistics_background_task(self, duration: int):
        """Background task to collect statistics for a given duration.

        :param duration: Duration in seconds to collect statistics
        :type duration: int
        """
        try:
            for tick in range(duration):
                if self.stop_event.is_set():
                    logging.info(f"Statistics collection cancelled by stop event.")
                    break
                await self.query_statistics()
                await asyncio.sleep(1)  # wait for 1 second before the next query
                logging.info(f"Statistics collection #{tick+1} completed.")
        except asyncio.CancelledError:
            logging.error(f"Statistics collection cancelled.")
    
    async def start_traffic(self):
        # start traffic on all tx ports
        logging.info(f"Starting traffic on all Tx ports")
        module_ports = []
        for tx_port_obj in self.tx_port_obj_set:
            module_ports.append(tx_port_obj.kind.module_id)
            module_ports.append(tx_port_obj.kind.port_id)
        await self.chassis_obj.traffic.set(on_off=enums.OnOff.ON, module_ports=module_ports)

    async def stop_traffic(self):
        # stop traffic on all tx ports
        logging.info(f"Stopping traffic on all Tx ports")
        module_ports = []
        for tx_port_obj in self.tx_port_obj_set:
            module_ports.append(tx_port_obj.kind.module_id)
            module_ports.append(tx_port_obj.kind.port_id)
        await self.chassis_obj.traffic.set(on_off=enums.OnOff.OFF, module_ports=module_ports)

    async def disconnect(self):
        # Disconnect from the chassis
        await self.chassis_obj.session.logoff()
        logging.info(f"Disconnected from chassis: {self.chassis}")

# *************************************************************************************
# main function
# *************************************************************************************
async def main(config_file: str = "config.json"):
    stop_event = asyncio.Event()
    ccc = XenaConfigControlCollect(stop_event)
    ccc.load_test_config(config_file=config_file)
    await ccc.run()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "config.json"))