#!/usr/bin/env python3
"""
Quick reduced RFC2889 test — runs only the Congestion Control test 
(simplest, single iteration, ~30s) to verify end-to-end flow.
Patches demo.json on-the-fly to disable all other test suites and
shorten duration to 10 seconds.
"""
from __future__ import annotations
import sys, json, asyncio, logging
from pathlib import Path
from pydantic import SecretStr

try:
    from xoa_converter.entry import converter
    from xoa_converter.types import TestSuiteType
except ImportError:
    print("pip install -U xoa-converter")
    sys.exit(1)

from xoa_core import controller, types

PROJECT_PATH = Path(__file__).parent
PLUGINS_PATH = PROJECT_PATH / "rfc_lib"
GUI_CONFIG  = PROJECT_PATH / "demo.x2889"
CHASSIS_IP  = "10.165.153.42"
MODULE_MAP  = {1: 4}

# ---------- helpers (reused from run_xoa_rfc.py) ----------
sys.path.insert(0, str(PROJECT_PATH))
from run_xoa_rfc import remap_tester_ids, remap_module_indices, read_rfc_type

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)


def make_quick_config(xoa_json: dict) -> dict:
    """Patch the config to run only congestion_control with 10-second duration."""
    ts = xoa_json.get("config", {}).get("test_suites_configuration", {})
    for name, sub in ts.items():
        if isinstance(sub, dict):
            if name == "congestion_control":
                sub["enabled"] = True
                sub["duration"] = 10.0
                sub["iterations"] = 1
            else:
                sub["enabled"] = False
                # also disable sub_test items if present
                for st in sub.get("sub_test", []):
                    if isinstance(st, dict):
                        st["enabled"] = False
    return xoa_json


async def main():
    # 1. Convert GUI config → JSON
    rfc_type = read_rfc_type(GUI_CONFIG)
    with open(GUI_CONFIG, "r") as f:
        xoa_json = json.loads(converter(rfc_type, f.read()))
    logger.info("Converted GUI config")

    # 2. Connect to chassis
    ctrl = await controller.MainController()
    ctrl.register_lib(str(PLUGINS_PATH))
    logger.info("Registered plugin")

    my_cred = types.Credentials(
        product=types.EProductType.VALKYRIE,
        host=CHASSIS_IP,
        password=SecretStr("xena"),
    )
    tester_id = await ctrl.add_tester(my_cred)
    logger.info(f"Connected → tester_id={tester_id}")

    # 3. Remap IDs / modules
    xoa_json = remap_tester_ids(xoa_json, tester_id)
    if MODULE_MAP:
        xoa_json = remap_module_indices(xoa_json, MODULE_MAP)
    logger.info(f"Remapped tester IDs and modules {MODULE_MAP}")

    # 4. Reduce to quick config
    xoa_json = make_quick_config(xoa_json)
    logger.info("Patched config → congestion_control only, 10s duration")

    # 5. Run
    info = ctrl.get_test_suite_info(rfc_type.value)
    if not info:
        logger.error("Test suite not recognized!")
        return
    execution_id = ctrl.start_test_suite(rfc_type.value, xoa_json)
    logger.info(f"Execution started: {execution_id}")

    async for msg in ctrl.listen_changes(execution_id, _filter={types.EMsgType.STATISTICS}):
        result_data = json.loads(msg.payload.model_dump_json())
        is_final = not result_data.get("is_live", True)
        _test_type = result_data.get("test_type", "unknown")
        if is_final:
            logger.info(f"✅ FINAL result  [{_test_type}]  status={result_data.get('status')}")
            logger.info(json.dumps(result_data, indent=2))
        else:
            logger.info(f"⏳ LIVE  [{_test_type}]  rate={result_data.get('rate')}  pkt_size={result_data.get('packet_size')}")

    logger.info("=== Quick test finished ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
