import asyncio
from xoa_driver import utils
from xoa_driver.lli import commands as cmd
from xoa_driver.lli import TransportationHandler
from xoa_driver.lli import establish_connection
from xoa_driver import enums

async def background_task(handler: TransportationHandler):
    while True:
        print(await cmd.PT_STREAM(handler, 0, 0, 0).get()) # port 0/0, stream[0]
        print(await cmd.PR_TPLDTRAFFIC(handler, 0, 1, 0).get()) # # port 0/1, stream [0]
        await asyncio.sleep(1)

async def my_awesome_func():
    ##################################################
    #  Connect to chassis 1                          #
    ##################################################
    handler = TransportationHandler(enable_logging=False)
    await establish_connection(handler, host="192.168.1.198", port=22606)
    await utils.apply(
        cmd.C_LOGON(handler).set("xena"),
        cmd.C_OWNER(handler).set("xoa"),
    ) # establish connection using username "xoa".

    ##################################################
    #  Connect to chassis 2                          #
    ##################################################
    handler2 = TransportationHandler(enable_logging=False)
    await establish_connection(handler2, host="192.168.1.198", port=22606)
    await utils.apply(
        cmd.C_LOGON(handler2).set("xena"),
        cmd.C_OWNER(handler2).set("Alice"),
    ) # establish connection using username "Alice".

    ##################################################
    #  Connect to chassis 3                          #
    ##################################################
    handler3 = TransportationHandler(enable_logging=False)
    await establish_connection(handler3, host="192.168.1.198", port=22606)
    await utils.apply(
        cmd.C_LOGON(handler3).set("xena"),
        cmd.C_OWNER(handler3).set("Bob"),
    ) # establish connection using username "Bob".

    ##################################################
    #  Get module 0/1/2 port count                   #
    ##################################################
    resp = await cmd.M_PORTCOUNT(handler, 0).get()
    print(resp.port_count) # get test module 0 port count
    resp = await cmd.M_PORTCOUNT(handler, 1).get()
    print(resp.port_count) # get test module 1 port count
    resp = await cmd.M_PORTCOUNT(handler, 2).get()
    print(resp.port_count) # get test module 2 port count

    ##################################################
    #  Check if 10G is supported on port 0/0 and 0/1 #
    ##################################################
    resp = await cmd.P_SPEEDS_SUPPORTED(handler, 0, 0).get()
    print(resp.f10G)
    resp = await cmd.P_SPEEDS_SUPPORTED(handler, 0, 1).get()
    print(resp.f10G)

    ##################################################
    #  Reserve port 0/0                              #
    ##################################################
    resp = await cmd.P_RESERVATION(handler, 0, 0).get() # port 0/0
    if resp.status == enums.ReservedStatus.RESERVED_BY_OTHER:
        await cmd.P_RESERVATION(handler, 0, 0).set(enums.ReservedAction.RELINQUISH)
    if resp.status == enums.ReservedStatus.RESERVED_BY_YOU:
        await cmd.P_RESERVATION(handler, 0, 0).set(enums.ReservedAction.RELEASE)
    await cmd.P_RESERVATION(handler, 0, 0).set(enums.ReservedAction.RESERVE)

    ##################################################
    #  Set comment for port 0/0                      #
    ##################################################
    await cmd.P_COMMENT(handler, 0, 0).set(comment="My Port")

    ##################################################
    #  Create a stream on port 0/0                   #
    ##################################################
    await cmd.PS_CREATE(handler,0,0,0).set()
    await cmd.PS_PACKETLENGTH(handler,0,0,0).set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000)

    ##################################################
    #  Start traffic on port 0/0                     #
    ##################################################
    await cmd.P_TRAFFIC(handler,0,0).set(on_off=enums.StartOrStop.START)

    ##################################################
    #  Collect statistics in background              #
    ##################################################
    asyncio.create_task(background_task(handler)) # put function to work in the background
    print("Task working in background")

def main():
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(my_awesome_func())
        loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()