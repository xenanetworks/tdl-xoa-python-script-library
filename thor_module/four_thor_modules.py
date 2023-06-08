import asyncio
from contextlib import suppress
from xoa_driver import (
    testers,
    modules,
    ports,
    utils,
    enums,
    exceptions
)
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import ArpChunk, NdpChunk, Hex
import ipaddress
from binascii import hexlify


#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"
MODULE_IDXS = [4,8]
PORT_IDX = 0

#---------------------------
# MODULE MEDIA
#---------------------------

# MODULE_MEDIA = enums.MediaConfigurationType.QSFPDD_PAM4
# PORT_COUNT = 1
# PORT_SPEED = 400000

# PORT_COUNT = 2
# PORT_SPEED = 200000

# PORT_COUNT = 4
# PORT_SPEED = 100000

# PORT_COUNT = 8
# PORT_SPEED = 50000

MODULE_MEDIA = enums.MediaConfigurationType.QSFP56_PAM4
PORT_COUNT = 2
PORT_SPEED = 200000

# PORT_COUNT = 4
# PORT_SPEED = 100000

# PORT_COUNT = 8
# PORT_SPEED = 50000

# MODULE_MEDIA = enums.MediaConfigurationType.QSFP28_NRZ
# PORT_COUNT = 2
# PORT_SPEED = 100000

# PORT_COUNT = 4
# PORT_SPEED = 50000

# PORT_COUNT = 2
# PORT_SPEED = 40000

# PORT_COUNT = 8
# PORT_SPEED = 525000

# PORT_COUNT = 8
# PORT_SPEED = 10000

#---------------------------
# STREAM PARAM
#---------------------------

SRC_IPV4 = "10.0.0.2"
SRC_MAC = "AAAAAAAAAA00"
DST_IPV4 = "10.1.0.2"
DST_MAC = "BBBBBBBBBB00"

FRAME_SIZE_BYTES = 128      # frame size including FCS field
STREAM_RATE = 100.0         # this means 100.0%
TRAFFIC_DURATION = 10       # 10 seconds

# ETHERNET HEADER
ETHERNET_TYPE =     "0800"

# IPV4
VERSION = "4"
HEADER_LENGTH = "5"
DSCP_ECN = "00"
TOTAL_LENGTH = '{:04X}'.format(FRAME_SIZE_BYTES - 14 - 4)
IDENTIFICATION = "0000"
FLAGS_OFFSET = "0000"
TTL = "7F"
PROTOCOL = "11"
HEADER_CHECKSUM = "0000"

# PAYLOAD PATTER
PAYLOAD_PATTERN = "FFFF0000"


