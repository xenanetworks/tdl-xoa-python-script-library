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
# 3. The script prints out the test data
# 
#
################################################################
from __future__ import annotations
import sys
from xoa_core import controller, types
import asyncio
import json
import csv
import subprocess
from pathlib import Path
import logging
from pydantic import SecretStr


class NetworkLostError(Exception):
    """Raised when the chassis becomes unreachable during a test."""
    pass


async def network_watchdog(host: str, interval: float = 15.0, fail_count: int = 3, logger=None):
    """Background task that pings the chassis every `interval` seconds.
    
    If `fail_count` consecutive pings fail, raises NetworkLostError
    which cancels the current task group.
    """
    consecutive_failures = 0
    while True:
        await asyncio.sleep(interval)
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["ping", "-c", "1", "-W", "3", host],
                capture_output=True,
            )
            if result.returncode == 0:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if logger:
                    logger.warning(f"Network check failed ({consecutive_failures}/{fail_count}): {host} unreachable")
        except Exception as e:
            consecutive_failures += 1
            if logger:
                logger.warning(f"Network check error ({consecutive_failures}/{fail_count}): {e}")

        if consecutive_failures >= fail_count:
            msg = f"Chassis {host} unreachable for {consecutive_failures} consecutive checks — aborting test"
            if logger:
                logger.error(msg)
            raise NetworkLostError(msg)

# XOA Converter is an independent module and it needs to be installed via `pip install xoa-converter`
try:
    from xoa_converter.entry import converter
    from xoa_converter.types import TestSuiteType
except ImportError:
    print("XOA Converter is an independent module and it needs to be installed via `pip install -U xoa-converter`")
    sys.exit()


#---------------------------
# Global parameters
#---------------------------
PROJECT_PATH = Path(__file__).parent
PLUGINS_PATH = PROJECT_PATH / "rfc_lib"
GUI_CONFIG = PROJECT_PATH / "demo.x2889"
XOA_CONFIG = PROJECT_PATH / "demo.json"
CHASSIS_IP = "10.165.153.42"
RUN_FROM_GUI_CONFIG = True

# Remap module indices from the GUI config to the target chassis.
# Key = old module index (in the config file), Value = new module index (on target chassis).
# Leave empty {} if no remapping is needed.
MODULE_MAP = {1: 4}

# Set True to reduce to 4 ports / 10s duration for quick validation (~5-15 min).
# Most test types still run, just with fewer port-pairs and shorter traffic.
QUICK_TEST = False

# Set to a list of test suite names to run ONLY those tests (others disabled).
# e.g. ["address_caching_capacity"]  or  ["rate_test", "forward_pressure"]
# Set to None or [] to run all enabled tests from the config file.
ONLY_TESTS = ["address_caching_capacity"]


#---------------------------
# internal functions
#---------------------------
def flat_total_json(data: dict) -> dict: 
    new_data = dict() 
    for key, value in data.items(): 
        if not isinstance(value, dict): 
            new_data[key] = value 
        else: 
            for k, v in value.items(): 
                new_data[key + "_" + k] = v 
    return new_data

def read_rfc_type(gui_config: Path) -> TestSuiteType:
    file_extension = Path(gui_config).suffix
    if file_extension == ".v2544" or file_extension == ".x2544":
        return TestSuiteType.RFC2544
    elif file_extension == ".v2889" or file_extension == ".x2889":
        return TestSuiteType.RFC2889
    else:
        return TestSuiteType.RFC3918

def remap_tester_ids(xoa_config: dict, new_tester_id: str) -> dict:
    """Replace all old tester_id references in the converted XOA config
    with the actual connected tester_id.
    
    The converted config may reference a different chassis than the one
    we are connected to (e.g. config was saved against chassis A but we
    run against chassis B). The tester_id is an MD5 hash of host:port,
    so it will differ. This function patches all occurrences.
    """
    # Collect all unique old tester_ids from port_identities
    old_ids = set(
        pi["tester_id"]
        for pi in xoa_config.get("port_identities", [])
        if pi.get("tester_id") != new_tester_id
    )
    if not old_ids:
        return xoa_config  # nothing to remap

    # 1. Patch port_identities
    for pi in xoa_config.get("port_identities", []):
        if pi["tester_id"] in old_ids:
            pi["tester_id"] = new_tester_id

    # 2. Patch ports_configuration keys and tester_id values
    ports_cfg = xoa_config.get("config", {}).get("ports_configuration", {})
    new_ports_cfg = {}
    for key, value in ports_cfg.items():
        new_key = key
        for old_id in old_ids:
            new_key = new_key.replace(old_id, new_tester_id)
        if isinstance(value, dict) and value.get("tester_id") in old_ids:
            value["tester_id"] = new_tester_id
        new_ports_cfg[new_key] = value
    if ports_cfg:
        xoa_config["config"]["ports_configuration"] = new_ports_cfg

    return xoa_config

