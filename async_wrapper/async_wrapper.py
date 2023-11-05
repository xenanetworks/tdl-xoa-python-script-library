from typing import Any, Awaitable, Callable, TypeVar
from xoa_driver.hlfuncs import mgmt, cli
from xoa_driver.misc import Hex
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver import ports
from xoa_driver import modules
from xoa_driver import testers
import asyncio
import threading
import time
import queue

T = TypeVar("T")


class XenaAsyncWrapper:
    """This is a wrapper class that encapsulates XOA asyncio functions 
    so you can use the APIs in a non-async fashion.
    """
    __slots__ = ("loop", "thread", "_events")

    def __init__(self) -> None:
        self.loop = None
        self.thread = threading.Thread(target=self._run_event_loop)
        self.thread.start()
        self._events = queue.Queue()

    def _run_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coroutine_threadsafe(self, coro: Awaitable[T]) -> T:
        if not self.loop:
            raise RuntimeError("Event loop is not running")
        future_ = asyncio.run_coroutine_threadsafe(coro, self.loop)
        if exc := future_.exception():
            raise exc
        return future_.result()

    def is_thread_started(self) -> bool:
        return self.loop is not None and self.loop.is_running()

    def close(self) -> None:
        if not self.loop:
            return None
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

    def __call__(self, coro):
        if self.loop is None:
            raise RuntimeError("Thread not started")

        event = asyncio.Event()

        def _callback(fut):
            self._events.put((fut.result(), fut.exception()))
            self.loop.call_soon_threadsafe(event.set)

        async def _runner():
            try:
                fut = asyncio.ensure_future(coro)
                fut.add_done_callback(_callback)
                await event.wait()
            except Exception as exc:
                self._events.put((None, exc))

        asyncio.run_coroutine_threadsafe(_runner(), self.loop)
        result, exc = self._events.get()

        if exc:
            raise exc
        return result


CHASSIS_IP = "10.20.1.170"
USERNAME = "xoa"
MODULE_IDX = 0
PORT_IDX = 0
TRAFFIC_DURATION = 3
COOLDOWN_DURATION = 1


def main() -> None:

    # initialize async wrapper
    xaw = XenaAsyncWrapper()

    # check if it starts to work
    while not xaw.is_thread_started():
        time.sleep(0.01)

    # create a tester instance
    # this will automatically create a tcp connection to the tester
    tester = xaw(testers.L23Tester(host=CHASSIS_IP, username=USERNAME, enable_logging=False))

    # obtain a module instance
    module = tester.modules.obtain(MODULE_IDX)

    # exit if module type is Chimera
    if isinstance(module, modules.ModuleChimera):
        return None

    # Obtain a port from the module
    port = module.ports.obtain(PORT_IDX)

    # Read port property
    resp = xaw(port.comment.get())
    print(f"{resp.comment}")

    # reserve & reset port
    xaw(mgmt.reserve_port(port=port))
    xaw(mgmt.reset_port(port=port))

    xaw(asyncio.sleep(5))

    # executing set request
    xaw(port.comment.set(comment="this is my comment"))

    # executing get request of p_comment command
    port_comment = xaw(port.comment.get())
    print(port_comment.comment)

    # create a stream
    stream = xaw(port.streams.create())
    xaw(utils.apply(
        stream.enable.set_on(),
        stream.comment.set(f"Stream A to B"),
        stream.rate.pps.set(stream_rate_pps=10000),
        stream.packet.length.set(length_type=enums.LengthType.FIXED, min_val=1000, max_val=1000),
        stream.tpld_id.set(test_payload_identifier = 0))
        )
    
    # start and stop traffic
    xaw(port.traffic.state.set_start())
    time.sleep(TRAFFIC_DURATION)
    xaw(port.traffic.state.set_stop())
    time.sleep(COOLDOWN_DURATION)

    # collect statistics
    _tx, _rx = xaw(utils.apply(
                port.statistics.tx.total.get(),
                port.statistics.rx.total.get(),
            ))
    print(f"==================================")
    print(f"{'TRAFFIC STATS'}")
    print(f"==================================")
    print(f"{'TX FRAMES:':<20}{_tx.packet_count_since_cleared}")
    print(f"{'RX FRAMES:':<20}{_rx.packet_count_since_cleared}")
    print(f"{'TX BYTES:':<20}{_tx.byte_count_since_cleared}")
    print(f"{'RX BYTES:':<20}{_rx.byte_count_since_cleared}")



if __name__ == "__main__":
    main()
