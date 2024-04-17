import asyncio
from xoa_driver import testers, modules, ports, enums
from typing import Generator, Optional, Union, List, Dict, Any
from xoa_driver.hlfuncs import mgmt, anlt
from xoa_driver.lli import commands

#region unions
FREYA_MODULE_UNION = Union[
    modules.MFreya800G1S1P_a,
    modules.MFreya800G1S1P_b,
    modules.MFreya800G1S1POSFP_a,
    modules.MFreya800G1S1POSFP_b,
    modules.MFreya800G4S1P_a,
    modules.MFreya800G4S1P_b,
    modules.MFreya800G4S1P_c,
    modules.MFreya800G4S1P_d,
    modules.MFreya800G4S1P_e,
    modules.MFreya800G4S1P_f,
    modules.MFreya800G4S1POSFP_a,
    modules.MFreya800G4S1POSFP_b,
    modules.MFreya800G4S1POSFP_c,
    modules.MFreya800G4S1POSFP_d,
    modules.MFreya800G4S1POSFP_e,
    modules.MFreya800G4S1POSFP_f,
    modules.MFreya800G1S1P_a_g1,
    modules.MFreya800G1S1P_b_g1,
    modules.MFreya800G1S1POSFP_a_g1,
    modules.MFreya800G1S1POSFP_b_g1,
    modules.MFreya800G4S1P_a_g1,
    modules.MFreya800G4S1P_b_g1,
    modules.MFreya800G4S1P_c_g1,
    modules.MFreya800G4S1P_d_g1,
    modules.MFreya800G4S1P_e_g1,
    modules.MFreya800G4S1P_f_g1,
    modules.MFreya800G4S1POSFP_a_g1,
    modules.MFreya800G4S1POSFP_b_g1,
    modules.MFreya800G4S1POSFP_c_g1,
    modules.MFreya800G4S1POSFP_d_g1,
    modules.MFreya800G4S1POSFP_e_g1,
    modules.MFreya800G4S1POSFP_f_g1,
    modules.MFreya800G1S1P_a_g2,
    modules.MFreya800G1S1P_b_g2,
    modules.MFreya800G1S1POSFP_a_g2,
    modules.MFreya800G1S1POSFP_b_g2,
    modules.MFreya800G4S1P_a_g2,
    modules.MFreya800G4S1P_b_g2,
    modules.MFreya800G4S1P_c_g2,
    modules.MFreya800G4S1P_d_g2,
    modules.MFreya800G4S1P_e_g2,
    modules.MFreya800G4S1P_f_g2,
    modules.MFreya800G4S1POSFP_a_g2,
    modules.MFreya800G4S1POSFP_b_g2,
    modules.MFreya800G4S1POSFP_c_g2,
    modules.MFreya800G4S1POSFP_d_g2,
    modules.MFreya800G4S1POSFP_e_g2,
    modules.MFreya800G4S1POSFP_f_g2,
]

#endregion

