################################################################
#
#        Z800 FREYA - FROM ANLT INTO TRAFFIC GENERATION
#
# This script show you how to starts AN/LT and upon successful 
# completion of LT, creates a single x ms link flap. 
# 

#
################################################################

import asyncio
from xoa_driver import testers, modules, ports, enums, utils
from typing import Generator, Optional, Union, List, Dict, Any
from xoa_driver.hlfuncs import mgmt, anlt
from xoa_driver.lli import commands
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "XOA"
TCP_PORT = 22606
PASSWORD = "xena"
PRINT_COMMUNICATION_TRACE = False

TEST_PORT = "3/0"


#---------------------------
# anlt_to_trafficgen
#---------------------------
async def anlt_to_trafficgen(
        chassis_ip: str, 
        username: str,
        port_str: str,
        tcp_port: int = 22606,
        password: str = "xena",
        print_communication_trace: bool = False,):

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="anlt_to_trafficgen.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Xena tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis_ip, username=username, password=password, port=tcp_port, enable_logging=print_communication_trace) as tester:

        # Access module
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)
        if not isinstance(module_obj, modules.Z800FreyaModule):
            logging.info(f"The module must be a Xena Z800 Freya module")
            logging.info(f"Abort")
            return None

        # Get the port
        port_obj = module_obj.ports.obtain(_pid)

        await mgmt.reserve_port(port_obj, reset=True)
        logging.info(f"Port {port_obj.kind.module_id}/{port_obj.kind.port_id} is reserved")
        
        logging.info(f"Port {port_obj.kind.module_id}/{port_obj.kind.port_id} is reset")

        # Read serdes lane count from port
        resp = await port_obj.capabilities.get()
        _serdes_cnt = resp.serdes_count
        logging.info(f"Port {port_obj.kind.module_id}/{port_obj.kind.port_id} has {_serdes_cnt} serdes lanes")

        # Configure AN_LT
        logging.info(f"Configuring AN/LT on port {port_obj.kind.module_id}/{port_obj.kind.port_id}")
        # Enable autorestart when link down or LT failed
        await port_obj.l1.anlt.autorestart.set(values=[enums.FreyaAutorestartMode.WHEN_LINK_DOWN_LT_FAILED])
        logging.info(f"  Enable autorestart when link down or LT failed")
        # Disallow AN if in loopback
        await port_obj.l1.anlt.allow_an_loopback.set(values=[enums.OnOff.OFF])
        logging.info(f"  Disallow AN if in loopback")
        # Disable Empty NP for Autoneg
        await port_obj.l1.anlt.send_empty_np.set(values=[enums.OnOff.OFF])
        logging.info(f"  Disable Empty NP for Autoneg")
        # Enable LT timeout & out-of-sync preset to IEEE
        await port_obj.l1.anlt.lt_config.set(oos_preset=enums.FreyaOutOfSyncPreset.IEEE, timeout_mode=enums.TimeoutMode.DEFAULT)
        logging.info(f"  Enable LT timeout & Set out-of-sync preset to IEEE")
        # Check port's supported technology abilities
        resp = await port_obj.l1.anlt.an.abilities.get()
        _supported_ta = resp.tech_abilities_supported
        # Check port's supported FEC abilities
        resp = await port_obj.l1.anlt.an.abilities.get()
        _supported_fec = resp.fec_modes_supported
        # Check port's supported PAUSE modes
        resp = await port_obj.l1.anlt.an.abilities.get()
        _supported_pause = resp.pause_modes_supported
        # Configure AUTONEG advertised technology abilities
        await port_obj.l1.anlt.an.config.set(advertised_tech_abilities=_supported_ta, advertised_fec_abilities=_supported_fec, advertised_pause_mode=_supported_pause)
        logging.info(f"  Configure AUTONEG advertised technology abilities, FEC capabilities and PAUSE modes")

        # Start AN_LT on all serdes
        await port_obj.l1.anlt.ctrl.enable_an_lt_auto()
        logging.info(f"AN/LT started on port {port_obj.kind.module_id}/{port_obj.kind.port_id}")

        # Wait for AN_GOOD for 2 seconds. If AN_GOOD is not detected, abort the test
        _timeout = 0
        _interval = 0.1
        _max_timeout = 20
        while True:
            resp = await port_obj.l1.anlt.an.status.get()
            if resp.autoneg_state == enums.AutoNegStatus.AN_GOOD:
                logging.info(f"AN_GOOD detected after {_timeout*_interval} seconds")
                break
            else:
                await asyncio.sleep(_interval)
                _timeout += 1
                if _timeout == _max_timeout:
                    logging.info(f"AN_GOOD not detected after {_max_timeout*_interval} seconds. Abort")
                    await abort_anlt(port_obj)
                    return None

        # Wait for success LT on all serdes
        _timeout = 0
        _interval = 0.1
        _max_timeout = 50
        _tokens = []
        for i in range(_serdes_cnt):
            _tokens.append(port_obj.l1.serdes[i].lt.status.get())
        while True:
            resps = await utils.apply(*_tokens)
            _lt_status = [resp.status for resp in resps]
            if enums.LinkTrainingStatus.NOT_TRAINED in _lt_status:
                await asyncio.sleep(_interval)
                _timeout += 1
                if _timeout == _max_timeout:
                    logging.info(f"Link Training unsuccessful after {_max_timeout*_interval} seconds. Abort")
                    await abort_anlt(port_obj)
                    return None
            else:
                logging.info(f"Link Training successful after {_timeout*_interval} seconds")
                break

        # Turn off ANLT
        await port_obj.l1.anlt.ctrl.disable_anlt()
        logging.info(f"AN/LT stopped on port {port_obj.kind.module_id}/{port_obj.kind.port_id}")

        # Do a link flap
        _downtime_ms = 10
        _uptime_ms = 10
        _repeat = 1
        await port_obj.pcs_pma.link_flap.params.set(duration=_downtime_ms, period=_downtime_ms+_uptime_ms, repetition=_repeat)
        await port_obj.pcs_pma.link_flap.enable.set_on()
        logging.info(f"Link flap ({_downtime_ms}ms down/{_uptime_ms}ms up) started on port {port_obj.kind.module_id}/{port_obj.kind.port_id}")