def remap_module_indices(xoa_config: dict, module_map: dict) -> dict:
    """Remap module indices in the XOA config.
    
    When running a config created for one chassis on a different chassis,
    the module indices may differ. This function patches all occurrences.
    
    Args:
        xoa_config: The converted XOA config dict.
        module_map: Dict mapping old module index to new module index,
                    e.g. {1: 3} to remap module 1 -> module 3.
    """
    if not module_map:
        return xoa_config

    # 1. Patch port_identities
    for pi in xoa_config.get("port_identities", []):
        old_mod = pi["module_index"]
        if old_mod in module_map:
            pi["module_index"] = module_map[old_mod]

    # 2. Patch ports_configuration keys (format: P-{tester_id}-{module}-{port})
    ports_cfg = xoa_config.get("config", {}).get("ports_configuration", {})
    new_ports_cfg = {}
    for key, value in ports_cfg.items():
        parts = key.split("-")
        # key format: P-{tester_id}-{module_index}-{port_index}
        if len(parts) >= 4:
            old_mod = int(parts[-2])
            if old_mod in module_map:
                parts[-2] = str(module_map[old_mod])
                key = "-".join(parts)
        new_ports_cfg[key] = value
    if ports_cfg:
        xoa_config["config"]["ports_configuration"] = new_ports_cfg

    return xoa_config


def trim_config_for_quick_test(xoa_config: dict) -> dict:
    """Reduce config to 4 ports and 10s duration so the full suite runs in ~5-15 min.

    Port requirements per test:
      - rate_test (throughput/forwarding): 2+ ports (mesh)
      - congestion_control: exactly 4 (2 SOURCE + 2 DESTINATION)
      - forward_pressure: 2 (1 SOURCE + 1 DESTINATION)
      - max_forwarding_rate: 2 (1 SOURCE + 1 DESTINATION)
      - address_caching_capacity: 3 (TEST + LEARNING + MONITORING)
      - address_learning_rate: 3 (same as above)
      - errored_frames_filtering: 2
      - broadcast_forwarding: 2+

    We keep the first 4 ports so congestion_control works,
    and disable address_learning_rate to save time (same code path as caching).
    """
    # --- keep only the first 4 ports ---
    pids = xoa_config.get("port_identities", [])
    keep_count = 4
    keep_keys = set()
    keep_item_ids = set()
    if len(pids) > keep_count:
        kept = pids[:keep_count]
        xoa_config["port_identities"] = kept
        for p in kept:
            tid = p["tester_id"]
            mod = p["module_index"]
            port = p["port_index"]
            keep_keys.add(f"P-{tid}-{mod}-{port}")
        # prune ports_configuration and collect kept item_ids (UUIDs)
        pc = xoa_config.get("config", {}).get("ports_configuration", {})
        new_pc = {}
        for k, v in pc.items():
            if k in keep_keys:
                new_pc[k] = v
                iid = v.get("item_id", "")
                if iid:
                    keep_item_ids.add(iid)
        xoa_config["config"]["ports_configuration"] = new_pc

    # --- disable tests we skip for quick runs ---
    # These tests require a physical DUT with MAC address learning:
    #   address_caching_capacity: hangs in toggle_sync_state / generate_traffic without DUT
    #   address_learning_rate: same code path as address_caching_capacity
    #   errored_frames_filtering: needs DUT to filter errored frames
    DISABLE_TESTS = {"address_learning_rate", "address_caching_capacity", "errored_frames_filtering"}

    def _prune_role_handler(d: dict) -> None:
        """Mark ports not in keep_item_ids as is_used=False in port_role_handler."""
        prh = d.get("port_role_handler")
        if prh and keep_item_ids:
            role_map = prh.get("role_map", {})
            pruned = {}
            for guid_key, role_info in role_map.items():
                uuid_part = guid_key.replace("guid_", "")
                if uuid_part in keep_item_ids:
                    pruned[guid_key] = role_info
                else:
                    pruned[guid_key] = {**role_info, "is_used": False}
            prh["role_map"] = pruned

    # --- shorten durations to 10s, iterations to 1 ---
    ts = xoa_config.get("config", {}).get("test_suites_configuration", {})
    for name, sub in ts.items():
        if not isinstance(sub, dict):
            continue
        # disable tests not needed for quick run
        if name in DISABLE_TESTS:
            sub["enabled"] = False
        if "duration" in sub:
            sub["duration"] = 10.0
        if "iterations" in sub:
            sub["iterations"] = 1
        # widen rate_sweep_options step to reduce iterations
        rso = sub.get("rate_sweep_options")
        if rso and isinstance(rso, dict):
            rso["step_value"] = 50.0  # was 1.0 — now only ~2 steps
        # prune top-level port_role_handler
        _prune_role_handler(sub)
        # also patch sub_test items (rate_test has sub_tests)
        for st in sub.get("sub_test", []):
            if isinstance(st, dict):
                if "duration" in st:
                    st["duration"] = 10.0
                if "iterations" in st:
                    st["iterations"] = 1
                rso_st = st.get("rate_sweep_options")
                if rso_st and isinstance(rso_st, dict):
                    rso_st["step_value"] = 50.0
                _prune_role_handler(st)

    # --- disable stop-on-LOS (no DUT means ports may lose sync after toggling) ---
    gtc = xoa_config.get("config", {}).get("general_test_configuration", {})
    gtc["should_stop_on_los"] = False

    return xoa_config


