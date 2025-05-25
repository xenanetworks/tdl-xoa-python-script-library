
import time
from .utils import ALL
from typing import List

class CSVDatabase(object):
    delimiter = ';'
    def __init__(self, file_name):
        self.file_name = file_name
        self.file('w').close() # create file

    def file(self, mode = 'r'):
        return open(self.file_name, mode)

    def get(self, pattern):
        pattern = list(pattern)
        return [line for line in self.all() if pattern == line]

    def add(self, line):
        with self.file('a') as f:
            f.write(self.delimiter.join(line) + '\n')

    def delete(self, pattern):
        lines = self.all()
        lines_to_delete = self.get(pattern)
        self.file('w').close() # empty file
        for line in lines:
            if line not in lines_to_delete:
                self.add(line)

    def all(self):
        with self.file() as f:
            return [list(line.strip().split(self.delimiter)) for line in f]

class Host(object):
    def __init__(self, mac, ip, hostname, last_used):
        self.mac = mac.upper()
        self.ip = ip
        self.hostname = hostname
        self.last_used = int(last_used)

    @classmethod
    def from_tuple(cls, line):
        mac, ip, hostname, last_used = line
        last_used = int(last_used)
        return cls(mac, ip, hostname, last_used)

    @classmethod
    def from_packet(cls, packet):
        return cls( packet.client_mac_address,
                    packet.requested_ip_address or packet.client_ip_address,
                    packet.host_name or '',
                    int(time.time()) )

    @staticmethod
    def get_pattern(mac = ALL, ip = ALL, hostname = ALL, last_used = ALL):
        return [mac, ip, hostname, last_used]

    def to_tuple(self):
        return [self.mac, self.ip, self.hostname, str(int(self.last_used))]

    def to_pattern(self):
        return self.get_pattern(ip = self.ip, mac = self.mac)

    def __hash__(self):
        return hash((self.mac, self.ip, self.hostname, self.last_used))

    def __eq__(self, other):
        return self.to_tuple() == other.to_tuple()

    def has_valid_ip(self):
        return self.ip and self.ip != '0.0.0.0'
        
class HostDatabase(object):
    def __init__(self, file_name):
        self.db = CSVDatabase(file_name)

    def get(self, **kw):
        pattern = Host.get_pattern(**kw)
        return list(map(Host.from_tuple, self.db.get(pattern)))

    def add(self, host):
        self.db.add(host.to_tuple())

    def delete(self, host = None, **kw):
        if host is None:
            pattern = Host.get_pattern(**kw)
        else:
            pattern = host.to_pattern()
        self.db.delete(pattern)

    def all(self):
        return list(map(Host.from_tuple, self.db.all()))

    def replace(self, host):
        self.delete(host)
        self.add(host)
        
def sorted_hosts(hosts: List[Host]) -> List[Host]:
    hosts = list(hosts)
    hosts.sort(key = lambda host: (host.hostname.lower(), host.mac.lower(), host.ip.lower()))
    return hosts