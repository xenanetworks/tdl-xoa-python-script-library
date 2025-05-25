from xoa_driver import ports

from .xsocket import XSocket
import time
import threading

import queue
import collections
import traceback

from .utils import *
from .host import *
from .bootp_packet import *


class DelayWorker(object):
    def __init__(self):
        self.closed = False
        self.queue = queue.Queue()
        self.thread = threading.Thread(target = self._delay_response_thread)
        self.thread.start()

    def _delay_response_thread(self):
        while not self.closed:
            if self.closed:
                break
            try:
                p = self.queue.get(timeout=1)
                t, func, args, kw = p
                now = time.time()
                if now < t:
                    time.sleep(0.01)
                    self.queue.put(p)
                else:
                    func(*args, **kw)
            except queue.Empty: 
                continue

    def do_after(self, seconds, func, args = (), kw = {}):
        self.queue.put((time.time() + seconds, func, args, kw))

    def close(self):
        self.closed = True

class Transaction(object):
    def __init__(self, server):
        self.server         = server
        self.configuration  = server.configuration
        self.packets        = []
        self.done_time      = time.time() + self.configuration.length_of_transaction
        self.done           = False
        self.do_after       = self.server.delay_worker.do_after
        self.smac           = ""
        self.dmac           = ""
        
    def is_done(self):
        return self.done or self.done_time < time.time()

    def close(self):
        self.done = True

    async def receive(self, packet):
        self.smac = packet.smac
        self.dmac = packet.dmac
        # packet from client <-> packet.message_type == 1
        if packet.message_type == 1 and packet.dhcp_message_type == 'DHCPDISCOVER':
            await self.received_dhcp_discover(packet,)
        elif packet.message_type == 1 and packet.dhcp_message_type == 'DHCPREQUEST':
            await self.received_dhcp_request(packet,)
        elif packet.message_type == 1 and packet.dhcp_message_type == 'DHCPINFORM':
            self.received_dhcp_inform(packet)
        else:
            return False
        return True

    async def received_dhcp_discover(self, discovery):
        if self.is_done(): return
        self.configuration.debug('discover:\n {}'.format(str(discovery).replace('\n', '\n\t')))
        await self.send_offer(discovery)

    async def send_offer(self, discovery):
        # https://tools.ietf.org/html/rfc2131
        offer = WriteBootProtocolPacket(self.configuration)
        offer.parameter_order = discovery.parameter_request_list
        mac = discovery.client_mac_address
        ip = offer.your_ip_address = self.server.get_ip_address(discovery)
        # offer.client_ip_address = 
        offer.transaction_id = discovery.transaction_id
        # offer.next_server_ip_address =
        offer.relay_agent_ip_address = discovery.relay_agent_ip_address
        offer.client_mac_address = mac
        offer.client_ip_address = discovery.client_ip_address or '0.0.0.0'
        offer.bootp_flags = discovery.bootp_flags
        offer.message_type = reversed_dhcp_message_types['DHCPOFFER']
        offer.client_mac_address = mac
        offer.smac = self.server.port_mac_address
        offer.dmac = self.smac
        offer.server_identifier = self.server.server_identifier
        await self.server.send_response(offer)
    
    async def received_dhcp_request(self, request):
        if self.is_done(): return 
        self.server.client_has_chosen(request)
        await self.acknowledge(request)
        self.close()

    async def acknowledge(self, request):
        ack = WriteBootProtocolPacket(self.configuration)
        ack.parameter_order = request.parameter_request_list
        ack.transaction_id = request.transaction_id
        # ack.next_server_ip_address =
        ack.bootp_flags = request.bootp_flags
        ack.relay_agent_ip_address = request.relay_agent_ip_address
        mac = request.client_mac_address
        ack.client_mac_address = mac
        requested_ip_address = request.requested_ip_address
        ack.client_ip_address = request.client_ip_address or '0.0.0.0'
        ack.your_ip_address = self.server.get_ip_address(request)
        ack.message_type = reversed_dhcp_message_types['DHCPACK']
        ack.smac = self.server.port_mac_address
        ack.dmac = self.smac
        ack.server_identifier = self.server.server_identifier
        await self.server.send_response(ack)

    def received_dhcp_inform(self, inform):
        self.close()
        self.server.client_has_chosen(inform)

class DHCPServerConfiguration(object):
    
    length_of_transaction = 40
    network = '192.168.173.0'
    broadcast_address = '255.255.255.255'
    subnet_mask = '255.255.255.0'
    router = None # list of ips
    server_identifier = "192.168.173.100"
    ip_address_lease_time = 300 # seconds
    domain_name_server = None # list of ips
    host_file = 'hosts.csv'
    debug = lambda *args, **kw: None

    def load(self, file):
        with open(file) as f:
            exec(f.read(), self.__dict__)

    def all_ip_addresses(self):
        ips = ip_addresses(self.network, self.subnet_mask)
        for i in range(5):
            next(ips)
        return ips

    def network_filter(self):
        return NETWORK(self.network, self.subnet_mask)

