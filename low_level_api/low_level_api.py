################################################################
#
#                   XOA LOW-LEVEL API
#
# This script shows you how to use the low-level API
#
################################################################

import asyncio
from xoa_driver import utils
from xoa_driver.lli import commands as cmd
from xoa_driver.lli import TransportationHandler
from xoa_driver.lli import establish_connection
from xoa_driver import enums

#---------------------------
# GLOBAL PARAMS
#---------------------------

CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "xoa"
PORT = "3/0"

TRAFFIC_DURATION = 10 # seconds

#---------------------------
# statistics_background_task
#---------------------------
async def statistics_background_task(
        handler: TransportationHandler,
        module_id: int,
        port_id: int,
        stream_id: int,
        duration: int,
        stop_event: asyncio.Event):
    count = 0
    while not stop_event.is_set():
        print(await cmd.PT_STREAM(handler, module_id, port_id, stream_id).get()) # port 0/0, stream[0]
        print(await cmd.PR_TPLDTRAFFIC(handler, module_id, port_id, stream_id).get()) # # port 0/1, stream [0]
        count+=1
        await asyncio.sleep(1)
    if count >= duration:
        stop_event.set()

#---------------------------
# low_level
#---------------------------
async def low_level(chassis: str, username: str, port_str: str, duration: int, stop_event: asyncio.Event):
    # Connect to chassis                            
    handler = TransportationHandler(enable_logging=False)
    await establish_connection(handler, host=chassis, port=22606)
    await utils.apply(
        cmd.C_LOGON(handler).set("xena"),
        cmd.C_OWNER(handler).set(username),
    )

    # module id and port id
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])

    # Get module port count                   
    resp = await cmd.M_PORTCOUNT(handler, _mid).get()
    print(resp.port_count)

    # Check if 10G is supported on port 
    resp = await cmd.P_SPEEDS_SUPPORTED(handler, _mid, _pid).get()
    print(resp.f10G)

    # Reserve port 
    resp = await cmd.P_RESERVATION(handler, _mid, _pid).get()
    if resp.status == enums.ReservedStatus.RESERVED_BY_OTHER:
        await cmd.P_RESERVATION(handler, _mid, _pid).set(enums.ReservedAction.RELINQUISH)
    if resp.status == enums.ReservedStatus.RESERVED_BY_YOU:
        await cmd.P_RESERVATION(handler, _mid, _pid).set(enums.ReservedAction.RELEASE)
    await cmd.P_RESERVATION(handler, _mid, _pid).set(enums.ReservedAction.RESERVE)

    # Set comment for port
    await cmd.P_COMMENT(handler, _mid, _pid).set(comment="My Port")

    # Create a stream on port
    await cmd.PS_CREATE(handler, _mid, _pid, 0).set()
    await cmd.PS_PACKETLENGTH(handler,_mid, _pid, 0).set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000)

    # Start traffic on port
    await cmd.P_TRAFFIC(handler, _mid, _pid,).set(on_off=enums.StartOrStop.START)

    # Collect statistics in background
    asyncio.create_task(statistics_background_task(handler, _mid, _pid, 0, duration, stop_event)) # put function to work in the background
    await stop_event.wait()
    
    # Stop traffic on port
    await cmd.P_TRAFFIC(handler, _mid, _pid,).set(on_off=enums.StartOrStop.STOP)

    # Release port
    await cmd.P_RESERVATION(handler, _mid, _pid).set(enums.ReservedAction.RELEASE)

async def main():
    stop_event = asyncio.Event()
    try:
        await low_level(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            duration=TRAFFIC_DURATION,
            stop_event=stop_event
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())