################################################################
#
#                   RFC TEST SUITE USING GUI CONFIG
#
# This script shows you how to run Xena 2544/2889/3918 
# configurations using xoa-core
# 
# The latest 2544/2889/3918 plugins are already included in rfc_lib/

# 1. The script first convert the Xena test suite GUI configuration 
# files (.v2544, .v2889, .v3918, .x2544, .x2889, .x3918) into .json, 
# which is used by the xoa-core.
# 
# 2. Then run the test configuration on the specified chassis given 
# by CHASSIS_IP.
# 
# 3. The script saves the final results into the specified csv file, 
# given by DATA_FILE.
# 
#
################################################################
from __future__ import annotations
import sys
from xoa_core import controller, types
import asyncio
import json
import csv
from pathlib import Path

# XOA Converter is an independent module and it needs to be installed via `pip install xoa-converter`
try:
    from xoa_converter.entry import converter
    from xoa_converter.types import TestSuiteType
except ImportError:
    print("XOA Converter is an independent module and it needs to be installed via `pip install xoa-converter`")
    sys.exit()

PROJECT_PATH = Path(__file__).parent
PLUGINS_PATH = PROJECT_PATH / "rfc_lib"

#---------------------------
# Global parameters
#---------------------------
RFC_TYPE = TestSuiteType.RFC2544 # allowed values: "RFC2544", "RFC2889", "RFC3918"
GUI_CONFIG = PROJECT_PATH / "demo.x2544"
XOA_CONFIG = PROJECT_PATH / "demo.json"
DATA_FILE = PROJECT_PATH / "demo.csv"
CHASSIS_IP = "10.165.136.70"


def normalize_json(data: dict) -> dict: 
    new_data = dict() 
    for key, value in data.items(): 
        if not isinstance(value, dict): 
            new_data[key] = value 
        else: 
            for k, v in value.items(): 
                new_data[key + "_" + k] = v 
    return new_data

#---------------------------
# run_xoa_rfc
#---------------------------
async def run_xoa_rfc(chassis: str, plugin_path: Path, gui_config: Path, rfc_type: TestSuiteType) -> None:
    # Define your tester login credentials
    my_tester_credential = types.Credentials(
        product=types.EProductType.VALKYRIE,
        host=chassis
    )

    # Create a default instance of the controller class.
    ctrl = await controller.MainController()

    # Register the plugins folder.
    ctrl.register_lib(str(plugin_path))

    # Add tester credentials into teh controller. If already added, it will be ignored.
    # If you want to add a list of testers, you need to iterate through the list.
    await ctrl.add_tester(my_tester_credential)

    # Convert GUI config into XOA config and run.
    with open(gui_config, "r") as f:
        # get test suite information from the core's registration
        info = ctrl.get_test_suite_info(rfc_type.value)
        if not info:
            print("Test suite is not recognized.")
            return None

        # convert the GUI config file into XOA config file
        xoa_config = converter(rfc_type, f.read())

        # save new data in xoa json
        with open(XOA_CONFIG, "w") as f:
            f.write(xoa_config)

        # you can use the config file below to start the test
        xoa_config_json = json.loads(xoa_config)

        # Test suite name is received from call of c.get_available_test_suites()
        execution_id = ctrl.start_test_suite(rfc_type.value, xoa_config_json)

        # The example here only shows a print of test result data.
        async for msg in ctrl.listen_changes(execution_id, _filter={types.EMsgType.STATISTICS}):
            result_data = json.loads(msg.payload.json())
            if result_data["is_final"] == True:
                if result_data["result_state"] == "done":
                    print(result_data)

                    # open a file for writing
                    with open(DATA_FILE, 'a') as data_file:
                        # create the csv writer object
                        csv_writer = csv.writer(data_file)
                        header = result_data.keys()
                        csv_writer.writerow(header)
                        csv_writer.writerow(result_data.values())
                        
    # By the next line, we prevent the script from being immediately
    # terminated as the test execution and subscription are non blockable, and they ran asynchronously,
    # await asyncio.Event().wait()

async def main():
    stop_event =asyncio.Event()
    try:
        await run_xoa_rfc(
            chassis=CHASSIS_IP,
            plugin_path=PLUGINS_PATH,
            gui_config=GUI_CONFIG,
            rfc_type=RFC_TYPE,
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())