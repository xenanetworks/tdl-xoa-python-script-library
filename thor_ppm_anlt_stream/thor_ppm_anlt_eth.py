################################################################
#
#                   THOR PPM, ANLT & STREAM
#
# What this script example does:
# 1. Connect to a tester
# 2. Change the module media type and port speed config on the specified modules
# 3. Configure module clock configuration
# 4. Configure ANLT on specified ports
# 5. Create IP streams on specified ports on the modules
# 6. Start & stop traffic on the ports
# 7. Collect port-level TX & RX counters
# 8. Free the modules and ports
# 9. Disconnect from the tester
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
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import Hex
from binascii import hexlify
import ipaddress
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.166"
USERNAME = "XOA"

TRAFFIC_DURATION = 10
COOL_DOWN = 2

#---------------------------
# MODULE PORT TRAFFIC CONFIG
#---------------------------
CONFIG_DATA = [
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
                        "src mac": "0000.0A00.0002",
                        "dst mac": "0000.0A01.0002",
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
                        "src mac": "0000.0A00.0003",
                        "dst mac": "0000.0A01.0003",
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
                        "src mac": "0000.0B00.0002",
                        "dst mac": "0000.0B01.0002",
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
                        "src mac": "0000.0B00.0003",
                        "dst mac": "0000.0B01.0003",
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
                        "src mac": "0000.0B00.0004",
                        "dst mac": "0000.0B01.0004",
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
# thor_ppm_anlt_stream
#---------------------------
async def thor_ppm_anlt_stream(chassis: str, username: str, duration: int, cool_down: int):
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    logging.info(f"==================================")
    logging.info(f"{'START'}")
    logging.info(f"==================================")
    # create tester instance and establish connection
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"{'Connect to chassis:':<20}{chassis}")
        logging.info(f"{'Username:':<20}{username}")

        logging.info(f"==================================")
        logging.info(f"{'MODULE MEDIA CONFIG'}")
        logging.info(f"==================================")

        for m_item in CONFIG_DATA:
            # access module on the tester
            mid = m_item["mid"]
            module = tester.modules.obtain(mid)

            if not isinstance(module, modules.Z400ThorModule):
                logging.info(f"Module {mid} is not a Thor module")
                return None # commands which used in this example are not supported by Chimera Module

            # reserve module
            logging.info(f"Reserve Module {mid}")
            await mgmt.free_module(module=module, should_free_ports=True)
            await mgmt.reserve_module(module=module, force=True)

            # change module media
            module_config = m_item["media"]
            
            resp = await module.media.get()
            logging.info(f"Module {mid}'s current media: {resp.media_config.name}")
            if resp.media_config != module_config:
                logging.info(f"Change Module {mid}'s media to: {module_config.name}")
                await module.media.set(media_config=module_config)
                resp = await module.media.get()
                logging.info(f"Module {mid}'s new media: {resp.media_config.name}")
            else:
                logging.info(f"Module {mid}'s media: no change")

            # Change module's port config
            resp = await module.cfp.config.get()
            logging.info(f"Module {mid}'s current port count x speed: {resp.portspeed_list}")
            port_count = m_item["port count"]
            port_speed = m_item["port speed"]
            
            speeds = [port_count]
            speeds.extend([port_speed]*port_count)
            if resp.portspeed_list != speeds:
                logging.info(f"Change Module {mid}'s port count x speed to: {port_count}x{int(port_speed/1000)}G")
                await module.cfp.config.set(portspeed_list=speeds)
                resp = await module.cfp.config.get()
                logging.info(f"Module {mid}'s new port count x speed: {resp.portspeed_list}")
            else:
                logging.info(f"Module {mid}'s port count x speed: no change")

            logging.info(f"==================================")
            logging.info(f"{'MODULE CLOCK CONFIG'}")
            logging.info(f"==================================")
            # timing configuration
            timing_source = m_item["timing source"]
            local_clock_adjustment_ppm = m_item["local clock adjustment ppm"]
            await module.timing.source.set(source=timing_source)
            await module.timing.clock_local_adjust.set(ppb=local_clock_adjustment_ppm*1000)
            logging.info(f"Module {mid}'s timing source: {timing_source.name}")
            logging.info(f"Module {mid}'s local clock adjustment: {local_clock_adjustment_ppm} ppm")
        
        logging.info(f"==================================")
        logging.info(f"{'PORT CONFIG'}")
        logging.info(f"==================================")

        _module_object_list = []
        _port_object_list = []
        for m_item in CONFIG_DATA:
            # access module on the tester
            mid = m_item["mid"]
            module = tester.modules.obtain(mid)
            _module_object_list.append(module)

            if not isinstance(module, modules.Z400ThorModule):
                logging.info(f"Module {mid} is not a Thor module")
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
                logging.info(f"Set Port {mid}/{pid} to {fec_mode.name}")

                # loopback mode
                await port.loop_back.set_none()

                # ANLT configuration
                logging.info(f"==================================")
                logging.info(f"{'ANLT CONFIG'}")
                logging.info(f"==================================")
                should_an = p_item["autoneg"]
                should_lt = p_item["link training"]
                logging.info(f"{mid}/{pid}: Autoneg: {should_an}, Link Training: {should_lt}")
                
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
                    logging.info("Thor doesn't support Autoneg-only mode.")
                
                logging.info(f"==================================")
                logging.info(f"{'STREAM CONFIG'}")
                logging.info(f"==================================")
                for s_item in p_item["streams"]:
                    # Create the stream on the port
                    logging.info(f"Create a stream on port {mid}/{pid}")
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
                    
                    eth = headers.Ethernet()                    
                    eth.dst_mac = dst_mac
                    eth.src_mac = src_mac
                    eth.ethertype = headers.EtherType.IPv4

                    ip = headers.IPV4()
                    ip.src = src_ip
                    ip.dst = dst_ip

                    logging.info(f"{'  Index:':<20}{stream.idx}")
                    logging.info(f"{'  DMAC:':<20}{dst_mac}")
                    logging.info(f"{'  SMAC:':<20}{src_mac}")
                    logging.info(f"{'  Dest IP:':<20}{dst_ip}")
                    logging.info(f"{'  Src  IP:':<20}{src_ip}")
                    logging.info(f"{'  Rate:':<20}{stream_rate_pct}%")
                    logging.info(f"{'  Frame Size Type:':<20}{frame_size_type.name} bytes")
                    logging.info(f"{'  Frame Size (min):':<20}{frame_size_min} bytes")
                    logging.info(f"{'  Frame Size (max):':<20}{frame_size_max} bytes")
                    logging.info(f"{'  Payload Pattern:':<20}{payload_pattern}")
                    logging.info(f"{'  TPLD ID:':<20}{tpld_id}")

                    await utils.apply(
                        stream.enable.set_on(),
                        stream.packet.limit.set(packet_count=frame_count),
                        stream.comment.set(f"Test stream"),
                        stream.rate.fraction.set(stream_rate_ppm=int(1000000*(stream_rate_pct/100))),
                        # stream.rate.pps.set(stream_rate_pps=stream_rate_fps),  
                        stream.packet.header.protocol.set(segments=[
                            enums.ProtocolOption.ETHERNET,
                            enums.ProtocolOption.IP]),
                        stream.packet.header.data.set(hex_data=Hex(str(eth)+str(ip))),
                        stream.packet.length.set(length_type=frame_size_type, min_val=frame_size_min, max_val=frame_size_max),
                        stream.payload.content.set(payload_type=enums.PayloadType.PATTERN, hex_data=Hex(payload_pattern)),
                        stream.tpld_id.set(test_payload_identifier = tpld_id),
                        stream.insert_packets_checksum.set_on(),
                    )
                

        logging.info(f"==================================")
        logging.info(f"{'TRAFFIC CONTROL'}")
        logging.info(f"==================================")
        for port in _port_object_list:
            logging.info(f"Clear port {port.kind.module_id}/{port.kind.port_id} RX & TX counters")
            await utils.apply(
                port.statistics.rx.clear.set(),
                port.statistics.tx.clear.set()
            )

        logging.info(f"Traffic duration: {duration} seconds")
        for port in _port_object_list:
            logging.info(f"Start traffic on Port {port.kind.module_id}/{port.kind.port_id}")
            await port.traffic.state.set_start()
        
        await asyncio.sleep(duration)

        for port in _port_object_list:
            logging.info(f"Stop traffic on Port {port.kind.module_id}/{port.kind.port_id}")
            await port.traffic.state.set_stop()

        # cool down
        logging.info(f"Cooling down: {cool_down} seconds")
        await asyncio.sleep(cool_down)

        for port in _port_object_list:
            logging.info(f"Read port {port.kind.module_id}/{port.kind.port_id} RX & TX counters")
            _tx, _rx = await utils.apply(
                port.statistics.tx.total.get(),
                port.statistics.rx.total.get(),
            )
            logging.info(f"==================================")
            logging.info(f"{'TRAFFIC STATS'}")
            logging.info(f"==================================")
            logging.info(f"{'TX FRAMES:':<20}{_tx.packet_count_since_cleared}")
            logging.info(f"{'RX FRAMES:':<20}{_rx.packet_count_since_cleared}")
            logging.info(f"{'TX BYTES:':<20}{_tx.byte_count_since_cleared}")
            logging.info(f"{'RX BYTES:':<20}{_rx.byte_count_since_cleared}")

        for module in _module_object_list:
            await mgmt.free_module(module=module, should_free_ports=True)
        
        logging.info(f"==================================")
        logging.info(f"{'DONE'}")
        logging.info(f"==================================")




async def main():
    stop_event = asyncio.Event()
    try:
        await thor_ppm_anlt_stream(CHASSIS_IP, USERNAME, TRAFFIC_DURATION, COOL_DOWN)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())