import os
import sys
import time
import select
import socket

here = sys.path[0]
sys.path.insert(0, os.path.join(here,'..'))

import threading
import binascii
from   coap   import	coap,							\
						coapResource,					\
						coapDefines		 as d,		\
						coapObjectSecurity  as oscoap
from util import *

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('bridgeAgent')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())


MOTE_IP = '' #fd00::212:4b00:1005:fdf3'
TIMEOUT = 2
class mote():
	def __init__(self,ip,desc=''):
		self.ip = ip
		self.desc = desc
		
		

class bridgeAgent(threading.Thread):
	BUFSIZE = 1024

	def __init__(self,ipAddress='',server_address = '/tmp/borderAgent'):
		# initialize the parent class
		threading.Thread.__init__(self)

		self.mote_list = {}
		self.bridge_ip = ''
		# open
		self.coap = coap.coap(ipAddress=ipAddress)

		self.nbrResource = nbrResource(notify=self.setBridgeIp)

		# install resource
		self.coap.addResource(self.nbrResource)
		
		
		
		# Make sure the socket does not already exist
		try:
			os.unlink(server_address)
		except OSError:
			if os.path.exists(server_address):
				raise
		# Create a UDS socket
		self.socket_handler = socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
		# Bind the socket to the port
		log.info(  'starting up on %s' % server_address)
		self.socket_handler.bind(server_address)



		self.active = True
		self.start()

	def setBridgeIp(self,ip,opt):
		if opt == '2':
			self.bridge_ip = ip
		

	def addNewMote(self,ip):
		if ip is None:
			return 
		elif ip == 'NULL':
			return
			
		log.debug('%s' % (ip))
		self.mote_list[ip] = mote(ip)
		#print(self.mote_list)
		
	def shutdown(self):
		self.active = False
		self.join()
		self.coap.close()
		self.socket_handler.close()

	def get_nbr(self):
		try:

			# retrieve value of 'test' resource
			p = self.coap.GET('coap://[%s]/nbr' % (self.bridge_ip),
					confirmable=True)

			var = get_post_variable(p)

			return(var['nbr'])
			
		except Exception as err:
			log.critical(err)
			
			return None

	def get_sensor(self,sensor):
		try:

			# retrieve value of 'test' resource
			p = self.coap.GET('coap://[%s]/%s' % (self.bridge_ip,sensor),
					confirmable=True)

			#print('=====')
			#print(''.join([chr(b) for b in p]))
			#print('=====')
			var = get_post_variable(p)
			#print(var)
			
		except Exception as err:
			log.critical((err))

	def get_motes(self):
		return self.mote_list

	def get(self,ip,res):
		try:

			# retrieve value of 'test' resource
			p = self.coap.GET('coap://[%s]/%s' % (ip,res),
					confirmable=True)

			print(p)
			return p
			
		except Exception as err:
			log.critical((err))
			return b''

	def post(self,ip,res,payload):
		try:

			# retrieve value of 'test' resource
			p = self.coap.PUT('coap://[%s]/%s' % (ip,res),
					confirmable=True,payload=payload)
			print(p)
			return p
			
		except Exception as err:
			log.critical((err))
			return b''

	def recv_handler(self,timestamp,source,data):
		option = data.split(b'/')
		print(option)
		opt = option[0].strip(b':')
		res_len = int(option[2].strip(b'[').strip(b']'))
		addr = option[3].strip(b'[').strip(b']')
		addr = ''.join([chr(b) for b in addr])
		res = option[4][0:res_len]
		res = ''.join([chr(b) for b in res])
		payload = option[4][res_len::]
		print(opt)
		print(addr)
		print(res)
		print(payload)
		result = b''
		if opt == b'post':
			result = self.post(addr,res,payload)
		self.socket_handler.sendto(result,source)

	#======================== private =========================================
	def _socket_ready_handle(self, s):
		"""
		Handle an input-ready socket

		@param s The socket object that is ready
		@returns 0 on success, -1 on error
		"""

		if s and s == self.socket_handler:
			try:
				# blocking wait for something from UDP socket
				raw,conn = self.socket_handler.recvfrom(self.BUFSIZE)
			except socket.error as err:
				log.critical("socket error: {0}".format(err))
				return -1
			else:
				if not raw:
					log.error("no data read from socket, stopping")
					return -1
				if not self.active:
					log.warning("active is false")
					return -1

			#print(conn)
			timestamp = time.time()
			source	= conn
			#data	  = [ord(b) for b in raw] #python2
			data	  = raw  #python3
			log.debug("got {2} from {1} at {0}".format(timestamp,source,data))
			#print("got {2} from {1} at {0}".format(timestamp,source,data))
			#call the process handler with the params
			self.recv_handler(timestamp,source,data)
		else:
			log.error("Unknown socket ready: " + str(s))
			return -1

		return 0



	def run(self):
		epoll = select.epoll()
		epoll.register(self.socket_handler.fileno(), select.EPOLLIN)
		fd_to_socket = {self.socket_handler.fileno():self.socket_handler,}


		while self.active:
			events = epoll.poll(TIMEOUT)
			if events :
				for fd, event in events:    
					if event & select.EPOLLIN:   
						sock = fd_to_socket[fd]
						if self._socket_ready_handle(sock) != 0:
							self.active = False
							break

			if self.bridge_ip != '':
				nbr = self.get_nbr()
				self.addNewMote(nbr)




class nbrResource(coapResource.coapResource):
	
	def __init__(self,notify=None):
		# initialize parent class
		coapResource.coapResource.__init__(self,path = 'nbr')
		self.notify = notify
		
	def GET(self,options=[]):
		#print('GET received')
		
		respCode		= d.COAP_RC_2_05_CONTENT
		respOptions	 = []
		respPayload	 = [ord(b) for b in 'hello world 1 2 3 4 5 6 7 8 9 0']
		
		return (respCode,respOptions,respPayload)

	def PUT(self,options,payload):
		
		#print('PUT received')
		#print('payload: ')
		#print(payload)
		
		respCode		= d.COAP_RC_2_05_CONTENT
		respOptions	 = []
		respPayload	 = b'put process done'
		
		return (respCode,respOptions,respPayload)


	def POST(self,options,payload):
		
		#print('POST received')
		#print('payload: ')
		#print(payload)

		var = get_post_variable(payload)
		#print(var)
		if self.notify:
			self.notify(var['ip'],var['opt'])
			
		respCode		= d.COAP_RC_2_05_CONTENT
		respOptions	 = []
		respPayload	 = b'post process done'
		
		return (respCode,respOptions,respPayload)


if __name__ == '__main__':
	import logging_setup
	b = bridgeAgent(ipAddress = 'FD00::1')

	#for t in threading.enumerate():
	#	print(t.name)

	try:
		while True:
			# let the server run
			i = input('#')
			if i == 'get':
				#print(i)
				b.get_sensor('nbr')
			elif i == 'exit':
				break
	except KeyboardInterrupt:
		print("key interrupt")
	b.shutdown()	
	sys.exit(0)
