from xenaasyncwrapper import XenaAsyncWrapper
import time
from xoa_driver.hlfuncs import mgmt, cli
from xoa_driver.misc import Hex
from xoa_driver import utils
from xoa_driver import enums
from xoa_driver import ports
from xoa_driver import modules
from xoa_driver import testers
from robot.api.deco import library, keyword, not_keyword

@library(scope="GLOBAL", auto_keywords=False)
class XOARobot:
    """
    Xena OpenAutomation Robot class
    This class connects to only one chassis at initialization.
    """

    @keyword("Connect Chassis")
    def connect_chassis(self, host: str, username: str = "xoa-robot", password: str = "xena", port: int = 22606, enable_logging: bool = False) -> None:
        self.xaw = XenaAsyncWrapper()
        # check if it starts to work
        while not self.xaw.is_thread_started():
            time.sleep(0.01)
        self.tester = self.xaw(testers.L23Tester(host=host, username=username, password=password, port=port, enable_logging=enable_logging))

    @keyword("Reserve Chassis")
    def reserve_chassis(self):
        for m in self.tester.modules:
            self.xaw(mgmt.release_module(module=m, should_release_ports=True))
        self.xaw(mgmt.reserve_tester(tester=self.tester))

    @keyword("Disconnect Chassis")
    def disconnect_chassis(self):
        self.xaw(self.tester.session.logoff())
        self.xaw.close()

    @keyword("Reserve Module")
    def reserve_module(self, port_id: str):
        _mid = int(port_id.split("/")[0])
        module = self.tester.modules.obtain(_mid)
        for p in module.ports:
            self.xaw(mgmt.release_port(port=p))
        self.xaw(mgmt.reserve_module(module=module))
    
    @keyword("Release Module")
    def release_module(self, port_id: str):
        _mid = int(port_id.split("/")[0])
        module = self.tester.modules.obtain(_mid)
        self.xaw(mgmt.release_module(module=module))

    @keyword("Reserve Port")
    def reserve_port(self, port_id: str):
        _mid = int(port_id.split("/")[0])
        _pid = int(port_id.split("/")[1])
        module = self.tester.modules.obtain(_mid)
        self.xaw(mgmt.release_tester(tester=self.tester))
        self.xaw(mgmt.release_module(module=module))
        port = module.ports.obtain(_pid)
        self.xaw(mgmt.reserve_port(port=port))

    @keyword("Reset Port")
    def reset_port(self, port_id: str):
        _mid = int(port_id.split("/")[0])
        _pid = int(port_id.split("/")[1])
        module = self.tester.modules.obtain(_mid)
        self.xaw(mgmt.release_module(module=module, should_release_ports=True))
        port = module.ports.obtain(_pid)
        self.xaw(mgmt.reset_port(port=port))

    @keyword("Release Port")
    def release_port(self, port_id: str):
        _mid = int(port_id.split("/")[0])
        _pid = int(port_id.split("/")[1])
        module = self.tester.modules.obtain(_mid)
        port = module.ports.obtain(_pid)
        self.xaw(mgmt.release_port(port=port))

    @keyword("Get Port Description")
    def get_port_description(self, port_id: str) -> str:
        _mid = int(port_id.split("/")[0])
        _pid = int(port_id.split("/")[1])
        module = self.tester.modules.obtain(_mid)
        port = module.ports.obtain(_pid)
        resp = self.xaw(port.comment.get())
        return resp.comment


