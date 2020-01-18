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

SERVER_IP = 'fd00::212:4b00:1005:fdf3'

print(SERVER_IP)
# open
c = coap.coap(udpPort=56783)

context = oscoap.SecurityContext(masterSecret=binascii.unhexlify('000102030405060708090A0B0C0D0E0F'),
                                 senderID=binascii.unhexlify('636c69656e74'),
                                 recipientID=binascii.unhexlify('736572766572'),
                                 aeadAlgorithm=oscoap.AES_CCM_16_64_128())

objectSecurity = o.ObjectSecurity(context=context)

try:
    # retrieve value of 'test' resource
    p = c.GET('coap://[{0}]/.well-known/core'.format(SERVER_IP),
              confirmable=True)

    print('=====')
    print(''.join([chr(b) for b in p]))
    print('=====')

    # retrieve value of 'test' resource
    p = c.GET('coap://[{0}]/nbr'.format(SERVER_IP),
              confirmable=True)

    print('=====')
    print(''.join([chr(b) for b in p]))
    print('=====')

    # retrieve value of 'test' resource
    p = c.GET('coap://[{0}]/sw'.format(SERVER_IP),
              confirmable=True)

    print('=====')
    print(''.join([chr(b) for b in p]))
    print('=====')


except Exception as err:
    print("Exception")
    print(err)



# close
c.close()

time.sleep(0.500)

#input("Done. Press enter to close.")
