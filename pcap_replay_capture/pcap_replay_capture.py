
################################################################
#
#                   PCAP REPLAY AND CAPTURE
#
# This example uses one Xena port to replay pcap packets and
# another one to capture.
#
# It uses a third-party package called scapy to read a pcap file
# and send each packet. 
#
# Captured packets are saved into another pcap file.
#
################################################################

import asyncio
from xoa_driver import (
    testers,
    modules,
    ports,
    utils,
    enums,
    exceptions
)
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import logging
import scapy.all

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.66"
USERNAME = "XOA"
REPLAY_PORT = "7/0"
CAPTURE_PORT = "7/1"
PCAP_FILENAME = "replay.pcap"
CAPTURED_FILENAME = "capture.pcap"

#---------------------------
# pcap_replay_capture
#---------------------------
async def pcap_replay_capture(chassis: str, username: str, replay_file: str, replay_port_str: str, capture_file: str, capture_port_str: str):
    
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # create tester object and establish connection using context manager with statement
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"===================================")
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")
        
        # get replay port object
        _mid = int(replay_port_str.split("/")[0])
        _pid = int(replay_port_str.split("/")[1])
        replay_module_obj = tester.modules.obtain(_mid)

        if isinstance(replay_module_obj, modules.ModuleChimera):
            return None
        replay_port_obj = replay_module_obj.ports.obtain(_pid)

        # get capture port object
        _mid = int(capture_port_str.split("/")[0])
        _pid = int(capture_port_str.split("/")[1])
        capture_module_obj = tester.modules.obtain(_mid)
        if isinstance(capture_module_obj, modules.ModuleChimera):
            return None
        capture_port_obj = capture_module_obj.ports.obtain(_pid)

        # reserve the port objects
        await mgmt.release_module(module=replay_module_obj, should_release_ports=False)
        await mgmt.reserve_port(port=replay_port_obj, force=True, reset=True)
        await mgmt.release_module(module=capture_module_obj, should_release_ports=False)
        await mgmt.reserve_port(port=capture_port_obj, force=True, reset=True)

        # configure capture trigger criteria
        await capture_port_obj.capturer.state.set(on_off=enums.StartOrStop.STOP)
        await capture_port_obj.capturer.trigger.set(start_criteria=enums.StartTrigger.ON,
                                        start_criteria_filter=0,
                                        stop_criteria=enums.StopTrigger.FULL,
                                        stop_criteria_filter=0)
        
        # configure packets to keep
        await capture_port_obj.capturer.keep.set(kind=enums.PacketType.ALL, index=0, byte_count=-1)

        # start capture
        await capture_port_obj.capturer.state.set(on_off=enums.StartOrStop.START)        

        # start replay on the replay port
        packet_list = scapy.all.rdpcap(filename=replay_file, count=-1)
        for i in range(len(packet_list)):
            pkt_hexstr= scapy.all.raw(packet_list[i]).hex()
            await replay_port_obj.tx_single_pkt.send.set(hex_data=Hex(pkt_hexstr))
            logging.info(f"Send packet #{i}: {pkt_hexstr}")

        await asyncio.sleep(10)

        # stop capture
        await capture_port_obj.capturer.state.set(on_off=enums.StartOrStop.STOP)
        # await port.capturer.state.set_stop()  # this is a shortcut func
        
        # check capture status
        resp = await capture_port_obj.capturer.stats.get()
        logging.info(f"Capture status: {'running' if resp.status == 0 else 'stopped'}")
        logging.info(f"Number of captured packets: {resp.packets}")

        # read captures packets from the buffer and show them one by one
        _packet_list = await capture_port_obj.capturer.obtain_captured()
        cap_packet_list = []
        for i in range(len(_packet_list)):
            resp = await _packet_list[i].packet.get()
            pkt_hexstr = resp.hex_data
            logging.info(f"Capt packet # {i}: {pkt_hexstr}")
            _pkt_bytes = bytes.fromhex(pkt_hexstr)
            cap_packet_list.append(_pkt_bytes)
        scapy.all.wrpcap(filename=capture_file, pkt=cap_packet_list)

        # release the port
        await mgmt.release_port(replay_port_obj)
        await mgmt.release_port(capture_port_obj)


async def main():
    stop_event = asyncio.Event()
    try:
        await pcap_replay_capture(
            chassis=CHASSIS_IP, 
            username=USERNAME, 
            replay_file=PCAP_FILENAME, 
            replay_port_str=REPLAY_PORT, 
            capture_file=CAPTURED_FILENAME, 
            capture_port_str=CAPTURE_PORT
            )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())