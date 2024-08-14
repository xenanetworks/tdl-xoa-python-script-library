################################################################
#
#                   OPTIMAL CABLE PERFORMANCE
# 
# This script uses exhaustive search to measure the PRBS BER on 
# each transceiver cursor value combination. At the end, all 
# results are sorted based on PRBS BER value with the best one 
# on the top.
#
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
TX_PORT= "3/0"
RX_PORT = "6/0"
LANE = 1
USERNAME = "xoa"
AMP_MIN = 0
AMP_MAX = 7
PRE_MIN = 0
PRE_MAX = 7
POST_MIN = 0
POST_MAX= 7
DELAY_AFTER_RESET = 2
DELAY_AFTER_EQ_WRITE = 2
PRBS_DURATION = 5

#---------------------------
# cable_perf_optimal
#---------------------------
async def cable_perf_optimal(chassis_ip: str, tx_port: str, rx_port: str, lane: int, username: str, amp_min: int, amp_max: int, pre_min: int, pre_max: int, post_min: int, post_max: int, delay_after_reset: int, delay_after_eq_write: int, prbs_duration: int):

    # configure basic logger
    logger = logging.getLogger("cable_perf_optimal")
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="cable_perf_optimal.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # get module indices and port indices
    _mid_0 = int(tx_port.split("/")[0])
    _pid_0 = int(tx_port.split("/")[1])
    _mid_1 = int(rx_port.split("/")[0])
    _pid_1 = int(rx_port.split("/")[1])

    # validate inputs
    if not 1<=lane<=8:
        logger.warning(f"Lane must in range[1,8]")
        return
    if amp_min > amp_max:
        logger.warning(f"Amplitude range error! You entered min ({amp_min}) > max ({amp_max}).")
        return
    if pre_min > pre_max:
        logger.warning(f"PreCursor range error! You entered min ({pre_min}) > max ({pre_max}).")
        return
    if post_min > post_max:
        logger.warning(f"PostCursor range error! You entered min ({post_min}) > max ({post_max}).")
        return
    if amp_max > 7 or pre_max > 7 or post_max > 7:
        logger.warning(f"Max > 7 error! amp_max: {amp_max}, pre_max: {pre_max}, post_max: {post_max}")
        return
    if amp_min < 0 or pre_min < 0 or post_min < 0:
        logger.warning(f"Min < 0 error! amp_min: {amp_min}, pre_min: {pre_min}, post_min: {post_min}")
        return

    logger.info(f"#####################################################################")
    logger.info(f"Chassis:              {chassis_ip}")
    logger.info(f"Username:             {username}")
    logger.info(f"PRBS TX Port:         {tx_port}")
    logger.info(f"PRBS RX Port:         {rx_port}")
    logger.info(f"Lane:                 {lane}")
    logger.info(f"Amplitude Range:      [{amp_min}, {amp_max}] dB")
    logger.info(f"PreCursor Range:      [{pre_min}, {pre_max}] dB")
    logger.info(f"PostCursor Range:     [{post_min}, {post_max}] dB")
    logger.info(f"Delay After Reset:    {delay_after_reset} seconds")
    logger.info(f"Delay After EQ Write: {delay_after_eq_write} seconds")
    logger.info(f"PRBS Duration:        {prbs_duration} seconds")
    logger.info(f"#####################################################################")

    # connect to the tester and automatically disconnect when ended
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:
    
        # access module on the tester
        module_obj_0 = tester_obj.modules.obtain(_mid_0)
        module_obj_1 = tester_obj.modules.obtain(_mid_1)

        # the module must be a freya module
        if not isinstance(module_obj_0, modules.Z800FreyaModule):
            logger.warning(f"Port {tx_port} is not a Freya port. Abort")
            return None
        if not isinstance(module_obj_1, modules.Z800FreyaModule):
            logger.warning(f"Port {rx_port} is not a Freya port. Abort")
            return None
        
        # get the port object
        tx_port_obj = module_obj_0.ports.obtain(_pid_0)
        rx_port_obj = module_obj_1.ports.obtain(_pid_1)

        # reserve the port and reset the port
        await mgmt.free_module(module_obj_0, should_free_ports=True)
        await mgmt.reserve_port(tx_port_obj)
        await mgmt.reset_port(tx_port_obj)
        await mgmt.free_module(module_obj_1, should_free_ports=True)
        await mgmt.reserve_port(rx_port_obj)
        await mgmt.reset_port(rx_port_obj)
        logger.info(f"Delay after reset: {delay_after_reset}s")
        await asyncio.sleep(delay_after_reset)

        # configure prbs
        await tx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=enums.PRBSPolynomial.PRBS31, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
        await rx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=enums.PRBSPolynomial.PRBS31, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

        # start prbs
        _serdes = lane - 1
        await tx_port_obj.serdes[_serdes].prbs.tx_config.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

        # exhaustive search of all cursor combinations
        result = []
        for _amp_db in range(amp_min, amp_max+1):
            for _pre_db in range(pre_min, pre_max+1):
                for _post_db in range(post_min, post_max+1):
                    await output_eq_write(port=rx_port_obj, lane=lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger=logger)
                    await output_eq_write(port=rx_port_obj, lane=lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger=logger)
                    await output_eq_write(port=rx_port_obj, lane=lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger=logger)
                    logger.info(f"Delay after EQ write: {delay_after_eq_write}s")
                    await asyncio.sleep(delay_after_eq_write)

                    # clear counters
                    logger.info(f"Clear PRBS counters")
                    await rx_port_obj.pcs_pma.rx.clear.set()
                    await tx_port_obj.pcs_pma.rx.clear.set()

                    # measure duration
                    logger.info(f"PRBS measure for {prbs_duration}s")
                    await asyncio.sleep(prbs_duration)

                    # read PRBS BER
                    _prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=lane, logger=logger)
                    logger.info(f"Amplitude: {_amp_db} dB, PreCursor: {_pre_db} dB, PostCursor: {_post_db} dB, PRBS BER: {_prbs_ber}")

                    # remember the result
                    result.append({"amp": _amp_db, "pre": _pre_db, "post": _post_db, "prbs_ber": _prbs_ber})
        
        # stop prbs
        _serdes = lane - 1
        await tx_port_obj.serdes[_serdes].prbs.tx_config.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

        # find the best
        sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
        logger.info(f"Final sorted results:")
        for i in sorted_result:
            logger.info(f"Amplitude: {i['amp']} dB, PreCursor: {i['pre']} dB, PostCursor: {i['post']} dB, PRBS BER: {i['prbs_ber']}")
        


