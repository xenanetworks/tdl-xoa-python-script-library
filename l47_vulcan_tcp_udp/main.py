import asyncio
import timeit
from contextlib import contextmanager
from high_level_interface import factory_tcp
from high_level_interface import factory_udp
from low_level_interface import factory_tcp as lli_factory_tcp
from low_level_interface import factory_udp as lli_factory_udp


from high_level_interface.framework import config
from original.tcptest import tcpCC_1B

@contextmanager
def check_time():
    start = timeit.default_timer()
    try:
        yield
    finally:
        stop = timeit.default_timer()
        elapsed = stop - start
        print("Finished in: ", elapsed)

async def main():
    print("Running High Level Interface")
    with check_time():
        await factory_tcp.tcpCC_1B()
        
    print("Running Low Level Interface")
    with check_time():
        await lli_factory_tcp.tcpCC_1B()
    
    config.ConfigurationLoader()
    print("Running Original CLI script")
    with check_time():
        tcpCC_1B()

if __name__ == '__main__':
    asyncio.run(main())