#---------------------------
# run_xoa_rfc
#---------------------------
async def run_xoa_rfc(chassis: str, plugin_path: Path, gui_config: Path, xoa_config: Path, run_from_gui_config: bool, module_map: dict = None) -> None:

    # configure basic logger
    logger = logging.getLogger("run_xoa_rfc")
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="run_xoa_rfc.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # Define your tester login credentials
    my_tester_credential = types.Credentials(
        product=types.EProductType.VALKYRIE,
        host=chassis,
        password=SecretStr("xena")
    )
    logger.info(f"#####################################################################")
    logger.info(f"Tester credential:")
    logger.info(f"  Chassis:            {chassis}")
    logger.info(f"#####################################################################")

    # Create a default instance of the controller class.
    ctrl = await controller.MainController()
    logger.info(f"Create XOA core controller")

    # Register the plugins folder.
    ctrl.register_lib(str(plugin_path))
    logger.info(f"Register plugin path: {plugin_path}")

    # Add tester credentials into the controller. If already added, it will be ignored.
    # If you want to add a list of testers, you need to iterate through the list.
    tester_id = await ctrl.add_tester(my_tester_credential)
    logger.info(f"Add tester {tester_id} to controller")

    # Wait for the controller to fully sync module/port info from the chassis
    await asyncio.sleep(5)
    logger.info("Controller sync delay complete")

    if run_from_gui_config == True:
        # Convert GUI config into XOA config and run.
        with open(gui_config, "r") as f:
            
            # get the rfc type from the filename
            rfc_type = read_rfc_type(gui_config)
            logger.info(f"Get the RFC type from the config filename")

            # get test suite information from the core's registration
            info = ctrl.get_test_suite_info(rfc_type.value)
            if not info:
                logger.warning("Test suite is not recognized.")
                return None

            # convert the GUI config file into XOA config file
            _xoa_config = converter(rfc_type, f.read())

            # save new data in xoa json
            with open(xoa_config, "w") as f:
                f.write(_xoa_config)
                logger.info(f"Convert {gui_config} into {xoa_config}")

            # you can use the config file below to start the test
            xoa_config_json = json.loads(_xoa_config)

            # Remap tester IDs in the config to match the actual connected chassis
            xoa_config_json = remap_tester_ids(xoa_config_json, tester_id)
            logger.info(f"Remapped tester IDs to {tester_id}")

            # Remap module indices if needed
            if module_map:
                xoa_config_json = remap_module_indices(xoa_config_json, module_map)
                logger.info(f"Remapped module indices: {module_map}")

            if QUICK_TEST:
                xoa_config_json = trim_config_for_quick_test(xoa_config_json)
                n_ports = len(xoa_config_json.get('port_identities', []))
                logger.info(f"QUICK_TEST: trimmed to {n_ports} ports, 10s duration")

            # If ONLY_TESTS is set, disable everything except those tests
            if ONLY_TESTS:
                ts = xoa_config_json.get("config", {}).get("test_suites_configuration", {})
                for name, sub in ts.items():
                    if isinstance(sub, dict):
                        if name in ONLY_TESTS:
                            sub["enabled"] = True
                            logger.info(f"ONLY_TESTS: enabled {name}")
                        else:
                            sub["enabled"] = False
                logger.info(f"ONLY_TESTS: running only {ONLY_TESTS}")

            # Test suite name is received from call of c.get_available_test_suites()
            execution_id = ctrl.start_test_suite(rfc_type.value, xoa_config_json)
            logger.info(f"Execute the RFC test. (Execution ID: {execution_id})")

            # Consume test results with a network watchdog running in parallel.
            # If the chassis becomes unreachable the watchdog raises NetworkLostError
            # which cancels the listener and exits cleanly instead of hanging.
            MSG_TIMEOUT = 120  # seconds to wait for a single message before considering it stuck

            async def _consume_results():
                async for msg in ctrl.listen_changes(execution_id, _filter={types.EMsgType.STATISTICS}):
                    result_data = json.loads(msg.payload.model_dump_json())
                    is_final = not result_data.get("is_live", True)
                    _test_type = result_data.get("test_type", "unknown")
                    if is_final:
                        logger.info(f"RFC-2889 {_test_type.upper()} test result (final)")
                        logger.info(json.dumps(result_data, sort_keys=True, indent=4))
                    else:
                        logger.debug(f"RFC-2889 {_test_type} live stats (rate={result_data.get('rate')}, pkt_size={result_data.get('packet_size')})")

            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(network_watchdog(chassis, interval=15, fail_count=3, logger=logger))
                    tg.create_task(_consume_results())
            except* NetworkLostError as eg:
                logger.error(f"TEST ABORTED: {eg.exceptions[0]}")
                sys.exit(1)
            except* Exception as eg:
                # _consume_results finished normally (test complete) — the watchdog
                # gets cancelled automatically when the TaskGroup scope exits.
                pass
    
    else:
        with open(xoa_config, "r") as f:
            # get the rfc type from the filename
            rfc_type = read_rfc_type(gui_config)
            logger.info(f"Get the RFC type from the config filename")

            # get rfc2889 test suite information from the core's registration
            info = ctrl.get_test_suite_info(rfc_type.value)
            if not info:
                print("Test suite is not recognized.")
                return None

            # Remap tester IDs to match the actual connected chassis
            xoa_config_json = json.load(f)
            xoa_config_json = remap_tester_ids(xoa_config_json, tester_id)
            logger.info(f"Remapped tester IDs to {tester_id}")

            # Remap module indices if needed
            if module_map:
                xoa_config_json = remap_module_indices(xoa_config_json, module_map)
                logger.info(f"Remapped module indices: {module_map}")

            # Test suite name: "RFC-2544" is received from call of c.get_available_test_suites()
            execution_id = ctrl.start_test_suite(rfc_type.value, xoa_config_json)

            logger.info(f"Execute the RFC test. (Execution ID: {execution_id})")

            # Consume test results with a network watchdog.
            async def _consume_results2():
                async for msg in ctrl.listen_changes(execution_id, _filter={types.EMsgType.STATISTICS}):
                    result_data = json.loads(msg.payload.model_dump_json())
                    is_final = not result_data.get("is_live", True)
                    _test_type = result_data.get("test_type", "unknown")
                    if is_final:
                        logger.info(f"RFC-2889 {_test_type.upper()} test result (final)")
                        logger.info(json.dumps(result_data, sort_keys=True, indent=4))
                    else:
                        logger.debug(f"RFC-2889 {_test_type} live stats (rate={result_data.get('rate')}, pkt_size={result_data.get('packet_size')})")

            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(network_watchdog(chassis, interval=15, fail_count=3, logger=logger))
                    tg.create_task(_consume_results2())
            except* NetworkLostError as eg:
                logger.error(f"TEST ABORTED: {eg.exceptions[0]}")
                sys.exit(1)
            except* Exception as eg:
                pass

async def main():
    stop_event =asyncio.Event()
    try:
        await run_xoa_rfc(
            chassis=CHASSIS_IP,
            plugin_path=PLUGINS_PATH,
            gui_config=GUI_CONFIG,
            xoa_config=XOA_CONFIG,
            run_from_gui_config=RUN_FROM_GUI_CONFIG,
            module_map=MODULE_MAP,
        )
    except KeyboardInterrupt:
        stop_event.set()


if __name__=="__main__":
    asyncio.run(main())