if __name__ == "__main__":
    if len(sys.argv) == 10:
        chassis_ip = sys.argv[1]
        tx_port = sys.argv[2]
        rx_port = sys.argv[3]
        lane = int(sys.argv[4])
        username = sys.argv[5]
        amp_min = int(sys.argv[6])
        amp_max = int(sys.argv[7])
        pre_min = int(sys.argv[8])
        pre_max = int(sys.argv[9])
        post_min = int(sys.argv[10])
        post_max = int(sys.argv[11])
        delay_after_reset = int(sys.argv[12])
        delay_after_eq_write = int(sys.argv[13])
        prbs_duration = int(sys.argv[14])
        asyncio.run(cable_perf_optimal(chassis_ip, tx_port, rx_port, lane, username, amp_min, amp_max, pre_min, pre_max, post_min, post_max, delay_after_reset, delay_after_eq_write, prbs_duration))
    elif len(sys.argv) == 1:
        asyncio.run(cable_perf_optimal(CHASSIS_IP, TX_PORT, RX_PORT, LANE, USERNAME, AMP_MIN, AMP_MAX, PRE_MIN, PRE_MAX, POST_MIN, POST_MAX, DELAY_AFTER_RESET, DELAY_AFTER_EQ_WRITE, PRBS_DURATION))
    else:
        print.info(f"Not enough parameters")