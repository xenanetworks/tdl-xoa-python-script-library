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
from binascii import hexlify
import ipaddress

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"

_THOR_MODULES = (modules.MThor400G7S1P, modules.MThor400G7S1P_b, modules.MThor400G7S1P_c, modules.MThor400G7S1P_d)
_TRAFFIC_DURATION = 10
_COOL_DOWN = 2

#---------------------------
# MODULE PORT TRAFFIC CONFIG
#---------------------------
module_port_traffic_config = [
    {
        "mid": 4,
        "media": enums.MediaConfigurationType.QSFP56_PAM4,
        "timing source": enums.TimingSource.CHASSIS,
        "local clock adjustment ppm": 10,
        "port count": 2,
        "port speed": 200_000,
        "ports": [
            {
                "pid": 0,
                "port fec mode": enums.FECMode.RS_FEC,
                "autoneg": False,
                "link training": False,
                "streams": [
                    {
                        "src mac": "00000A000002",
                        "dst mac": "00000A010002",
                        "src ip": "10.0.0.2",
                        "dest ip": "11.0.0.2",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 128,
                        "frame size max": 128,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "1234432156788765ABCDDCBAFFFFEEEE1221",
                        "tpld id": 0
                    },
                    {
                        "src mac": "00000A000003",
                        "dst mac": "00000A010003",
                        "src ip": "10.0.0.3",
                        "dest ip": "11.0.0.3",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 256,
                        "frame size max": 256,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF0000",
                        "tpld id": 1
                    }
                ]
            },
            {
                "pid": 1,
                "port fec mode": enums.FECMode.RS_FEC,
                "autoneg": False,
                "link training": False,
                "streams": [
                    {
                        "src mac": "00000B000002",
                        "dst mac": "00000B010002",
                        "src ip": "11.0.0.2",
                        "dest ip": "10.0.0.2",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 128,
                        "frame size max": 128,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF0000FFFFEEEE",
                        "tpld id": 2
                    },
                    {
                        "src mac": "00000B000003",
                        "dst mac": "00000B010003",
                        "src ip": "11.0.0.3",
                        "dest ip": "10.0.0.3",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 256,
                        "frame size max": 256,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF1234",
                        "tpld id": 3
                    },
                    {
                        "src mac": "00000B000004",
                        "dst mac": "00000B010004",
                        "src ip": "11.0.0.4",
                        "dest ip": "10.0.0.4",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 512,
                        "frame size max": 512,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF00000000",
                        "tpld id": 4
                    }
                ]
            }
        ]
    },
    {
        "mid": 8,
        "media": enums.MediaConfigurationType.QSFP56_PAM4,
        "timing source": enums.TimingSource.CHASSIS,
        "local clock adjustment ppm": 10,
        "port count": 2,
        "port speed": 200_000,
        "ports": [
            {
                "pid": 0,
                "port fec mode": enums.FECMode.RS_FEC,
                "autoneg": False,
                "link training": False,
                "streams": [
                    {
                        "src mac": "00000C000002",
                        "dst mac": "00000C010002",
                        "src ip": "13.0.0.2",
                        "dst ip": "14.0.0.2",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 128,
                        "frame size max": 128,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF00001122",
                        "tpld id": 5
                    },
                    {
                        "src mac": "00000D000003",
                        "dst mac": "00000D010003",
                        "src ip": "13.0.0.3",
                        "dst ip": "14.0.0.3",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 256,
                        "frame size max": 256,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFF0000AABB",
                        "tpld id": 6
                    }
                ]
            },
            {
                "pid": 1,
                "port fec mode": enums.FECMode.RS_FEC,
                "autoneg": False,
                "link training": False,
                "streams": [
                    {
                        "src mac": "00000E000002",
                        "dst mac": "00000E010002",
                        "src ip": "14.0.0.2",
                        "dst ip": "13.0.0.2",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 128,
                        "frame size max": 128,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "FFFFEEEE",
                        "tpld id": 7
                    },
                    {
                        "src mac": "00000F000003",
                        "dst mac": "00000F010003",
                        "src ip": "14.0.0.3",
                        "dst ip": "13.0.0.3",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 256,
                        "frame size max": 256,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "DEAD",
                        "tpld id": 8
                    },
                    {
                        "src mac": "000010000004",
                        "dst mac": "000010010004",
                        "src ip": "14.0.0.4",
                        "dst ip": "13.0.0.4",
                        "frame size type": enums.LengthType.FIXED,
                        "frame size min": 512,
                        "frame size max": 512,
                        "stream rate pct": 10.0,
                        "stream rate fps": 10000,
                        "frame count": -1,
                        "payload pattern": "DAED",
                        "tpld id": 9
                    }
                ]
            }
        ]
    },
]


