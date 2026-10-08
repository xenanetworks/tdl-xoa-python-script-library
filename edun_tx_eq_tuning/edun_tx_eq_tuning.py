################################################################
#
#                   Z1608 EDUN TX TAP TUNING
#
# This script show you how to adjust the TX FEE values on Z1608
# Edun modules.
# 
#
################################################################

import asyncio
from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
import logging

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.20.1.170"
USERNAME = "XOA"
PORT = "0/0"
SERDES = 0
TCP_PORT = 22606
PASSWORD = "xena"

async def edun_tx_tune(
        chassis_ip: str, 
        username: str, 
        serdes_id: int, 
        port_str: str,
        tcp_port: int,
        password: str,):

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis_ip, username=username, password=password, port=tcp_port, enable_logging=False) as tester_obj:

        
        port_obj = await mgmt.obtain_port_by_id(tester=tester_obj, port_id=port_str)
        if not isinstance(port_obj, ports.Z1600EdunPort):
            logging.info(f"The port {port_str} is not an Edun port")
            logging.info(f"Abort")
            return None

        await mgmt.reserve_ports(ports=[port_obj], reset=True)
        

        # Read serdes lane count from port
        resp = await port_obj.capabilities.get()
        _serdes_cnt = resp.serdes_count

        if serdes_id+1>_serdes_cnt:
            logging.info(f"Serdes lane {serdes_id} doesn't exit. There are {_serdes_cnt} serdes lanes on this port.")
            return None

        # set using NATIVE
        
        _pre3 = -3
        _pre2 = 2
        _pre = -1
        _main = 157
        _post = -1
        _post2 = 2
        _sum_of_taps = _pre3 + _pre2 + _pre + _main + _post + _post2
        if _sum_of_taps > 168:
            logging.warning(f"Sum of taps ({_sum_of_taps}) exceeds the maximum allowed value of 168")
            return None
        if _pre > 0 or _post > 0:
            logging.warning(f"Invalid tap values: pre={_pre}, post={_post}. Both should be non-positive.")
            return None
        if _pre3 > 0 or _pre3 < -12:
            logging.warning(f"Invalid tap value: pre3={_pre3}. It should be in the range [-12, 0].")
            return None
        logging.info(f"Write (native): pre3={_pre3}, pre2={_pre2}, pre={_pre}, main={_main}, post={_post}, post2={_post2}")
        
        await port_obj.layer1.serdes[serdes_id].medium.tx.native.set(tap_values=[_pre3, _pre2, _pre, _main, _post, _post2])
        
        # release the port
        await mgmt.release_ports(ports=[port_obj])


async def main():
    stop_event = asyncio.Event()
    try:
        await edun_tx_tune(
            chassis_ip=CHASSIS_IP,
            username=USERNAME,
            serdes_id = SERDES,
            port_str=PORT,
            tcp_port=TCP_PORT,
            password=PASSWORD
            )
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())