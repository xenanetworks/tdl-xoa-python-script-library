################################################################
#
#                   STREAM MODIFIER
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve port
# 3. Create a stream
# 4. Add modifiers on the stream
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import utils, enums
from xoa_driver.hlfuncs import mgmt, headers
from xoa_driver.misc import Hex

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "xoa"
PORT = "0/0"

#---------------------------
# modifier
#---------------------------
async def modifier(chassis: str, username: str, port_str: str):
    # create tester instance and establish connection
    my_tester = await testers.L23Tester(chassis, username) 

    # access module on the tester
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = my_tester.modules.obtain(_mid)

    if isinstance(module_obj, modules.E100ChimeraModule):
        return None # commands which used in this example are not supported by Chimera Module

    # access port 0 on the module as the TX port
    port_obj = module_obj.ports.obtain(_pid)

    # use high-level func to reserve the port
    await mgmt.reserve_port(port_obj, reset=True)
    
    # reset the port
    await port_obj.reset.set()

    # create one stream on the port
    my_stream = await port_obj.streams.create()

    eth = headers.Ethernet()
    eth.dst_mac = "0000.0000.0002"
    eth.src_mac = "0000.0000.0001"
    eth.ethertype = headers.EtherType.IPv4

    await utils.apply(
        # Create the TPLD index of stream
        my_stream.tpld_id.set(0), 
        # Configure the packet size
        my_stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000),
        # Enable stream
        my_stream.enable.set_on(), 
        # Configure the stream rate
        my_stream.rate.fraction.set(stream_rate_ppm=500000), 

        # Configure the packet type
        my_stream.packet.header.protocol.set(segments=[enums.ProtocolOption.ETHERNET, enums.ProtocolOption.IP]),
        # Configure the packet header data
        my_stream.packet.header.data.set(hex_data = Hex(str(eth))) 
    )

    # create one modifier and configure
    await my_stream.packet.header.modifiers.configure(1)
    # access the created modifier
    my_modifier = my_stream.packet.header.modifiers.obtain(0)
    # configure the modifier
    # place the modifier on header position 0
    await my_modifier.specification.set(position=0, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1) 
    await my_modifier.range.set(min_val=0, step=1, max_val=65535)

    # to create another modifier, you need to re-configure all modifiers again
    await my_stream.packet.header.modifiers.configure(2)

    my_modifier = my_stream.packet.header.modifiers.obtain(0)
    # place the first modifier on header position 0
    await my_modifier.specification.set(position=0, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1) 
    await my_modifier.range.set(min_val=0, step=1, max_val=65535)

    my_modifier_2 = my_stream.packet.header.modifiers.obtain(1)
    # place the second modifier on header position 6
    await my_modifier_2.specification.set(position=6, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1) 
    await my_modifier_2.range.set(min_val=0, step=1, max_val=65535)

    # to delete the first modifier, you need to re-configure all modifiers again
    await my_stream.packet.header.modifiers.configure(1)
    
    my_modifier = my_stream.packet.header.modifiers.obtain(0)
    # place the modifier on header position 0
    await my_modifier.specification.set(position=6, mask=Hex("FFFF0000"), action=enums.ModifierAction.INC, repetition=1) 
    await my_modifier.range.set(min_val=0, step=1, max_val=65535)

    # to delete all modifiers
    await my_stream.packet.header.modifiers.configure(0)

async def main():
    stop_event = asyncio.Event()
    try:
        await modifier(
            chassis=CHASSIS_IP, 
            username=USERNAME,
            port_str=PORT
        )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())