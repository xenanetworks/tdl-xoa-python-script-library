from socket import inet_aton, inet_ntoa
import base64
import struct

def inet_ntoaX(data):
    return ['.'.join(map(str, data[i:i + 4])) for i in range(0, len(data), 4)]

def inet_atonX(ips):
    return b''.join(map(inet_aton, ips))

def macunpack(data):
    s = base64.b16encode(data)
    return ':'.join([s[i:i+2].decode('ascii') for i in range(0, 12, 2)])

def macpack(mac):
    return base64.b16decode(mac.replace(':', '').replace('-', '').encode('ascii'))

def unpackbool(data):
    return data[0]

def packbool(bool):
    return bytes([bool])

def ip_addresses(network, subnet_mask):
    import socket, struct
    subnet_mask = struct.unpack('>I', socket.inet_aton(subnet_mask))[0]
    network = struct.unpack('>I', socket.inet_aton(network))[0]
    network = network & subnet_mask
    start = network + 1
    end = (network | (~subnet_mask & 0xffffffff))
    return (socket.inet_ntoa(struct.pack('>I', i)) for i in range(start, end))

class ALL(object):
    def __eq__(self, other):
        return True
    def __repr__(self):
        return self.__class__.__name__
    
class GREATER(object):
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return type(self.value)(other) > self.value

class NETWORK(object):
    def __init__(self, network, subnet_mask):
        self.subnet_mask = struct.unpack('>I', inet_aton(subnet_mask))[0]
        self.network = struct.unpack('>I', inet_aton(network))[0]
    def __eq__(self, other):
        ip = struct.unpack('>I', inet_aton(other))[0]
        return  ip & self.subnet_mask == self.network and \
                ip - self.network and \
                ip - self.network != ~self.subnet_mask & 0xffffffff
        
class CASEINSENSITIVE(object):
    def __init__(self, s):
        self.s = s.lower()
    def __eq__(self, other):
        return self.s == other.lower()