#---------------------------
# abort_anlt
#---------------------------
async def abort_anlt(port_obj: ports.Z800FreyaPort):
    await port_obj.l1.anlt.ctrl.disable_anlt()

# Autoneg technology abilities enums
from enum import Flag
class AutonegTechAbilities(Flag):
    _800G_ETC_CR8_KR8 = 0x0000000020000000
    _400G_ETC_CR8_KR8 = 0x0000000010000000
    _50G_ETC_CR2 =      0x0000000008000000
    _50G_ETC_KR2 =      0x0000000004000000
    _25G_ETC_CR =       0x0000000002000000
    _25G_ETC_KR =       0x0000000001000000
    _1P6TBASE_CR8_KR8 = 0x0000000000800000
    _800GBASE_CR4_KR4 = 0x0000000000400000
    _400GBASE_CR2_KR2 = 0x0000000000200000
    _200GBASE_CR1_KR1 = 0x0000000000100000
    _800GBASE_CR8_KR8 = 0x0000000000080000
    _400GBASE_CR4_KR4 = 0x0000000000040000
    _200GBASE_CR2_KR2 = 0x0000000000020000
    _100GBASE_CR1_KR1 = 0x0000000000010000
    _200GBASE_CR4_KR4 = 0x0000000000008000
    _100GBASE_CR2_KR2 = 0x0000000000004000
    _50GBASE_CR_KR =    0x0000000000002000
    _5GBASE_KR =        0x0000000000001000
    _2P5GBASE_KX =      0x0000000000000800
    _25GBASE_CR_KR =    0x0000000000000400
    _25GBASE_CRS_KRS =  0x0000000000000200
    _100GBASE_CR4 =     0x0000000000000100
    _100GBASE_KR4 =     0x0000000000000080
    _100GBASE_KP4 =     0x0000000000000040
    _100GBASE_CR10 =    0x0000000000000020
    _40GBASE_CR4 =      0x0000000000000010
    _40GBASE_KR4 =      0x0000000000000008
    _10GBASE_KR =       0x0000000000000004
    _10GBASE_KX4 =      0x0000000000000002
    _1000BASE_KX =      0x0000000000000001



async def main():
    stop_event = asyncio.Event()
    try:
        await anlt_to_trafficgen(
            chassis_ip=CHASSIS_IP,
            username=USERNAME,
            port_str=TEST_PORT,
            tcp_port=TCP_PORT,
            password=PASSWORD,
            print_communication_trace=PRINT_COMMUNICATION_TRACE
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())