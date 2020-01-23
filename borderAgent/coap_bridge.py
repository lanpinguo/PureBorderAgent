import os
import sys
import time

here = sys.path[0]
sys.path.insert(0, os.path.join(here,'..'))

import threading
import binascii
from   coap   import	coap,							\
						coapResource,					\
						coapDefines		 as d,		\
						coapObjectSecurity  as oscoap
import logging_setup
from util import *

MOTE_IP = '' #fd00::212:4b00:1005:fdf3'

class mote():
	def __init__(self,ip,desc=''):
		self.ip = ip
		self.desc = desc
		
		

class bridge(threading.Thread):
	def __init__(self,ipAddress=''):
		# initialize the parent class
		threading.Thread.__init__(self)

		self.mote_list = {}
		self.bridge_ip = ''
		# open
		self.c = coap.coap(ipAddress=ipAddress)

		self.nbrResource = nbrResource(notify=self.setBridgeIp)

		# install resource
		self.c.addResource(self.nbrResource)
		
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
			
		print('%s' % (ip))
		self.mote_list[ip] = mote(ip)
		print(self.mote_list)
		
	def shutdown(self):
		self.active = False
		self.join()
		self.c.close()

	def get_nbr(self):
		try:

			# retrieve value of 'test' resource
			p = self.c.GET('coap://[%s]/nbr' % (self.bridge_ip),
					confirmable=True)

			var = get_post_variable(p)

			return(var['nbr'])
			
		except Exception as err:
			print("Exception")
			print(err)
			
			return None

	def get_sensor(self,sensor):
		try:

			# retrieve value of 'test' resource
			p = self.c.GET('coap://[%s]/%s' % (self.bridge_ip,sensor),
					confirmable=True)

			#print('=====')
			#print(''.join([chr(b) for b in p]))
			#print('=====')
			var = get_post_variable(p)
			print(var)
			
		except Exception as err:
			print("Exception")
			print(err)

	def run(self):
	
		while self.active:
			if self.bridge_ip != '':
				nbr = self.get_nbr()
				self.addNewMote(nbr)
			time.sleep(2)




class nbrResource(coapResource.coapResource):
	
	def __init__(self,notify=None):
		# initialize parent class
		coapResource.coapResource.__init__(self,path = 'nbr')
		self.notify = notify
		
	def GET(self,options=[]):
		print('GET received')
		
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
		print(var)
		if self.notify:
			self.notify(var['ip'],var['opt'])
			
		respCode		= d.COAP_RC_2_05_CONTENT
		respOptions	 = []
		respPayload	 = b'post process done'
		
		return (respCode,respOptions,respPayload)


if __name__ == '__main__':

	b = bridge(ipAddress = 'FD00::1')

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
