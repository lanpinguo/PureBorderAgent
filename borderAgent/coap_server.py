import os
import sys
here = sys.path[0]
sys.path.insert(0, os.path.join(here,'..'))

import threading
import binascii
from   coap   import    coap,                            \
                        coapResource,                    \
                        coapDefines         as d,        \
                        coapObjectSecurity  as oscoap
import logging_setup

MOTE_IP = 'fd00::212:4b00:1005:fdf3'


def get_test():
    try:

        # retrieve value of 'test' resource
        p = c.GET('coap://[{0}]/nbr'.format(MOTE_IP),
                confirmable=True)

        print('=====')
        print(''.join([chr(b) for b in p]))
        print('=====')

    except Exception as err:
        print("Exception")
        print(err)



class nbrResource(coapResource.coapResource):
    
    def __init__(self):
        # initialize parent class
        coapResource.coapResource.__init__(
            self,
            path = 'nbr',
        )
    
    def GET(self,options=[]):
        
        print('GET received')
        
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = [ord(b) for b in 'hello world 1 2 3 4 5 6 7 8 9 0']
        
        return (respCode,respOptions,respPayload)

    def PUT(self,options,payload):
        
        print('PUT received')
        print('payload: ')
        print(payload)
        
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = b'put process done'
        
        return (respCode,respOptions,respPayload)


    def POST(self,options,payload):
        
        print('POST received')
        print('payload: ')
        print(payload)
        
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = b'post process done'
        
        return (respCode,respOptions,respPayload)

# open
c = coap.coap(ipAddress='fd00::1')

nbrResource = nbrResource()

context = oscoap.SecurityContext(masterSecret   = binascii.unhexlify('000102030405060708090A0B0C0D0E0F'),
                                 senderID       = binascii.unhexlify('736572766572'),
                                 recipientID    = binascii.unhexlify('636c69656e74'),
                                 aeadAlgorithm  = oscoap.AES_CCM_16_64_128())

# add resource - context binding with authorized methods
#nbrResource.addSecurityBinding((context, d.METHOD_ALL))

# install resource
c.addResource(nbrResource)

for t in threading.enumerate():
    print(t.name)

try:
    while True:
        # let the server run
        i = input('#')
        if i == 'get':
            #print(i)
            get_test()
        elif i == 'exit':
            break
except KeyboardInterrupt:
    print("key interrupt")
    
# close
c.close()
sys.exit(0)
