import socket
import time
import logging
from typing import Optional, Callable, Union, List, Dict, Any

class ServerUnavaliable(Exception):
	pass

class SimpleSocket(object):
	def __init__(self, hostname: str, port: int = 22611, timeout: int = 20) -> None:
		self.server_addr = (hostname, port)
		self.is_connected = False
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(timeout)
		self.retry_connect = 3
		self._connect()

	def __del__(self) -> None:
		self.sock.close()
	
	def _connect(self):
		try:
			if hasattr(self, "sock"):
				connid = 1
				err = self.sock.connect_ex(self.server_addr)
				if err == 0:
					self.retry_connect = 3
					self.is_connected = True
				else:
					self.re_connect()

		except socket.error as msg:
			logging.error(f"[Socket connection error] Cannot connect to { self.server_addr[0] }, error: {msg}\n")
			self.re_connect()

	def re_connect(self):
		time.sleep(5)
		self.retry_connect -= 1
		if self.retry_connect > 0:
			self._connect()
		else:
			raise ServerUnavaliable(f'Cannot connect to <{ self.server_addr[0] }>, host is unavailable')

	def close(self):
		if hasattr(self, "sock"):
			self.sock.close()
			
	# Send a string command to a socket
	def send(self, cmd: str) -> None:
		"""Send a command string to server, ignores the response.

		:param cmd: The command to send.
		:type cmd: str
		:return: None
		:rtype: None
		:raises RuntimeError: If the socket connection is broken.
		"""
		if hasattr(self, "sock") and self.is_connected:
			sent = self.sock.send((cmd + '\n').encode('utf-8'))
			if sent == 0:
				raise RuntimeError("Socket connection broken")

	# Send a string command to a socket and return a string response from the socket
	def send_with_resp(self, cmd: str, check_terminator = True) -> str:
		"""Sends the command to server and returns the response.

		:param cmd: The command to send.
		:type cmd: str
		:param check_terminator: Whether to check for the response terminator, defaults to True
		:type check_terminator: bool, optional
		:raises RuntimeError: If the socket connection is broken.
		:return: The response from the server.
		:rtype: str
		"""
		if hasattr(self, "sock") and self.is_connected:
			try:
				sent = self.sock.send((cmd + '\n').encode('utf-8'))
				if sent == 0:
					raise RuntimeError("Socket connection broken")
				tmp = self.sock.recv(4096)
				print(f"#1 {tmp.decode('utf_8')}")
				while tmp == b'' or not tmp.decode('utf_8').endswith('<SYNC>\n'):
					tmp = tmp + self.sock.recv(4096)
					print(f"#2 {tmp.decode('utf_8')}")
				return tmp.decode('utf_8')
			except socket.error as msg:
				logging.error(f"[Socket connection error] { msg }")
				return ''
		return ''

	# Send a long string data to the socket and return a long string of response from the socket
	def send_list_with_resp(self, cmds: list[str]) -> list[str]:
		"""Sends a list of commands to server and returns the responses.

		:param cmds: The list of commands to send.
		:type cmds: list[str]
		:raises ValueError: If cmds is not a list.
		:return: The response from the server.
		:rtype: list[str]
		"""
		if not isinstance(cmds, list):
			raise ValueError('\'cmds\' - must be a instance of list')
		
		cmd = ''.join(cmds) + '\n'
		
		if hasattr(self, "sock") and self.is_connected:
			try:
				self.sock.sendall((cmd).encode('utf-8'))
				data = self.sock.recv(4096)
				while not data:
					data = self.sock.recv(4096)
				_resps = data.decode('utf_8')
				while True:
					if _resps.count('\n') < len(cmds):
						data2 = self.sock.recv(4096).decode('utf_8')
						if data2:
							_resps = _resps + data2
					else:
						break
				# def mapper(v): return f"{ v[0] }: { v[1] }"
				# resps = "\n".join( list( map(mapper, list( zip(cmds, _resps.split('\n')) ) ) ) )
				resps = _resps.split('\n')[:-1]
				return resps
			except socket.error as msg:
				logging.error(f"[Socket connection error] { msg }")
				return ['']
		return ['']
	
	def set_keepalives(self):
		if hasattr(self, "sock") and self.is_connected:
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 2)
