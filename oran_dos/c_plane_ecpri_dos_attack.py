import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt, cli
from xoa_driver.misc import Hex
import ipaddress
from headers import *

CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "oran_dos"
PORT = "7/1"
XPC_MODE = True
DURATION = 10
XPC_FILENAME = "ecpri_dos.xpc"

async def s_plane_ptp_dos(chassis_ip: str, port_str: str, username: str, xpc_mode: bool, duration: int):

    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])

    print(f"#####################################################################")
    print(f"Test:               C-Plane eCPRI DoS Attack")
    print(f"Chassis:            {chassis_ip}")
    print(f"Username:           {username}")
    print(f"Port:               {port_str}")
    print(f"XPC mode:           {xpc_mode}")
    print(f"Test Duration:      {duration} sec")
    print(f"#####################################################################")


    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    print(f"Connect to chassis")
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        module = tester.modules.obtain(_mid)

        if isinstance(module, modules.ModuleChimera):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module
        port = module.ports.obtain(_pid)

        # Forcibly reserve the TX port and reset it.
        print(f"Reserve port {port.kind.module_id}/{port.kind.port_id}")
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)
        await asyncio.sleep(2)

        if xpc_mode:
            # Configure port from .xpc file
            print(f"Load {XPC_FILENAME}")
            await cli.port_config_from_file(port, XPC_FILENAME)
        else:
            print(f"Configure port and stream")
            # Configure port using native python
            await port.max_header_length.set(max_header_length=256) # Port's max header length = 128
            stream = await port.streams.create() # create a stream on the port
            
            # Prepare packet header data
            eth = Ethernet()
            eth.dst_mac = "0080.1600.0000"
            eth.src_mac = "0030.051d.1e27"
            eth.ethertype = "AEFE"

            ecpri = eCPRIGeneralDataTransfer()
            
            await utils.apply(
                stream.comment.set(comment="C-Plane eCPRI DoS Attack"), # stream description
                stream.rate.fraction.set(stream_rate_ppm=100_000), # rate in ppm, 10%=100_000, 100%=1_000_000
                stream.burst.burstiness.set(size=0, density=100), # non-burst, burst size = 0, burst density = 100%
                stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.RAW_28]), # stream header, Ethernet | RAW28
                stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ecpri))),
                stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=68, max_val=68),
                stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex("00")),
                stream.tpld_id.set(test_payload_identifier=-1),
                stream.insert_packets_checksum.set_on(),
                stream.enable.set_on()
            )
            
            await stream.packet.header.modifiers.configure(1) # create one modifier and configure
            mod0 = stream.packet.header.modifiers.obtain(0) # access the created modifier
            # configure the modifier
            # place the modifier on header position 6
            await mod0.specification.set(position=6, mask=Hex("FFFF0000"), action=enums.ModifierAction.RANDOM, repetition=1) 
            await mod0.range.set(min_val=0, step=1, max_val=65535)

        # start traffic
        print(f"Start traffic")
        await port.traffic.state.set_start()
        # test duration
        for i in range(duration):
            print(f"."*(i+1))
            await asyncio.sleep(1)
        # stop traffic
        print(f"Stop traffic")
        await port.traffic.state.set_stop()
        await mgmt.free_port(port)

        print(f"Done")

async def main():
    stop_event = asyncio.Event()
    try:
        await s_plane_ptp_dos(CHASSIS_IP, PORT, USERNAME, XPC_MODE, DURATION)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
