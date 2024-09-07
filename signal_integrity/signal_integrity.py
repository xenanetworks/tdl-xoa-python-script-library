################################################################
#
#              SIGNAL INTEGRITY HISTOGRAM PLOTTING
#
# What this script example does:
# 1. Connect to a tester
# 2. Reserve a port. 
# 3. Collecting SIV data from all 8 lanes
# 4. Plot the live histogram 
#
################################################################

import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import logging

import matplotlib.pyplot as plt
from collections import deque

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "10.165.136.60"
USERNAME = "xoa"
PORT = "3/0"
FIGURE_TITLE = "Signal Integrity Histogram View"
DENSITY = 1 # how many batches of siv data to show on the plot. A higher density means more data and slower plotting.

async def siv_plot(
        chassis: str, 
        username: str, 
        port_str: str,
        figure_title: str,
        density: int):
    
    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="siv_plot.log", mode="a"),
            logging.StreamHandler()]
        )
    
    async with testers.L23Tester(host=chassis, username=username, password="xena", port=22606, enable_logging=False) as tester:
        logging.info(f"#####################################################################")
        logging.info(f"Chassis:                 {chassis}")
        logging.info(f"Username:                {username}")
        logging.info(f"Port:                    {port_str}")

        # Access module on the tester
        _mid = int(port_str.split("/")[0])
        _pid = int(port_str.split("/")[1])
        module_obj = tester.modules.obtain(_mid)

        if not isinstance(module_obj, modules.Z800FreyaModule):
            logging.info(f"Module {_mid} is not Z800 Freya module. Abort.")
            return None
        
        port_obj = module_obj.ports.obtain(_pid)
        await mgmt.free_module(module=module_obj, should_free_ports=False)
        await mgmt.reserve_port(port_obj)

        # figure config
        plt.ion()
        fig = plt.figure(constrained_layout=True)
        fig.suptitle(f"{figure_title} d={density}")
        gs = fig.add_gridspec(nrows=4, ncols=2)
        siv0 = fig.add_subplot(gs[0, 0])  # siv for lane 0
        siv1 = fig.add_subplot(gs[1, 0])  # siv for lane 1
        siv2 = fig.add_subplot(gs[2, 0])  # siv for lane 2
        siv3 = fig.add_subplot(gs[3, 0])  # siv for lane 3
        siv4 = fig.add_subplot(gs[0, 1])  # siv for lane 4
        siv5 = fig.add_subplot(gs[1, 1])  # siv for lane 5
        siv6 = fig.add_subplot(gs[2, 1])  # siv for lane 6
        siv7 = fig.add_subplot(gs[3, 1])  # siv for lane 7

        h0 = ()
        h1 = ()
        h2 = ()
        h3 = ()
        h4 = ()
        h5 = ()
        h6 = ()
        h7 = ()
        
        DATA_PER_BATCH = 2000
        data0 = deque(h0, maxlen=density*DATA_PER_BATCH)
        data1 = deque(h1, maxlen=density*DATA_PER_BATCH)
        data2 = deque(h2, maxlen=density*DATA_PER_BATCH)
        data3 = deque(h3, maxlen=density*DATA_PER_BATCH)
        data4 = deque(h4, maxlen=density*DATA_PER_BATCH)
        data5 = deque(h5, maxlen=density*DATA_PER_BATCH)
        data6 = deque(h6, maxlen=density*DATA_PER_BATCH)
        data7 = deque(h7, maxlen=density*DATA_PER_BATCH)

        siv0.set(xlabel=f"Value", ylabel=f"Lane 0")
        siv1.set(xlabel=f"Value", ylabel=f"Lane 1")
        siv2.set(xlabel=f"Value", ylabel=f"Lane 2")
        siv3.set(xlabel=f"Value", ylabel=f"Lane 3")
        siv4.set(xlabel=f"Value", ylabel=f"Lane 4")
        siv5.set(xlabel=f"Value", ylabel=f"Lane 5")
        siv6.set(xlabel=f"Value", ylabel=f"Lane 6")
        siv7.set(xlabel=f"Value", ylabel=f"Lane 7")

        n = 0
        while True:
            print(f"control {n}")
            await utils.apply(
                port_obj.l1.serdes[0].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[1].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[2].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[3].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[4].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[5].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[6].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
                port_obj.l1.serdes[7].medium.siv.control.set(opcode=enums.Layer1Opcode.START_SCAN),
            )
            while True:
                resp0, resp1, resp2, resp3, resp4, resp5, resp6, resp7 = await utils.apply(
                    port_obj.l1.serdes[0].medium.siv.data.get(),
                    port_obj.l1.serdes[1].medium.siv.data.get(),
                    port_obj.l1.serdes[2].medium.siv.data.get(),
                    port_obj.l1.serdes[3].medium.siv.data.get(),
                    port_obj.l1.serdes[4].medium.siv.data.get(),
                    port_obj.l1.serdes[5].medium.siv.data.get(),
                    port_obj.l1.serdes[6].medium.siv.data.get(),
                    port_obj.l1.serdes[7].medium.siv.data.get(),
                )
                if resp0.result == 0 or resp1.result == 0 or resp2.result == 0 or resp3.result == 0 or resp4.result == 0 or resp5.result == 0 or resp6.result == 0 or resp7.result == 0:
                    continue
                else:
                    lst0 = resp0.value[12:]
                    tmp0 = []
                    for x in zip(lst0[0::2], lst0[1::2]):
                        tmp0.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data0.extend(tuple(tmp0))
                    siv0.relim()
                    siv0.autoscale_view()
                    print(f"data0 len = {len(data0)}")
                    siv0.hist(x=[*data0], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst1 = resp1.value[12:]
                    tmp1 = []
                    for x in zip(lst1[0::2], lst1[1::2]):
                        tmp1.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data1.extend(tuple(tmp1))
                    siv1.relim()
                    siv1.autoscale_view()
                    print(f"data1 len = {len(data1)}")
                    siv1.hist(x=[*data1], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst2 = resp2.value[12:]
                    tmp2 = []
                    for x in zip(lst2[0::2], lst2[1::2]):
                        tmp2.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data2.extend(tuple(tmp2))
                    siv2.relim()
                    siv2.autoscale_view()
                    print(f"data2 len = {len(data2)}")
                    siv2.hist(x=[*data2], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst3 = resp3.value[12:]
                    tmp3 = []
                    for x in zip(lst3[0::2], lst3[1::2]):
                        tmp3.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data3.extend(tuple(tmp3))
                    siv3.relim()
                    siv3.autoscale_view()
                    print(f"data3 len = {len(data3)}")
                    siv3.hist(x=[*data3], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst4 = resp4.value[12:]
                    tmp4 = []
                    for x in zip(lst4[0::2], lst4[1::2]):
                        tmp4.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data4.extend(tuple(tmp4))
                    siv4.relim()
                    siv4.autoscale_view()
                    print(f"data4 len = {len(data4)}")
                    siv4.hist(x=[*data4], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst5 = resp5.value[12:]
                    tmp5 = []
                    for x in zip(lst5[0::2], lst5[1::2]):
                        tmp5.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data5.extend(tuple(tmp5))
                    siv5.relim()
                    siv5.autoscale_view()
                    print(f"data5 len = {len(data5)}")
                    siv5.hist(x=[*data5], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst6 = resp6.value[12:]
                    tmp6 = []
                    for x in zip(lst6[0::2], lst6[1::2]):
                        tmp6.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data6.extend(tuple(tmp6))
                    siv6.relim()
                    siv6.autoscale_view()
                    print(f"data6 len = {len(data6)}")
                    siv6.hist(x=[*data6], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    lst7 = resp7.value[12:]
                    tmp7 = []
                    for x in zip(lst7[0::2], lst7[1::2]):
                        tmp7.append(int.from_bytes(bytes(x), byteorder='big', signed=True))
                    data7.extend(tuple(tmp7))
                    siv7.relim()
                    siv7.autoscale_view()
                    print(f"data7 len = {len(data7)}")
                    siv7.hist(x=[*data7], bins=128, range=(-64, 63), density=False, color="blue", orientation="horizontal")

                    plt.show()
                    plt.pause(1)
                    print(f"plot {n}")
                    n += 1
                    break

async def main():
    stop_event = asyncio.Event()
    try:
        await siv_plot(
            chassis=CHASSIS_IP,
            username=USERNAME,
            port_str=PORT,
            figure_title=FIGURE_TITLE,
            density=DENSITY
            )
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())