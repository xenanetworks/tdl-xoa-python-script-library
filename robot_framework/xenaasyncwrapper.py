import asyncio
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

