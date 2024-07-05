################################################################
#
#                   SIMPLE ARP TABLE
#
# This script show you how to configure ARP table 
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex, ArpChunk
from ipaddress import IPv4Address, IPv6Address
from binascii import hexlify
from xoa_driver.misc import Hex

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "demo.xenanetworks.com"
USERNAME = "simple_arp_table"
PORT = "2/0"

#---------------------------
# simple_arp_table
#---------------------------
async def simple_arp_table(chassis: str, username: str, port_str: str,):
    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module index 0 on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module = tester.modules.obtain(_mid)

        if isinstance(module, modules.E100ChimeraModule):
            return None # commands which used in this example are not supported by Chimera Module

        # Get the port on module 
        port = module.ports.obtain(_pid)

        # Forcibly reserve the TX port and reset it.
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        await asyncio.sleep(5)

        # Configure the port with minimal necessary settings after reset
        await port.comment.set(comment="port with arp table")
        await port.tx_config.enable.set_on()
        # Enable ARP and Ping reply on Port
        await port.net_config.ipv4.arp_reply.set_on()
        await port.net_config.ipv4.ping_reply.set_on()
        # Configure ARP table entry list
        arp_table_entry_list=[]
        arp_table_entry = ArpChunk(
                ipv4_address=IPv4Address("1.1.1.1"),
                prefix=24,
                patched_mac=enums.OnOff.OFF,
                mac_address=Hex("010101010101")
                )
        arp_table_entry_list.append(arp_table_entry)
        # set ARP table for Port
        await port.arp_rx_table.set(chunks=arp_table_entry_list)

        # release port
        await mgmt.free_port(port=port)