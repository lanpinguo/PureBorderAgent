import os
import sys
here = sys.path[0]
sys.path.insert(0, os.path.join(here,'..'))

import time
import binascii

from coap import coap
from coap import coapOption           as o
from coap import coapObjectSecurity   as oscoap

#import logging_setup


def set_actuator(c,target,payload):
	try:
		# retrieve value of 'test' resource
		p = c.PUT('coap://[{0}]/relay-sw'.format(target),
				  confirmable=True,payload=payload)

		print('=====')
		print(''.join([chr(b) for b in p]))
		print('=====')

	except Exception as err:
		print("Exception")
		print(err)

def get_sensor(c,target):
	try:
		# retrieve value of 'test' resource
		p = c.GET('coap://[{0}]/hcho'.format(target),
				  confirmable=True)

		print('=====')
		print(''.join([chr(b) for b in p]))
		print('=====')
	except Exception as err:
		print("Exception")
		print(err)

if __name__ == '__main__':
	#SERVER_IP = 'fd00::212:4b00:1005:fdf1'
	SERVER_IP = 'fd00::212:4b00:18f1:d9d2'
	#SERVER_IP = 'fd00::0212:4b00:1940:c0e3'
	print(SERVER_IP)
	# open
	c = coap.coap(udpPort=5683)

	context = oscoap.SecurityContext(masterSecret=binascii.unhexlify('000102030405060708090A0B0C0D0E0F'),
									 senderID=binascii.unhexlify('636c69656e74'),
									 recipientID=binascii.unhexlify('736572766572'),
									 aeadAlgorithm=oscoap.AES_CCM_16_64_128())

	objectSecurity = o.ObjectSecurity(context=context)


	while True:
		raw_in = input('mote#')
		args = raw_in.split()
		if len(args) == 0:
			continue
		cmd = args[0]
		if cmd == 'hcho':
			SERVER_IP = 'fd00::212:4b00:18f1:d9d2'
			get_sensor(c,SERVER_IP)
		elif cmd == 'fish':
			#fish jar control
			SERVER_IP = 'fd00::0212:4b00:1940:c0e3'
			if len(args) < 2:
				print('too short parameter')
				continue

			mask = 0
			if len(args) == 3:
				if args[1] == 'all':
					mask = ((1<<0)|(1<<1)|(1<<2)|(1<<3))
				else:
					try :
						index = int(args[1])
					except Exception as err:
						print(err)
						continue
					if index >= 4 :
						print("Wrong Mask Parameter")
						continue
					mask = (1<<index)

			state = args[2]
			if state == 'on':
				payload = b"&state=%lx&mask=%lx" % (mask,mask)
			elif state == 'off':
				payload = b"&state=%lx&mask=%lx" % ((~mask) & 0xFFFFFFFF,mask)
			else:
				print('Wrong State Parameter')
				continue
			print(payload)
			set_actuator(c,SERVER_IP,payload)
		elif cmd == 'exit':
			break

	# close
	c.close()