class DHCPServer(object):
    def __init__(self, port: ports.GenericL23Port, configuration: DHCPServerConfiguration | None):
        
        if configuration is None:
            self.configuration = DHCPServerConfiguration()
        else:
            self.configuration = configuration
        
        self.port = port
        self.__xsocket = XSocket(self.port, filter_type=XSocket.FilterType.DhcpServer)
        self.delay_worker = DelayWorker()
        self.closed = False
        self.transactions = collections.defaultdict(lambda: Transaction(self)) # id: transaction
        self.hosts = HostDatabase(self.configuration.host_file)
        self.time_started = time.time()
        self.port_mac_address = ""
        self.server_identifier = self.configuration.server_identifier

    async def close(self):
        await self.__xsocket.stop()
        self.closed = True
        self.delay_worker.close()
        for transaction in list(self.transactions.values()):
            transaction.close()

    async def update(self, timeout = 0):
        # 1- try to receive from xsocket
        ret_error, data = await self.__xsocket.receive_packet()
        if ret_error == XSocket.Error.Success and data and len(data) != 0:
            packet = ReadBootProtocolPacket(data)
            await self.received(packet)
        for transaction_id, transaction in list(self.transactions.items()):
            if transaction.is_done():
                transaction.close()
                self.transactions.pop(transaction_id)

    async def received(self, packet):
        if not await self.transactions[packet.transaction_id].receive(packet):
            self.configuration.debug('received:\n {}'.format(str(packet).replace('\n', '\n\t')))
            
    def client_has_chosen(self, packet):
        self.configuration.debug('client_has_chosen:\n {}'.format(str(packet).replace('\n', '\n\t')))
        host = Host.from_packet(packet)
        if not host.has_valid_ip():
            return
        self.hosts.replace(host)

    def is_valid_client_address(self, address):
        if address is None:
            return False
        a = address.split('.')
        s = self.configuration.subnet_mask.split('.')
        n = self.configuration.network.split('.')
        return all(s[i] == '0' or a[i] == n[i] for i in range(4))

    def get_ip_address(self, packet):
        mac_address = packet.client_mac_address
        requested_ip_address = packet.requested_ip_address
        known_hosts = self.hosts.get(mac = CASEINSENSITIVE(mac_address))
        assigned_addresses = set(host.ip for host in self.hosts.get())
        ip = None
        if known_hosts:
            # 1. choose known ip address
            for host in known_hosts:
                if self.is_valid_client_address(host.ip):
                    ip = host.ip
        if ip is None and self.is_valid_client_address(requested_ip_address) and ip not in assigned_addresses:
            # 2. choose valid requested ip address
            ip = requested_ip_address
        if ip is None:
            # 3. choose new, free ip address
            chosen = False
            network_hosts = self.hosts.get(ip = self.configuration.network_filter())
            for ip in self.configuration.all_ip_addresses():
                if not any(host.ip == ip for host in network_hosts):
                    chosen = True
                    break
            if not chosen:
                # 4. reuse old valid ip address
                network_hosts.sort(key = lambda host: host.last_used)
                ip = network_hosts[0].ip
                assert self.is_valid_client_address(ip)
        if not any([host.ip == ip for host in known_hosts]):
            self.hosts.replace(Host(mac_address, ip, packet.host_name or '', time.time()))
        return ip

    async def send_response(self, packet):
        self.configuration.debug('broadcasting:\n {}'.format(str(packet).replace('\n', '\n\t')))
        await self.__xsocket.send_packet(packet.to_bytes())
    
    @staticmethod
    def hex_to_mac_address(hex_string: str):
        mac_address = ':'.join(hex_string[i:i+2] for i in range(0, 12, 2))
        return mac_address

    async def run(self):
        ret = await self.port.net_config.mac_address.get()
        self.port_mac_address = DHCPServer.hex_to_mac_address(ret.mac_address)
        await self.__xsocket.start()
        
        while not self.closed:
            try:
                await self.update(1)
            except KeyboardInterrupt:
                break
            except:
                traceback.print_exc()

    def run_in_thread(self):
        thread = threading.Thread(target = self.run)
        thread.start()
        return thread

    def debug_clients(self):
        for host in self.hosts.all():
            line = '\t'.join(host.to_tuple())
            if line:
                self.configuration.debug(line)

    def get_all_hosts(self):
        return sorted_hosts(self.hosts.get())

    def get_current_hosts(self):
        return sorted_hosts(self.hosts.get(last_used = GREATER(self.time_started)))