#---------------------------
# eth_header_generator
#---------------------------
def eth_header_generator(
        dst_mac: str = "000000000000", 
        src_mac: str = "000000000000"
        ) -> str:
    _ethertype = "FFFF"

    header = f'{dst_mac}{src_mac}{_ethertype}'
    return header

#---------------------------
# eth_ip_header_generator
#---------------------------
def eth_ip_header_generator(
        dst_mac: str = "000000000000", 
        src_mac: str = "000000000000",
        dst_ip: str = "0.0.0.0",
        src_ip: str = "0.0.0.0",
        frame_size: int = 64

        ) -> str:
    _ethertype = "0800"
    _total_length = '{:04X}'.format(frame_size - 14 - 4)
    _src_ip = ipaddress.IPv4Address(src_ip)
    _dst_ip = ipaddress.IPv4Address(dst_ip)

    header = f'{dst_mac}{src_mac}{_ethertype}4500{_total_length}000000007FFF0000{hexlify(_src_ip.packed).decode()}{hexlify(_dst_ip.packed).decode()}'
    return header

#---------------------------
# thor_ppm_anlt_eth
#---------------------------
async def thor_ppm_anlt_eth(stop_event: asyncio.Event):
    print(f"==================================")
    print(f"{'START'}")
    print(f"==================================")
    # create tester instance and establish connection
    async with testers.L23Tester(host=CHASSIS_IP, username=USERNAME, password="xena", port=22606, enable_logging=False) as tester:
        print(f"{'Connect to chassis:':<20}{CHASSIS_IP}")
        print(f"{'Username:':<20}{CHASSIS_IP}")

        print(f"==================================")
        print(f"{'MODULE MEDIA CONFIG'}")
        print(f"==================================")

        for m_item in module_port_traffic_config:
            # access module on the tester
            mid = m_item["mid"]
            module = tester.modules.obtain(mid)

            if not isinstance(module, _THOR_MODULES):
                print(f"Module {mid} is not a Thor module")
                return None # commands which used in this example are not supported by Chimera Module

            # reserve module
            print(f"Reserve Module {mid}")
            await mgmt.free_module(module=module, should_free_ports=True)
            await mgmt.reserve_module(module=module, force=True)

            # change module media
            module_config = m_item["media"]
            
            resp = await module.media.get()
            print(f"Module {mid}'s current media: {resp.media_config.name}")
            if resp.media_config != module_config:
                print(f"Change Module {mid}'s media to: {module_config.name}")
                await module.media.set(media_config=module_config)
                resp = await module.media.get()
                print(f"Module {mid}'s new media: {resp.media_config.name}")
            else:
                print(f"Module {mid}'s media: no change")

            # Change module's port config
            resp = await module.cfp.config.get()
            print(f"Module {mid}'s current port count x speed: {resp.portspeed_list}")
            port_count = m_item["port count"]
            port_speed = m_item["port speed"]
            
            speeds = [port_count]
            speeds.extend([port_speed]*port_count)
            if resp.portspeed_list != speeds:
                print(f"Change Module {mid}'s port count x speed to: {port_count}x{int(port_speed/1000)}G")
                await module.cfp.config.set(portspeed_list=speeds)
                resp = await module.cfp.config.get()
                print(f"Module {mid}'s new port count x speed: {resp.portspeed_list}")
            else:
                print(f"Module {mid}'s port count x speed: no change")

            print(f"==================================")
            print(f"{'MODULE CLOCK CONFIG'}")
            print(f"==================================")
            # timing configuration
            timing_source = m_item["timing source"]
            local_clock_adjustment_ppm = m_item["local clock adjustment ppm"]
            await module.timing.source.set(source=timing_source)
            await module.timing.clock_local_adjust.set(ppb=local_clock_adjustment_ppm*1000)
            print(f"Module {mid}'s timing source: {timing_source.name}")
            print(f"Module {mid}'s local clock adjustment: {local_clock_adjustment_ppm} ppm")
        
        print(f"==================================")
        print(f"{'PORT CONFIG'}")
        print(f"==================================")

        _module_object_list = []
        _port_object_list = []
        for m_item in module_port_traffic_config:
            # access module on the tester
            mid = m_item["mid"]
            module = tester.modules.obtain(mid)
            _module_object_list.append(module)

            if not isinstance(module, _THOR_MODULES):
                print(f"Module {mid} is not a Thor module")
                return None # commands which used in this example are not supported by Chimera Module

            # reserve module
            await mgmt.reserve_module(module=module, force=True)

            for p_item in m_item["ports"]:
                # access port on the module
                pid = p_item["pid"]
                port = module.ports.obtain(pid)
                _port_object_list.append(port)
                
                await mgmt.reserve_port(port, force=True)
                await mgmt.reset_port(port)

                await asyncio.sleep(5)

                # fec mode = rs-fec
                fec_mode = p_item["port fec mode"]
                await port.fec_mode.set(mode=fec_mode)
                print(f"Set Port {mid}/{pid} to {fec_mode.name}")

                # loopback mode
                await port.loop_back.set_none()

                # ANLT configuration
                print(f"==================================")
                print(f"{'ANLT CONFIG'}")
                print(f"==================================")
                should_an = p_item["autoneg"]
                should_lt = p_item["link training"]
                print(f"{mid}/{pid}: Autoneg: {should_an}, Link Training: {should_lt}")
                
                if should_an == True and should_lt == True:
                    await port.pcs_pma.link_training.settings.set(
                        mode=enums.LinkTrainingMode.START_AFTER_AUTONEG,
                        pam4_frame_size=enums.PAM4FrameSize.P16K_FRAME,
                        nrz_pam4_init_cond=enums.LinkTrainingInitCondition.NO_INIT,
                        nrz_preset=enums.NRZPreset.NRZ_NO_PRESET,
                        timeout_mode=enums.TimeoutMode.DEFAULT
                    )
                    await port.pcs_pma.auto_neg.settings.set(
                        mode=enums.AutoNegMode.ANEG_ON, 
                        tec_ability=enums.AutoNegTecAbility.DEFAULT_TECH_MODE, 
                        fec_capable=enums.AutoNegFECOption.DEFAULT_FEC, 
                        fec_requested=enums.AutoNegFECOption.DEFAULT_FEC, 
                        pause_mode=enums.PauseMode.NO_PAUSE)
                    
                elif should_an == False and should_lt == True:
                    await port.pcs_pma.auto_neg.settings.set(
                        mode=enums.AutoNegMode.ANEG_OFF, 
                        tec_ability=enums.AutoNegTecAbility.DEFAULT_TECH_MODE, 
                        fec_capable=enums.AutoNegFECOption.DEFAULT_FEC, 
                        fec_requested=enums.AutoNegFECOption.DEFAULT_FEC, 
                        pause_mode=enums.PauseMode.NO_PAUSE)
                    await port.pcs_pma.link_training.settings.set(
                        mode=enums.LinkTrainingMode.STANDALONE,
                        pam4_frame_size=enums.PAM4FrameSize.P16K_FRAME,
                        nrz_pam4_init_cond=enums.LinkTrainingInitCondition.NO_INIT,
                        nrz_preset=enums.NRZPreset.NRZ_NO_PRESET,
                        timeout_mode=enums.TimeoutMode.DEFAULT
                    )
                elif should_an == False and should_lt == False:
                    await port.pcs_pma.auto_neg.settings.set(
                        mode=enums.AutoNegMode.ANEG_OFF, 
                        tec_ability=enums.AutoNegTecAbility.DEFAULT_TECH_MODE, 
                        fec_capable=enums.AutoNegFECOption.DEFAULT_FEC, 
                        fec_requested=enums.AutoNegFECOption.DEFAULT_FEC, 
                        pause_mode=enums.PauseMode.NO_PAUSE)
                    await port.pcs_pma.link_training.settings.set(
                        mode=enums.LinkTrainingMode.START_AFTER_AUTONEG,
                        pam4_frame_size=enums.PAM4FrameSize.P16K_FRAME,
                        nrz_pam4_init_cond=enums.LinkTrainingInitCondition.NO_INIT,
                        nrz_preset=enums.NRZPreset.NRZ_NO_PRESET,
                        timeout_mode=enums.TimeoutMode.DEFAULT
                    )
                else:
                    print("Thor doesn't support Autoneg-only mode.")
                
                print(f"==================================")
                print(f"{'STREAM CONFIG'}")
                print(f"==================================")
                for s_item in p_item["streams"]:
                    # Create the stream on the port
                    print(f"Create a stream on port {mid}/{pid}")
                    stream = await port.streams.create()

                    dst_mac = s_item["dst mac"]
                    src_mac = s_item["src mac"]
                    dst_ip = s_item["dst ip"]
                    src_ip = s_item["src ip"]
                    stream_rate_pct = s_item["stream rate pct"]
                    # stream_rate_fps = s_item["stream rate fps"]
                    frame_count = s_item["frame count"]
                    frame_size_type = s_item["frame size type"]
                    frame_size_min = s_item["frame size min"]
                    frame_size_max = s_item["frame size max"]
                    payload_pattern = s_item["payload pattern"]
                    tpld_id = s_item["tpld id"]
                    # header = eth_header_generator(
                    #     dst_mac=dst_mac,
                    #     src_mac=src_mac,
                    #     )
                    header = eth_ip_header_generator(
                        dst_mac=dst_mac,
                        src_mac=src_mac,
                        dst_ip=dst_ip,
                        src_ip=src_ip,
                        frame_size=frame_size_min
                        )
                    print(f"{'  Index:':<20}{stream.idx}")
                    print(f"{'  DMAC:':<20}{dst_mac}")
                    print(f"{'  SMAC:':<20}{src_mac}")
                    print(f"{'  Dest IP:':<20}{dst_ip}")
                    print(f"{'  Src  IP:':<20}{src_ip}")
                    print(f"{'  Rate:':<20}{stream_rate_pct}%")
                    print(f"{'  Frame Size Type:':<20}{frame_size_type.name} bytes")
                    print(f"{'  Frame Size (min):':<20}{frame_size_min} bytes")
                    print(f"{'  Frame Size (max):':<20}{frame_size_max} bytes")
                    print(f"{'  Payload Pattern:':<20}{payload_pattern}")
                    print(f"{'  TPLD ID:':<20}{tpld_id}")

                    await utils.apply(
                        stream.enable.set_on(),
                        stream.packet.limit.set(packet_count=frame_count),
                        stream.comment.set(f"Test stream"),
                        stream.rate.fraction.set(stream_rate_ppm=int(1000000*(stream_rate_pct/100))),
                        # stream.rate.pps.set(stream_rate_pps=stream_rate_fps),  
                        stream.packet.header.protocol.set(segments=[
                            enums.ProtocolOption.ETHERNET,
                            enums.ProtocolOption.IP]),
                        stream.packet.header.data.set(hex_data=Hex(header)),
                        stream.packet.length.set(length_type=frame_size_type, min_val=frame_size_min, max_val=frame_size_max),
                        stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex(payload_pattern)),
                        stream.tpld_id.set(test_payload_identifier = tpld_id),
                        stream.insert_packets_checksum.set_on(),
                    )
                

        print(f"==================================")
        print(f"{'TRAFFIC CONTROL'}")
        print(f"==================================")
        for port in _port_object_list:
            print(f"Clear port {port.kind.module_id}/{port.kind.port_id} RX & TX counters")
            await utils.apply(
                port.statistics.rx.clear.set(),
                port.statistics.tx.clear.set()
            )

        print(f"Traffic duration: {_TRAFFIC_DURATION} seconds")
        for port in _port_object_list:
            print(f"Start traffic on Port {port.kind.module_id}/{port.kind.port_id}")
            await port.traffic.state.set_start()
        
        await asyncio.sleep(_TRAFFIC_DURATION)

        for port in _port_object_list:
            print(f"Stop traffic on Port {port.kind.module_id}/{port.kind.port_id}")
            await port.traffic.state.set_stop()

        # cool down
        print(f"Cooling down: {_COOL_DOWN} seconds")
        await asyncio.sleep(_COOL_DOWN)

        for port in _port_object_list:
            print(f"Read port {port.kind.module_id}/{port.kind.port_id} RX & TX counters")
            _tx, _rx = await utils.apply(
                port.statistics.tx.total.get(),
                port.statistics.rx.total.get(),
            )
            print(f"==================================")
            print(f"{'TRAFFIC STATS'}")
            print(f"==================================")
            print(f"{'TX FRAMES:':<20}{_tx.packet_count_since_cleared}")
            print(f"{'RX FRAMES:':<20}{_rx.packet_count_since_cleared}")
            print(f"{'TX BYTES:':<20}{_tx.byte_count_since_cleared}")
            print(f"{'RX BYTES:':<20}{_rx.byte_count_since_cleared}")

        for module in _module_object_list:
            await mgmt.free_module(module=module, should_free_ports=True)
        
        print(f"==================================")
        print(f"{'DONE'}")
        print(f"==================================")




async def main():
    stop_event = asyncio.Event()
    try:
        await thor_ppm_anlt_eth(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())