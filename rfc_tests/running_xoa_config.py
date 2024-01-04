from __future__ import annotations
from xoa_core import (
    controller,
    types,
)
import asyncio
import json
from pathlib import Path

PROJECT_PATH = Path(__file__).parent
XOA_CONFIG = PROJECT_PATH / "xoa_2544_config.json"
PLUGINS_PATH = PROJECT_PATH / "test_suites"


async def subscribe(ctrl: "controller.MainController", channel_name: str, fltr: set["types.EMsgType"] | None = None) -> None:
    async for msg in ctrl.listen_changes(channel_name, _filter=fltr):
        print(msg)


async def main() -> None:
    # Define your tester login credentials
    my_tester_credential = types.Credentials(
        product=types.EProductType.VALKYRIE,
        host="10.20.30.40"
    )

    # Create a default instance of the controller class.
    ctrl = await controller.MainController()

    # Register the plugins folder.
    ctrl.register_lib(str(PLUGINS_PATH))

    # Add tester credentials into teh controller. If already added, it will be ignored.
    # If you want to add a list of testers, you need to iterate through the list.
    await ctrl.add_tester(my_tester_credential)

    # Subscribe to test resource notifications.
    asyncio.create_task(subscribe(ctrl, channel_name=types.PIPE_RESOURCES))

    # Load your XOA 2544 config and run.
    with open(XOA_CONFIG, "r") as f:

        # Get rfc2544 test suite information from the core's registration
        info = ctrl.get_test_suite_info("RFC-2544")
        if not info:
            print("Test suite RFC-2544 is not recognized.")
            return None

        # Test suite name: "RFC-2544" is received from call of c.get_available_test_suites()
        test_exec_id = ctrl.start_test_suite("RFC-2544", json.load(f))

        # The example here only shows a print of test result data.
        asyncio.create_task(
            subscribe(ctrl, channel_name=test_exec_id, fltr={types.EMsgType.STATISTICS})
        )

    # By the next line, we prevent the script from being immediately
    # terminated as the test execution and subscription are non blockable, and they ran asynchronously,
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
