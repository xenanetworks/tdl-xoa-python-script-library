import asyncio
import time
import typing
import contextlib
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver import lli
from xoa_driver.lli import commands as cmd
from . import config
from . import test_port

class TestCase(typing.Protocol):
    config: "config.ConfigurationLoader"
    def __init__(self, config: "config.ConfigurationLoader") -> None: ...
    async def pre_test(self, port_params,  port_role: "enums.Role") -> None: ...
    async def do_test(self, test_resources: "typing.Dict[enums.Role, test_port.TestPort]") -> None: ...
    async def post_test(self, test_resources: "typing.Dict[enums.Role, test_port.TestPort]") -> None: ...

T = typing.TypeVar("T", bound="L47Test")

class L47Test(object):
    def __init__(self, test_case: typing.Type[TestCase]) -> None:
        self.config = config.ConfigurationLoader()
        self.test_resources: typing.Dict[enums.Role, test_port.TestPort] = dict()
        self.test_case = test_case(self.config)
    
    async def setup(self: T) -> T:
        print("Connecting...")
        self.transport = lli.TransportationHandler(enable_logging=self.config.debug)
        await lli.establish_connection(self.transport, self.config.chassis_ip)
        await utils.apply(
            cmd.C_LOGON(self.transport).set(self.config.chassis_pwd),
            cmd.C_OWNER(self.transport).set(self.config.chassis_owner),
        )
        print("Assign ports")
        self.test_resources[enums.Role.SERVER] = test_port.TestPort(self.transport, self.config.chassis_port_s, enums.Role.SERVER, self.test_case)
        self.test_resources[enums.Role.CLIENT] = test_port.TestPort(self.transport, self.config.chassis_port_c, enums.Role.CLIENT, self.test_case)
        print("Prepare ports...")
        await asyncio.gather(*[tp.prepare_port() for tp in self.test_resources.values()])
        return self
    
    async def cleanup(self) -> None:
        if not self.transport:
            return None
        ports_to_release = [
            cmd.P_RESERVATION(self.transport, *tr.port_kind).set_release()
            for tr in self.test_resources.values()
            if tr.is_reserved_by_me
        ]
        await utils.apply(*ports_to_release)
        await cmd.C_LOGOFF(self.transport).set()
        self.transport.close()
    
    async def __aenter__(self: typing.Awaitable[T]) -> T:
        return await self
    
    async def __aexit__(self, type, value, traceback) -> None:
        await self.cleanup()
    
    def __await__(self: T): # type: ignore
        return self.setup().__await__()
    
    async def pre_test(self) -> None:
        await asyncio.gather(*[ tp.pre_test() for tp in self.test_resources.values() ])
    
    @staticmethod
    async def __wait(begin_time: float, time_step: float) -> None:
        def __do():
            diff = time.time() - begin_time
            while diff < time_step:
                diff = time.time() - begin_time
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, __do)
    
    @contextlib.asynccontextmanager
    async def __traffic_runner(self) -> typing.AsyncGenerator[None, None]:
        print("Start traffic on both ports...")
        await asyncio.gather(*[ tp.start_traffic() for tp in self.test_resources.values() ])
        try:
            yield
        finally:
            print("\nTraffic STOP")
            await asyncio.gather(*[ tp.stop_traffic() for tp in self.test_resources.values() ])
    
    async def do_test(self, wait_rump_up: bool = False, skip_rump_down: bool = False) -> None:
        (
            offset_time, 
            up_time, 
            steady_time, 
            down_time
        ) = self.config.lp.to_seconds()
        duration = sum(
            (
                steady_time,
                up_time if not wait_rump_up else .0,  
                down_time if not skip_rump_down else .0
            )
        )
        time_clock = 0.0
        time_step = 1.0 / self.config.sampling_rate
        async with self.__traffic_runner():
            await asyncio.sleep(offset_time + up_time if wait_rump_up else 0)
            while time_clock <= duration:
                begin = time.time()
                print(f"\rProgress: {int(time_clock / duration * 100)}%    Duration: {int(time_clock)}s/{int(duration)}s", end='', flush=True)
                await self.test_case.do_test(self.test_resources)
                await self.__wait(begin, time_step)
                time_clock += time_step
        if skip_rump_down:
            print("Wait for rump down")
            await asyncio.sleep(down_time)
    
    async def post_test(self) -> None:
        await self.test_case.post_test(self.test_resources)