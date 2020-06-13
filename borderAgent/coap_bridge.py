#!/usr/bin/python3

import os
import sys
import time
import select
import socket
import readline
<<<<<<< HEAD
import subprocess
import logging_setup
import json
=======
>>>>>>> a9cb1557c4c94789fc7a6f037d5022f18ec1f3b2

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

			#print(p)
			return p
			
		except Exception as err:
			log.critical((err))
			return b''

	def post(self,ip,res,payload):
		try:

			# retrieve value of 'test' resource
			p = self.coap.PUT('coap://[%s]/%s' % (ip,res),
					confirmable=True,payload=payload)
			#print(p)
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
		#print(opt)
		#print(addr)
		#print(res)
		#print(payload)
		result = b'this is echo for test'
		if opt == b'post':
			result = self.post(addr,res,payload)
		result += b"test"
		print(source)
		print(result)
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
				print(nbr)




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


def cmd(command,log):
	subp = subprocess.Popen(command,shell=False,stdout=log,stderr=subprocess.STDOUT)
	#subp.wait(2)
	#if subp.poll() == 0:
	#    print(subp.communicate()[1])
	#else:
	#    print("失败")
	return subp

def CreateAccessoryInstance(ip_address):
	data_dir = 'data'
	
	accessory_base_info = {
		"aid":1,
		"category":5,
		"name":"Pure Light Bulb",
		"manufacturer":"Pure",
		"model":"LightBulb1,2",
		"serialNumber":"02124b001005fdf3",
		"firmwareVersion":"1",
		"hardwareVersion":"1"
	}

	if not os.path.exists(data_dir) :
		os.mkdir(data_dir)

	accessory_dir = os.path.join(data_dir,ip_address)
	if os.path.exists(accessory_dir):
		return

	os.mkdir(accessory_dir)

	_log = open(os.path.join(accessory_dir, 'running.log'),'a')

	accessory_store_dir = os.path.join(accessory_dir,'.HomeKitStore')
	os.mkdir(accessory_store_dir)

	with open(os.path.join(accessory_store_dir,'00.01'), 'w') as info_file:
		json.dump(accessory_base_info,info_file)

	ret = subprocess.run(
		["AccessorySetupGenerator_arm64",
		 "--ip", "--category 5",
		  "--setup-code 518-08-582"],
		   capture_output=True)
	print(ret)

if __name__ == '__main__':

	# Check data, log dirs, if not exist, then create them


	test_mote_ip = 'fd00::212:4b00:1005:fdf3'
	#os.mkdir(test_mote_ip)
	#os.rmdir(test_mote_ip)
	ss = None


	b = bridgeAgent(ipAddress = 'FD00::1')

	#for t in threading.enumerate():
	#	print(t.name)

	try:
		while True:
			# let the server run
			i = input('coap>')
			if i == 'get':
				#print(i)
				b.get_sensor('nbr')
			elif i == 'sim':
				CreateAccessoryInstance(test_mote_ip)
				pass
			elif i == 'exit':
				break
	except KeyboardInterrupt:
		print("key interrupt")
	b.shutdown()	
	if ss:
		print('kill sub process ')
		ss.terminate()         
	print('exit')

	sys.exit(0)
