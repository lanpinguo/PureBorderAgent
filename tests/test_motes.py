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

motes_ip = { 'fish'      :'fd00::0212:4b00:1940:c0e3',
			'front_light':'fd00::212:4b00:18f1:d9d2',
			'back_light' : 'fd00::0212:4b00:1940:c17a'}



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

def cmd_sw_config(coap,mote,args):
	if len(args) < 1:
		print('too short parameter')
		return 1

	mask = 0
	if len(args) == 2:
		if args[0] == 'all':
			mask = 0xFFFFFFFF
		else:
			try :
				index = int(args[0])
			except Exception as err:
				print(err)
				return 2
			if index >= 8 :
				print("Wrong Mask Parameter")
				return 3
			mask = (1<<index)

	state = args[1]
	if state == 'on':
		payload = b"&state=%lx&mask=%lx" % (mask,mask)
	elif state == 'off':
		payload = b"&state=%lx&mask=%lx" % ((~mask) & 0xFFFFFFFF,mask)
	else:
		print('Wrong State Parameter')
		return 4
	print(payload)
	set_actuator(coap,mote,payload)
	return 0


def cmd_parser(coap,args):
	if len(args) == 0:
		return 0
	cmd = args[0]
	if cmd == 'hcho':
		mote = motes_ip['front_light']
		get_sensor(coap,mote)
	elif cmd == 'fish':
		#fish jar control
		mote = motes_ip['fish']
		result = cmd_sw_config(coap,mote,args[1::])
		return result
	elif cmd == 'front':
		#fish jar control
		mote = motes_ip['front_light']
		result = cmd_sw_config(coap,mote,args[1::])
		return result
	elif cmd == 'back':
		#fish jar control
		mote = motes_ip['back_light']
		result = cmd_sw_config(coap,mote,args[1::])
		return result
	elif cmd == 'exit':
		return -1
	return 0

if __name__ == '__main__':
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
		result = cmd_parser(c,args)
		print("cmd exec result: %d" % result)
		if result < 0:
			break
	# close
	c.close()

