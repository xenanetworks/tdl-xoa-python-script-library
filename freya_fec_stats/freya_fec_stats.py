import asyncio

from xoa_driver import testers
from xoa_driver import modules
from xoa_driver import ports
from xoa_driver import enums
from xoa_driver import utils
from xoa_driver.hlfuncs import mgmt
from xoa_driver.misc import Hex
import ipaddress
import csv
import time

CHASSIS_IP = "10.20.30.60"
USERNAME = "xoa"
MODULE_IDX = 3
PORT_IDX = 1
_FREYA_MODULES = (modules.MFreya800G4S1P_a, modules.MFreya800G4S1P_b, modules.MFreya800G4S1POSFP_a, modules.MFreya800G4S1POSFP_b)
_FREYA_PORTS = (ports.PFreya800G4S1P_a, ports.PFreya800G4S1P_b, ports.PFreya800G4S1POSFP_a, ports.PFreya800G4S1POSFP_b)
        

async def my_awesome_func(stop_event: asyncio.Event):

    # Establish connection to a Valkyrie tester using Python context manager
    # The connection will be automatically terminated when it is out of the block
    async with testers.L23Tester(CHASSIS_IP, USERNAME, enable_logging=False) as tester:

        # Access module index 0 on the tester
        module = tester.modules.obtain(MODULE_IDX)

        if not isinstance(module, _FREYA_MODULES):
            print(f"Not Freya module")
            return None 

        # Get the port 0 on module 0 as TX port
        port = module.ports.obtain(PORT_IDX)

        # Forcibly reserve the port and reset it.
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)

        await asyncio.sleep(5)

        # set FEC mode on
        await port.fec_mode.set(mode=enums.FECMode.ON)

        await port.pcs_pma.rx.clear.set()
        fec_status = await port.pcs_pma.rx.fec_status.get()
        n = fec_status.data_count - 2
        field = ["time"]
        for i in range(n):
            field.append(f"FEC Blocks (Symbol Errors = {i})")
        field.append(f"FEC Blocks (Symbol Errors > {n-1})")
        field.append("total_rx_bit_count")
        field.append("total_rx_codeword_count")
        field.append("total_corrected_codeword_count")
        field.append("total_uncorrectable_codeword_count")
        field.append("total_corrected_symbol_count")
        field.append("total_pre_fec_ber")
        field.append("total_post_fec_ber")

        with open('fec_stats.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(field)
            while True:
                dat = []
                dat.append(time.time())
                total_status, fec_status = await utils.apply(
                    port.pcs_pma.rx.total_status.get(),
                    port.pcs_pma.rx.fec_status.get()
                )
                print(f"{fec_status.data_count}")
                print(f"{fec_status.stats}")
                print(f"{total_status}")
                n = fec_status.data_count - 2
                for i in range(n):
                    dat.append(fec_status.stats[i])
                    print(f"FEC Blocks (Symbol Errors = {i}): {fec_status.stats[i]}")
                print(f"FEC Blocks (Symbol Errors > {n-1}): {fec_status.stats[n]}")
                dat.append(fec_status.stats[n])
                dat.append(total_status.total_rx_bit_count)
                dat.append(total_status.total_rx_codeword_count)
                dat.append(total_status.total_corrected_codeword_count)
                dat.append(total_status.total_uncorrectable_codeword_count)
                dat.append(total_status.total_corrected_symbol_count)
                dat.append(1/total_status.total_pre_fec_ber)
                dat.append(1/total_status.total_post_fec_ber)
                writer.writerow(dat)
                print(f"total_rx_bit_count: {total_status.total_rx_bit_count}")
                print(f"total_rx_codeword_count: {total_status.total_rx_codeword_count}")
                print(f"total_corrected_codeword_count: {total_status.total_corrected_codeword_count}")
                print(f"total_uncorrectable_codeword_count: {total_status.total_uncorrectable_codeword_count}")
                print(f"total_corrected_symbol_count: {total_status.total_corrected_symbol_count}")
                print(f"total_pre_fec_ber: {1/total_status.total_pre_fec_ber}")
                print(f"total_post_fec_ber: {1/total_status.total_post_fec_ber}")
                await asyncio.sleep(1)

async def main():
    stop_event = asyncio.Event()
    try:
        await my_awesome_func(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