async def freya_tx_tune_native(
        chassis_ip: str, 
        username: str, 
        mid: int, 
        pid: int, 
        sid: int, 
        pre3: int,
        pre2: int,
        pre: int,
        main: int,
        post: int,
        stop_event: asyncio.Event):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module
        module = tester.modules.obtain(mid)
        if not isinstance(module, FREYA_MODULE_UNION):
            print(f"The module is not a Freya module")
            print(f"Abort")
            return None

        # Get the port
        port = module.ports.obtain(pid)

        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        # Read serdes lane count from port
        resp = await port.capabilities.get()
        _serdes_cnt = resp.serdes_count

        if sid+1>_serdes_cnt:
            print(f"Serdes lane {sid} doesn't exit. There are {_serdes_cnt} serdes lanes on this port.")
            return None

        conn, mid, pid = anlt.get_ctx(port)
        print(f"Write (native): pre3 = {pre3}, pre2 = {pre2}, pre = {pre}, main = {main}, post = {post}")
        await commands.PL1_PHYTXEQ(conn, mid, pid, sid).set(pre3, pre2, pre, main, post)

        resp = await commands.PL1_PHYTXEQ(conn, mid, pid, sid).get()
        print(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await commands.PL1_PHYTXEQ_LEVEL(conn, mid, pid, sid).get()
        print(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await commands.PL1_PHYTXEQ_COEFF(conn, mid, pid, sid).get()
        print(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")



async def freya_tx_tune_level(
        chassis_ip: str, 
        username: str, 
        mid: int, 
        pid: int, 
        sid: int, 
        pre3: float,
        pre2: float,
        pre: float,
        main: int,
        post: float,
        stop_event: asyncio.Event):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module
        module = tester.modules.obtain(mid)
        if not isinstance(module, FREYA_MODULE_UNION):
            print(f"The module is not a Freya module")
            print(f"Abort")
            return None

        # Get the port
        port = module.ports.obtain(pid)

        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        # Read serdes lane count from port
        resp = await port.capabilities.get()
        _serdes_cnt = resp.serdes_count

        if sid+1>_serdes_cnt:
            print(f"Serdes lane {sid} doesn't exit. There are {_serdes_cnt} serdes lanes on this port.")
            return None

        conn, mid, pid = anlt.get_ctx(port)
        _pre3 = int(pre3*10)
        _pre2 = int(pre2*10)
        _pre = int(pre*10)
        _post = int(post*10)
        _main = main
        print(f"Write (level): pre3 = {pre3}dB, pre2 = {pre2}dB, pre = {pre}dB, main = {main}mV, post = {post}dB")
        await commands.PL1_PHYTXEQ_LEVEL(conn, mid, pid, sid).set(_pre3, _pre2, _pre, _main, _post)

        resp = await commands.PL1_PHYTXEQ(conn, mid, pid, sid).get()
        print(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await commands.PL1_PHYTXEQ_LEVEL(conn, mid, pid, sid).get()
        print(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await commands.PL1_PHYTXEQ_COEFF(conn, mid, pid, sid).get()
        print(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")



async def freya_tx_tune_coeff(
        chassis_ip: str, 
        username: str, 
        mid: int, 
        pid: int, 
        sid: int, 
        pre3: float,
        pre2: float,
        pre: float,
        main: float,
        post: float,
        stop_event: asyncio.Event):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester:

        # Access module
        module = tester.modules.obtain(mid)
        if not isinstance(module, FREYA_MODULE_UNION):
            print(f"The module is not a Freya module")
            print(f"Abort")
            return None

        # Get the port
        port = module.ports.obtain(pid)

        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        # Read serdes lane count from port
        resp = await port.capabilities.get()
        _serdes_cnt = resp.serdes_count

        if sid+1>_serdes_cnt:
            print(f"Serdes lane {sid} doesn't exit. There are {_serdes_cnt} serdes lanes on this port.")
            return None

        conn, mid, pid = anlt.get_ctx(port)
        _pre3 = int(pre3*1000)
        _pre2 = int(pre2*1000)
        _pre = int(pre*1000)
        _post = int(post*1000)
        _main = int(main*1000)
        print(f"Write (IEEE): pre3 = {pre3}, pre2 = {pre2}, pre = {pre}, main = {main}, post = {post}")
        await commands.PL1_PHYTXEQ_COEFF(conn, mid, pid, sid).set(_pre3, _pre2, _pre, _main, _post)

        resp = await commands.PL1_PHYTXEQ(conn, mid, pid, sid).get()
        print(f"Read (native):  pre3 = {resp.pre3}, pre2 = {resp.pre2}, pre = {resp.pre}, main = {resp.main}, post = {resp.post}")
        resp = await commands.PL1_PHYTXEQ_LEVEL(conn, mid, pid, sid).get()
        print(f"Read (level):  pre3 = {resp.pre3/10}dB, pre2 = {resp.pre2/10}dB, pre = {resp.pre/10}dB, main = {resp.main}mV, post = {resp.post/10}dB")
        resp = await commands.PL1_PHYTXEQ_COEFF(conn, mid, pid, sid).get()
        print(f"Read (IEEE):  pre3 = {resp.pre3/1000}, pre2 = {resp.pre2/1000}, pre = {resp.pre/1000}, main = {resp.main/1000}, post = {resp.post/1000}")


async def main():
    stop_event = asyncio.Event()
    try:
        # await freya_tx_tune_native(chassis_ip="10.165.136.60", username="xoa", mid=3, pid=0, sid=0, pre3=0, pre2=0, pre=21, main=77, post=13, stop_event=stop_event)
        # await freya_tx_tune_level(chassis_ip="10.165.136.60", username="xoa", mid=3, pid=0, sid=0, pre3=0.0, pre2=0.0, pre=5.7, main=900, post=3.0, stop_event=stop_event)
        await freya_tx_tune_coeff(chassis_ip="10.165.136.60", username="xoa", mid=3, pid=0, sid=0, pre3=0.0, pre2=0.0, pre=-0.362, main=1.125, post=-0.199, stop_event=stop_event)

    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())