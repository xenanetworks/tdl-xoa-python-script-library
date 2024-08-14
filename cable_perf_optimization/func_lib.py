# ***********************************************************************************************
# this library file contains functions for dp init, register rw, prbs ber read, etc.
# ***********************************************************************************************

import asyncio

from xoa_driver import testers, modules, ports, enums
from xoa_driver.misc import Hex
from enums import *
import logging
import math

# *************************************************************************************
# func: stop_auto_dp_init
# description: Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)
# *************************************************************************************
async def stop_auto_dp_init(port: ports.GenericL23Port, logger: logging.Logger):
    """Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)

    :param port: port object
    :type port: ports.GenericL23Port
    :param logger: logger object
    :type logger: logging.Logger
    """
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("FF"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: apply_dp_init
# description: Apply Data Path Init (Write address 143 value 0xFF)
# *************************************************************************************
async def apply_dp_init(port: ports.GenericL23Port, logger: logging.Logger):
    """Apply Data Path Init (Write address 143 value 0xFF)

    :param port: port object
    :type port: ports.GenericL23Port
    :param logger: logger object
    :type logger: logging.Logger
    """
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Apply Data Path Init (Write address 143 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=143, byte_count=1).set(value=Hex("FF"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: activate_dp
# description: Activate Data Path (Write address 128 with value 0x00)
# *************************************************************************************
async def activate_dp(port: ports.GenericL23Port, logger: logging.Logger):
    """Activate Data Path (Write address 128 with value 0x00)

    :param port: port object
    :type port: ports.GenericL23Port
    :param logger: logger object
    :type logger: logging.Logger
    """
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Activate Data Path (Write address 128 with value 0x00)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("00"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: output_eq_write
# description: Write input dB value to a specified cursor on a specified lane
# *************************************************************************************
async def output_eq_write(port: ports.GenericL23Port, lane: int, db: int, cursor: Cursor, logger: logging.Logger):
    """Write input dB value to a specified cursor on a specified lane

    :param port: port object
    :type port: ports.GenericL23Port
    :param lane: transceiver lane, from 1-8
    :type lane: int
    :param db: dB value, from 0-7
    :type db: int
    :param cursor: cursor to adjust
    :type cursor: Cursor
    :param logger: logger object
    :type logger: logging.Logger
    """
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Write {db} dB to {cursor.name} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=db<=7

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = math.ceil(lane/2) + 161 + int(cursor.value*4)
    
    _is_upper_lane = False
    if lane % 2 == 0: # upper lane, value should update bit 7-4
        _is_upper_lane = True

    # read the byte from the address
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    
    if _is_upper_lane: # upper lane, value should update bit 7-4
        _value = db << 4 # move the value 4 bits to the left
        _tmp &= 0x0F # erase bit 7-4
        _tmp |= _value # add the desired value
    else: # lower lane, value should update bit 3-0
        _value = db # the value as is
        _tmp &= 0xF0 # erase bit 3-0
        _tmp |= _value # add the desired value
    
    # write the new byte into the address
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).set(value=Hex('{:02X}'.format(_tmp)))
    await asyncio.sleep(1)

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _is_upper_lane:
        _tmp &= 0xF0 # take the bit 7-4 of the read
        _read = _tmp >> 4
    else:
        _tmp &= 0x0F # take the bit 7-4 of the read
        _read = _tmp
    if _read == db:
        logger.info(f"  Write operation successful")
    else:
        logger.info(f"  Write operation failed. (Wrote {db} dB but read {_read})")

# *************************************************************************************
# func: output_eq_read
# description: Read dB value from a specified cursor on a specified lane
# *************************************************************************************
async def output_eq_read(port: ports.GenericL23Port, lane: int, cursor: Cursor, logger: logging.Logger):
    """Read dB value from a specified cursor on a specified lane

    :param port: port object
    :type port: ports.GenericL23Port
    :param lane: transceiver lane, from 1-8
    :type lane: int
    :param cursor: cursor to adjust
    :type cursor: Cursor
    :param logger: logger object
    :type logger: logging.Logger
    """
    assert 1<=lane<=8

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = math.ceil(lane/2) + 161 + int(cursor.value*4)
    
    _is_upper_lane = False
    if lane % 2 == 0: # upper lane, value should update bit 7-4
        _is_upper_lane = True

    # read the byte from the address
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _is_upper_lane:
        _tmp &= 0xF0 # take the bit 7-4 of the read
        _read = _tmp >> 4
    else:
        _tmp &= 0x0F # take the bit 7-4 of the read
        _read = _tmp
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Read {_read} dB from {cursor.name} - Lane {lane} ")

# *************************************************************************************
# func: app_sel
# description: Write AppSelCode, DataPathID, and ExplicitControl to a specified lane
# *************************************************************************************
async def app_sel(port: ports.GenericL23Port, lane: int, appsel_code: int, dp_id: int, explicit_ctrl: int, logger: logging.Logger):
    """Write AppSelCode, DataPathID, and ExplicitControl to a specified lane

    :param port: port object
    :type port: ports.GenericL23Port
    :param lane: transceiver lane, from 1-8
    :type lane: int
    :param appsel_code: appsel code, from 0-15
    :type appsel_code: int
    :param dp_id: data path id, from 0-7
    :type dp_id: int
    :param explicit_ctrl: explicit control, 0 for false/off, 1 for true/on
    :type explicit_ctrl: int
    :param logger: logger object
    :type logger: logging.Logger
    """
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Write AppSelCode={appsel_code}, DataPathID={dp_id}, ExplicitControl={explicit_ctrl} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=appsel_code<=15
    assert 0<=dp_id<=7
    assert 0<=explicit_ctrl<=1

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = 144 + lane
    _tmp = (appsel_code<<4) + (dp_id<<1) + explicit_ctrl
    
    # write the new byte into the address
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).set(value=Hex('{:02X}'.format(_tmp)))
    await asyncio.sleep(1)

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp2 = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _tmp2 == _tmp:
        logger.info(f"  Write operation successful")
    else:
        logger.info(f"  Write operation failed. (Wrote 0x{_tmp} but read 0x{_tmp2})")

# *************************************************************************************
# func: read_prbs_ber
# description: Read PRBS BER from a specified lane
# *************************************************************************************
async def read_prbs_ber(port: ports.GenericL23Port, lane: int, logger: logging.Logger) -> float:
    """Read PRBS BER from a specified lane. If zero errored bits, the BER is calculated as 4.6/prbs_bits for 99% confidence level.
    Read more in https://www.lightwaveonline.com/home/article/16647704/explaining-those-ber-testing-mysteries

    :param port: Read PRBS BER from a specified lane
    :type port: ports.GenericL23Port
    :param lane: lane, from 1-8
    :type lane: int
    :param logger: logger object
    :type logger: logging.Logger
    :return: PRBS BER
    :rtype: float
    """
    assert 1<=lane<=8
    # read starting PRBS BER
    _prbs_ber = 0.0
    _serdes = lane - 1
    resp = await port.serdes[_serdes].prbs.status.get()
    _prbs_bits = resp.byte_count * 8
    _prbs_errors = resp.error_count
    if _prbs_errors == 0:
        # _prbs_ber = 4.6/_prbs_bits
        _prbs_ber = 0
        logger.info(f"  PRBS BER [{lane}]: < {'{0:.3e}'.format(_prbs_ber)}")
    else:
        _prbs_ber = _prbs_errors/_prbs_bits
        logger.info(f"  PRBS BER [{lane}]: {'{0:.3e}'.format(_prbs_ber)}")
    return _prbs_ber
    
def less_equal(current: float, target:float) -> bool:
    if current <= target:
        return True
    else:
        return False
    
# *************************************************************************************
# func: test_done
# description: Show test result and stop PRBS
# *************************************************************************************
async def test_done(port: ports.GenericL23Port, lane: int, current_ber: float, target_ber: float, amp_db: int, pre_db: int, post_db: int, is_successful: bool, logger: logging.Logger):
    """Show test result and stop PRBS

    :param port: port object
    :type port: ports.GenericL23Port
    :param lane: lane index, 1-8
    :type lane: int
    :param current_ber: current BER
    :type current_ber: float
    :param target_ber: target BER
    :type target_ber: float
    :param amp_db: final amplitude dB
    :type amp_db: int
    :param pre_db: final pre-cursor dB
    :type pre_db: int
    :param post_db: final post-cursor dB
    :type post_db: int
    :param is_successful: flag
    :type is_successful: bool
    """
    logger.info(f"#####################################################################")
    logger.info(f"Lane: {lane}")
    logger.info(f"Current PRBS BER: {'{0:.3e}'.format(current_ber)}, Target PRBS BER: {target_ber}")
    logger.info(f"{'SUCCESS' if is_successful else 'FAILED'}: amp = {amp_db} dB, pre = {pre_db} dB, post = {post_db} dB")
    logger.info(f"#####################################################################")

    # stop PRBS on port
    _serdes = lane - 1
    await port.serdes[_serdes].prbs.tx_config.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)