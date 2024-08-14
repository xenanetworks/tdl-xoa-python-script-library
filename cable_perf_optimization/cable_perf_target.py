################################################################
#
#                   TARGET CABLE PERFORMANCE
#
# This script uses a target value to find the locally optimal 
# transceiver cursor value combination. When the measured 
# PRBS BER value is less that the target, the search will stop.
#
################################################################

import asyncio
import sys

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from func_lib import *
import logging

#---------------------------
# Global parameters
#---------------------------
CHASSIS_IP = "10.165.136.60"
P0 = "3/0"
P1 = "6/0"
LANE = 1
USERNAME = "xoa"
AMP_INIT = 0
PRE_INIT = 0
POST_INIT = 0
TARGET_BER = 1.2e-9
DELAY_AFTER_RESET = 2
DELAY_AFTER_EQ_WRITE = 2

#---------------------------
# cable_perf_target
#---------------------------
async def cable_perf_target(chassis_ip: str, p0: str, p1: str, lane: int, username: str, amp_init: int, pre_init: int, post_init: int, target_ber: float, delay_after_reset: int, delay_after_eq_write: int):
    
    # configure basic logger
    logger = logging.getLogger("cable_perf_target")
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="cable_perf_target.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # get module indices and port indices
    _mid_0 = int(p0.split("/")[0])
    _pid_0 = int(p0.split("/")[1])
    _mid_1 = int(p1.split("/")[0])
    _pid_1 = int(p1.split("/")[1])

    if not 1<=lane<=8:
        logger.warning(f"Lane must in range[1,8]")
        return

    logger.info(f"#####################################################################")
    logger.info(f"Chassis:            {chassis_ip}")
    logger.info(f"Username:           {username}")
    logger.info(f"PRBS TX Port:       {p0}")
    logger.info(f"PRBS RX Port:       {p1}")
    logger.info(f"Lane:               {lane}")
    logger.info(f"Initial Amplitude:   {amp_init} dB")
    logger.info(f"Initial PreCursor:   {pre_init} dB")
    logger.info(f"Initial PostCursor:  {post_init} dB")
    logger.info(f"Target PRBS BER:     {target_ber}")
    logger.info(f"#####################################################################")

    # connect to the tester and automatically disconnect when ended
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:

        # access module on the tester
        module_0 = tester_obj.modules.obtain(_mid_0)
        module_1 = tester_obj.modules.obtain(_mid_1)

        # the module must be a freya module
        if not isinstance(module_0, modules.Z800FreyaModule):
            logger.warning(f"Port {p0} is not a Freya port. Abort")
            return None
        if not isinstance(module_1, modules.Z800FreyaModule):
            logger.warning(f"Port {p1} is not a Freya port. Abort")
            return None
        
        # get the port object
        port_0 = module_0.ports.obtain(_pid_0)
        port_1 = module_1.ports.obtain(_pid_1)

        # reserve the port and reset the port
        await mgmt.free_module(module_0, should_free_ports=True)
        await mgmt.reserve_port(port_0)
        await mgmt.reset_port(port_0)
        await mgmt.free_module(module_1, should_free_ports=True)
        await mgmt.reserve_port(port_1)
        await mgmt.reset_port(port_1)
        await asyncio.sleep(delay_after_reset)

        # configure PRBS on port 0 and port 1
        await port_0.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=enums.PRBSPolynomial.PRBS31, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.PERSECOND)
        await port_1.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=enums.PRBSPolynomial.PRBS31, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.PERSECOND)

        # start PRBS on port 0
        _serdes = lane - 1
        await port_0.serdes[_serdes].prbs.tx_config.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

        # write amp/pre/post to initial dB as a starting point
        _amp_db = amp_init
        _pre_db = pre_init
        _post_db = post_init
        logger.info(f"|----------------------|")
        logger.info(f"|  Initial dB Values   |")
        logger.info(f"|----------------------|")
        await output_eq_write(port=port_1, lane=lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger=logger)
        await output_eq_write(port=port_1, lane=lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger=logger)
        await output_eq_write(port=port_1, lane=lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger=logger)
        await asyncio.sleep(delay_after_eq_write)

        # check if PRBS BER is less equal to target BER
        _current_prbs_ber = await read_prbs_ber(port=port_1, lane=lane, logger=logger)
        if less_equal(_current_prbs_ber, target_ber):
            await test_done(port_0, lane, _current_prbs_ber, target_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger=logger)
            return
        else:
            _prev_prbs_ber = _current_prbs_ber

            # algorithm - adjust amplitude and check PRBS stats on port 1
            logger.info(f"|----------------------|")
            logger.info(f"|   Adjust AMPLITUDE   |")
            logger.info(f"|----------------------|")
            while _amp_db<7:
                _amp_db += 1
                await output_eq_write(port=port_1, lane=lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger=logger)
                await asyncio.sleep(delay_after_eq_write)

                # read the current BER
                _current_prbs_ber = await read_prbs_ber(port=port_1, lane=lane, logger=logger)
                
                # if current BER <= target BER, mark done and finish
                if less_equal(_current_prbs_ber, target_ber):
                    await test_done(port_0, lane, _current_prbs_ber, target_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger=logger)
                    return
                # if target BER < current BER <= prev BER, continue the searching
                elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                    _prev_prbs_ber = _current_prbs_ber
                    continue
                # if current BER > prev BER, roll back and move on to pre-cursor
                else:
                    _amp_db -= 1
                    await output_eq_write(port=port_1, lane=lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger=logger)
                    break
            await asyncio.sleep(delay_after_eq_write)

            # algorithm - adjust pre-cursor and check PRBS stats on port 1
            logger.info(f"|----------------------|")
            logger.info(f"|   Adjust PRE-CURSOR  |")
            logger.info(f"|----------------------|")
            while _pre_db<7:
                _pre_db += 1
                await output_eq_write(port=port_1, lane=lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger=logger)
                await asyncio.sleep(delay_after_eq_write)

                # read the current BER
                _current_prbs_ber = await read_prbs_ber(port=port_1, lane=lane, logger=logger)
                
                # if current BER <= target BER, mark done and finish
                if less_equal(_current_prbs_ber, target_ber):
                    await test_done(port_0, lane, _current_prbs_ber, target_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger=logger)
                    return
                # if target BER < current BER <= prev BER, continue the searching
                elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                    _prev_prbs_ber = _current_prbs_ber
                    continue
                # if current BER > prev BER, roll back and move on to pre-cursor
                else:
                    _pre_db -= 1
                    await output_eq_write(port=port_1, lane=lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger=logger)
                    break
            await asyncio.sleep(delay_after_eq_write)

            # algorithm - adjust post-cursor and check PRBS stats on port 1
            logger.info(f"|----------------------|")
            logger.info(f"|  Adjust POST-CURSOR  |")
            logger.info(f"|----------------------|")
            while _post_db<7:
                _post_db += 1
                await output_eq_write(port=port_1, lane=lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger=logger)
                await asyncio.sleep(delay_after_eq_write)

                # read the current BER
                _current_prbs_ber = await read_prbs_ber(port=port_1, lane=lane, logger=logger)
                
                # if current BER <= target BER, mark done and finish
                if less_equal(_current_prbs_ber, target_ber):
                    await test_done(port_0, lane, _current_prbs_ber, target_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger=logger)
                    return
                # if target BER < current BER <= prev BER, continue the searching
                elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                    _prev_prbs_ber = _current_prbs_ber
                    continue
                # if current BER > prev BER, roll back and move on to pre-cursor
                else:
                    _post_db -= 1
                    await output_eq_write(port=port_1, lane=lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger=logger)
                    break
            await asyncio.sleep(delay_after_eq_write)

            # searching failed
            # read the current BER
            _current_prbs_ber = await read_prbs_ber(port=port_1, lane=lane, logger=logger)
            await test_done(port_0, lane, _current_prbs_ber, target_ber, _amp_db, _pre_db, _post_db, is_successful=False, logger=logger)


if __name__ == "__main__":
    if len(sys.argv) == 10:
        chassis_ip = sys.argv[1]
        p0 = sys.argv[2]
        p1 = sys.argv[3]
        lane = int(sys.argv[4])
        username = sys.argv[5]
        amp_init = int(sys.argv[6])
        pre_init = int(sys.argv[7])
        post_init = int(sys.argv[8])
        target_ber = float(sys.argv[9])
        delay_after_reset = int(sys.argv[10])
        delay_after_eq_write = int(sys.argv[11])
        asyncio.run(cable_perf_target(chassis_ip, p0, p1, lane, username, amp_init, pre_init, post_init, target_ber, delay_after_reset, delay_after_eq_write))
    elif len(sys.argv) == 1:
        asyncio.run(cable_perf_target(CHASSIS_IP, P0, P1, LANE, USERNAME, AMP_INIT, PRE_INIT, POST_INIT, TARGET_BER, DELAY_AFTER_RESET,DELAY_AFTER_EQ_WRITE))
    else:
        print(f"Not enough parameters")