async def thor_module_streams(stop_event: asyncio.Event):
    # create tester instance and establish connection+
    async with testers.L23Tester(CHASSIS_IP, USERNAME) as tester:
        
        print(f"============================")
        print(f"{'MODULE MEDIA CONFIG'}")
        print(f"============================")

        for mid in MODULE_IDXS:
            # access module on the tester
            module = tester.modules.obtain(mid)

            if not isinstance(module, modules.MThor400G7S1P): #!Make sure this is your module!#
                return None # commands which used in this example are not supported by Chimera Module

            # reserve module
            print(f"Reserve module {mid}")
            await mgmt.free_module(module=module, should_free_ports=True)
            await mgmt.reserve_module(module=module, force=True)

            # change module media
            print(f"Change module {mid} media to {MODULE_MEDIA.name}")
            await module.media.set(media_config=MODULE_MEDIA)

            # Change module's port config
            print(f"Change port config to {PORT_COUNT}x{int(PORT_SPEED/1000)}G")
            port_count = PORT_COUNT
            port_speed = PORT_SPEED
            speeds = [port_count]
            speeds.extend([port_speed]*port_count)
            await module.cfp.config.set(portspeed_list=speeds)

    async with testers.L23Tester(CHASSIS_IP, USERNAME) as tester:
        
        print(f"============================")
        print(f"{'PORT & STREAM CONFIG'}")
        print(f"============================")

        _ports = []
        _modules = []
        for mid in MODULE_IDXS:
            # access module on the tester
            module = tester.modules.obtain(mid)
            _modules.append(module)

            if not isinstance(module, modules.MThor400G7S1P): #!Make sure this is your module!#
                return None # commands which used in this example are not supported by Chimera Module

            # reserve module
            await mgmt.reserve_module(module=module, force=True)

            # access port on the module
            port = module.ports.obtain(PORT_IDX)
            await mgmt.reserve_port(port, force=True)

            print(f"Set port {mid}/{PORT_IDX} to RS-FEC")
            # fec mode = rs-fec
            await port.fec_mode.set_rs_fec()

            # Create the stream on the port
            print(f"Create a stream on port {mid}/{PORT_IDX}")
            stream = await port.streams.create()

            print(f"{'Stream DMAC:':<20}{DST_MAC}")
            print(f"{'Stream SMAC:':<20}{SRC_MAC}")
            print(f"{'Stream SRC IPv4:':<20}{SRC_IPV4}")
            print(f"{'Stream DST IPv4:':<20}{DST_IPV4}")
            src_ip = ipaddress.IPv4Address(SRC_IPV4)
            hexlify(src_ip.packed).decode()
            dst_ip = ipaddress.IPv4Address(DST_IPV4)
            hexlify(dst_ip.packed).decode()
            HEADER = f'{DST_MAC}{SRC_MAC}{ETHERNET_TYPE}{VERSION}{HEADER_LENGTH}{DSCP_ECN}{TOTAL_LENGTH}{IDENTIFICATION}{FLAGS_OFFSET}{TTL}11{HEADER_CHECKSUM}{hexlify(src_ip.packed).decode()}{hexlify(dst_ip.packed).decode()}'

            print(f"{'Stream Rate:':<20}{STREAM_RATE}%")
            print(f"{'Stream Frame Size:':<20}{FRAME_SIZE_BYTES} bytes")
            print(f"{'Traffic Duration:':<20}{TRAFFIC_DURATION} seconds")
            await utils.apply(
                stream.enable.set_on(),
                stream.packet.limit.set(packet_count=-1),
                stream.comment.set(f"Test stream"),
                stream.rate.fraction.set(stream_rate_ppm=int(1000000*(STREAM_RATE/100))),            
                stream.packet.header.protocol.set(segments=[
                    enums.ProtocolOption.ETHERNET,
                    enums.ProtocolOption.IP]),
                stream.packet.header.data.set(hex_data=Hex(HEADER)),
                stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=FRAME_SIZE_BYTES, max_val=FRAME_SIZE_BYTES),
                stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex(PAYLOAD_PATTERN)),
                stream.tpld_id.set(test_payload_identifier = mid),
                stream.insert_packets_checksum.set_on(),
            )
            _ports.append(port)

        print(f"============================")
        print(f"{'TRAFFIC CONTROL'}")
        print(f"============================")
        print(f"Clear port's RX & TX counters")
        for port in _ports:
            await utils.apply(
                port.statistics.rx.clear.set(),
                port.statistics.tx.clear.set()
            )

        print(f"Start traffic")
        for port in _ports:
            await port.traffic.state.set_start()
        
        await asyncio.sleep(TRAFFIC_DURATION)
        print(f"Stop traffic")
        for port in _ports:
            await port.traffic.state.set_stop()

        # read the TX/RX packets and TX/RX bytes
        await asyncio.sleep(2)
        print(f"Read port's RX & TX counters")

        for port in _ports:
            _tx, _rx = await utils.apply(
                port.statistics.tx.total.get(),
                port.statistics.rx.total.get(),
            )
            print(f"============================")
            print(f"{'TRAFFIC STATS'}")
            print(f"============================")
            print(f"{'TX FRAMES:':<20}{_tx.packet_count_since_cleared}")
            print(f"{'RX FRAMES:':<20}{_rx.packet_count_since_cleared}")
            print(f"{'TX BYTES:':<20}{_tx.byte_count_since_cleared}")
            print(f"{'RX BYTES:':<20}{_rx.byte_count_since_cleared}")

        for module in _modules:
            await mgmt.free_module(module=module, should_free_ports=True)



async def main():
    stop_event = asyncio.Event()
    try:
        await thor_module_streams(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())