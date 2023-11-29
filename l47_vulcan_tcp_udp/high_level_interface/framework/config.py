import os
import typing
from xoa_driver import enums

def _from_string(cls, params: str, divider: str = "/"):
    return cls(*map(int, params.split(divider)))

class PortInfo(typing.NamedTuple):
    module_id: int
    port_id: int

    def __repr__(self) -> str:
        return f"{self.module_id}/{self.port_id}"

class LPShape(typing.NamedTuple):
    star_time: int
    rampup_duration: int
    steady_duration: int
    rampdown_duration: int
    
    @property
    def duration(self) -> int:
        return sum(self)
    
    @property
    def duration_in_seconds(self) -> float:
        return self.duration / 1000
    
    def to_seconds(self) -> typing.Tuple[float, float, float, float]:
        return tuple(map(lambda v: v / 1000, self))


class CRange(typing.NamedTuple):
    ipv4_address: str
    address_count: int 
    start_port: int = 100
    port_count: int = 1
    max_address_count: int = 9999999


class SRange(typing.NamedTuple):
    ipv4_address: str 
    address_count: int = 1
    start_port: int = 5000
    port_count: int = 1

DEBUG = "DEBUG"
SAMPLING_RATE = "SAMPLING_RATE"
CHASSIS_IP_ADDR = "CHASSIS_IP_ADDR"
CHASSIS_OWNER = "CHASSIS_OWNER"
CHASSIS_PWD = "CHASSIS_PWD"
CHASSIS_PE_NUM = "CHASSIS_PE_NUM"
CHASSIS_PORT_C = "CHASSIS_PORT_C"
CHASSIS_PORT_S = "CHASSIS_PORT_S"
CG_ID = "CG_ID"
IP_VER = "IP_VER"
LP = "LP"
C_STARTIP  = "C_STARTIP"
S_STARTIP = "S_STARTIP"
C_CONNS = "C_CONNS"
SPEED = "SPEED"
UDP_TYPE = "UDP_TYPE"
UDP_SIZE = "UDP_SIZE"

class ConfigurationLoader:
    def __init__(self) -> None:
        self.__load()
        self.debug = "true" == os.environ.get(DEBUG, "false")
        self.sampling_rate = int(os.environ.get(SAMPLING_RATE, "1"))
        
        self.chassis_ip = os.environ[CHASSIS_IP_ADDR]
        self.chassis_owner = os.environ[CHASSIS_OWNER]
        self.chassis_pwd = os.environ[CHASSIS_PWD]
        self.chassis_pe_num = int(os.environ[CHASSIS_PE_NUM])
        self.chassis_port_c = _from_string(PortInfo, os.environ[CHASSIS_PORT_C])
        self.chassis_port_s = _from_string(PortInfo, os.environ[CHASSIS_PORT_S])

        self.cg_id = int(os.environ.get(CG_ID, "0"))
        self.ip_ver = enums.L47IPVersion( int(os.environ.get(IP_VER, "4")) )
        self.lp = _from_string(LPShape, os.environ[LP], divider=" ")
        self.c_startip = os.environ[C_STARTIP]
        self.s_startip = os.environ[S_STARTIP]
        self.c_conns = int(os.environ[C_CONNS])
        self.speed = enums.PortSpeedMode[os.environ.get(SPEED, "F10G")]
        
        self.c_range =  CRange(self.c_startip, int(self.c_conns))
        self.s_range =  SRange(self.s_startip)
        
        try:
            self.udp_type = enums.MSSType[os.environ[UDP_TYPE]]
        except KeyError as e:
            values = [ v.name for v in enums.MSSType ]
            print(f"UDP_TYPE can be represented only by one of: {values}")
            raise e
        self.udp_size = int(os.environ.get(UDP_SIZE, "1"))

    def __load(self) -> None:
        lookup_path = os.path.abspath(os.getcwd())
        env_file_path = os.path.join(lookup_path, ".env")
        if not os.path.isfile(env_file_path):
            return None
        
        print("Load config from .env")
        with open(env_file_path) as f:
            for line in f:
                if line.startswith("#") or line.startswith(" ") or line.startswith("\n"):
                    continue
                key, value = line.split("=")
                os.environ[key.strip()] = value.replace("\n", "").strip()