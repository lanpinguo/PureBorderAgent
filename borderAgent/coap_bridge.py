#!/usr/bin/python3

import os
import sys
import time
import select
import socket
import readline
import subprocess
import logging_setup
import json

here = sys.path[0]
sys.path.insert(0, os.path.join(here,'..'))

import threading
import binascii
from   coap   import    coap,                            \
                        coapResource,                    \
                        coapDefines         as d,        \
                        coapObjectSecurity  as oscoap
from util import *

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('bridgeAgent')
#log.setLevel(logging.ERROR)
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

# Accessory general defines
Accessory_Type_Other                 =  1
Accessory_Type_Bridges               =  2
Accessory_Type_Fans                  =  3
Accessory_Type_Garage_Door_Openers   =  4
Accessory_Type_Lighting              =  5
Accessory_Type_Locks                 =  6
Accessory_Type_Outlets               =  7
Accessory_Type_Switches              =  8
Accessory_Type_Thermostats           =  9
Accessory_Type_Sensors               = 10
Accessory_Type_Security_Systems      = 11
Accessory_Type_Doors                 = 12
Accessory_Type_Windows               = 13
Accessory_Type_Window_Coverings      = 14
Accessory_Type_Programmable_Switches = 15
Accessory_Type_Range_Extenders       = 16
Accessory_Type_IP_Cameras            = 17
Accessory_Type_Video_Doorbells       = 18
Accessory_Type_Air_Purifiers         = 19
Accessory_Type_Heaters               = 20
Accessory_Type_Air_Conditioners      = 21
Accessory_Type_Humidifiers           = 22
Accessory_Type_Dehumidifiers         = 23
Accessory_Type_Sprinklers            = 28
Accessory_Type_Faucets               = 29
Accessory_Type_Shower_Systems        = 30

AccessoryTempleteMap = {Accessory_Type_Lighting : 'GeneralTemplete.OpenSSL'}



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

        if ip in self.mote_list:
            return 
        print(ip)   
        log.debug('%s' % (ip))
        self.mote_list[ip] = HAP_ACCESSORY(ip,Accessory_Type_Lighting)
        time.sleep(1)
        self.mote_list[ip].StartAccessoryInstance()
        #print(self.mote_list)
        
    def shutdown(self):
        self.active = False
        self.join()
        self.coap.close()
        self.socket_handler.close()
        for acc in self.mote_list:
            self.mote_list[acc].shutdown()

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
            source    = conn
            #data      = [ord(b) for b in raw] #python2
            data      = raw  #python3
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

        print('Start poll sockets')
        self.check_period = 0
        while self.active:
            events = epoll.poll(TIMEOUT)
            if events :
                for fd, event in events:    
                    if event & select.EPOLLIN:   
                        sock = fd_to_socket[fd]
                        if self._socket_ready_handle(sock) != 0:
                            self.active = False
                            break

            if self.check_period > 0:
                self.check_period -= 1

            if self.bridge_ip != '' and self.check_period == 0:
                nbr = self.get_nbr()
                if nbr == 'NULL':
                    self.check_period = 5
                    continue
                self.addNewMote(nbr)




class nbrResource(coapResource.coapResource):
    
    def __init__(self,notify=None):
        # initialize parent class
        coapResource.coapResource.__init__(self,path = 'nbr')
        self.notify = notify
        
    def GET(self,options=[]):
        #print('GET received')
        
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = [ord(b) for b in 'hello world 1 2 3 4 5 6 7 8 9 0']
        
        return (respCode,respOptions,respPayload)

    def PUT(self,options,payload):
        
        #print('PUT received')
        #print('payload: ')
        #print(payload)
        
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = b'put process done'
        
        return (respCode,respOptions,respPayload)


    def POST(self,options,payload):
        
        #print('POST received')
        #print('payload: ')
        #print(payload)

        var = get_post_variable(payload)
        #print(var)
        if self.notify:
            self.notify(var['ip'],var['opt'])
            
        respCode        = d.COAP_RC_2_05_CONTENT
        respOptions     = []
        respPayload     = b'post process done'
        
        return (respCode,respOptions,respPayload)





class HAP_ACCESSORY():
    data_dir = b'data'

    def __init__(self,ip_addr,category):

        if isinstance(ip_addr, str):
            self.ip_addr = ip_addr.encode(encoding='utf8')
        else:
            self.ip_addr = ip_addr
        self.category = category
        self.hap_accessory_proc = None
        self.instanceKeyName = self.ip_addr.replace(b':',b'_')
        self.accessory_dir = os.path.abspath(os.path.join(
            os.getcwd().encode(encoding='utf8'),
            self.data_dir,
            self.instanceKeyName))
        self.CreateAccessoryInstance(self.ip_addr,category)

    def GetInstanceKeyName(self):
            return self.instanceKeyName


    def CreateAccessoryInstance(self,ip_address,category):
        
        accessory_base_info = {
            "aid":1,
            "category":5,
            "name":str(ip_address[6::],encoding='utf8'),
            "manufacturer":"Pure",
            "model":"LightBulb1,2",
            "serialNumber": str(ip_address[6::].replace(b':',b''),encoding='utf8'),
            "firmwareVersion":"1",
            "hardwareVersion":"1"
        }

        if not os.path.exists(self.data_dir) :
            os.mkdir(self.data_dir)

        accessory_dir = self.accessory_dir
        if os.path.exists(accessory_dir):
            log.warning("accessory_dir:%s exists" % accessory_dir)
            return

        os.mkdir(accessory_dir)
        self.accessory_dir = accessory_dir

        self.log = os.path.join(accessory_dir, b'running.log')

        accessory_store_dir = os.path.join(accessory_dir,b'.HomeKitStore')
        os.mkdir(accessory_store_dir)

        with open(os.path.join(accessory_store_dir,b'00.01'), 'w') as info_file:
            json.dump(accessory_base_info,info_file)
        
        #category = 5
        setupCode = '518-08-582'
        setupGenerator = os.path.join(os.getcwd(),"AccessorySetupGenerator_arm64")
        command = "%s --ip --category %d --setup-code \'%s\'" % (setupGenerator, category, setupCode)
        #print(command)
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        try:
            outs, errs = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()

        #print(outs.split(b'\n'))
        rc = proc.poll()
        if rc is None:
            return
        if rc != 0:
            return
        output = outs.split(b'\n')
        #print(output)
        #print(output[2])
        srpSalt = bytes.decode(output[2],encoding='utf8')
        srpVerifier= bytes.decode(output[3],encoding='utf8')
        setupID = output[4] + b'\0'

        with open(os.path.join(accessory_store_dir,b'40.10'), 'wb') as setupInfoFile:
            setupInfoFile.write(bytes.fromhex(srpSalt + srpVerifier))

        with open(os.path.join(accessory_store_dir,b'40.11'), 'wb') as setupIDFile:
            setupIDFile.write(setupID)



    def StartAccessoryInstance(self):
            if self.accessory_dir is None:
                log.error("accessory_dir is None")
                return
            if not os.path.exists(self.accessory_dir):
                log.error("accessory_dir:%s not exists" % self.accessory_dir)
                return

            if self.category not in AccessoryTempleteMap:
                log.error("Unsupported category:%d " % self.category)
                return 
 
            hap_templete_app = os.path.join(os.getcwd(),AccessoryTempleteMap[self.category])

            #command = "%s --root %s" % (hap_templete_app, self.accessory_dir.decode('utf8'))
            #print(command)
            #self.hap_accessory_proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            self.hap_accessory_proc = subprocess.Popen(hap_templete_app, cwd=self.accessory_dir, stdout=subprocess.PIPE)

    def ShowState(self):
        if self.hap_accessory_proc :
            rc = self.hap_accessory_proc.poll()
            if rc is None:
                return False
            if rc != 0:
                log.error('hap_accessory_proc exception : %ld' % rc)
            return True
        else:
            return True

    def ShowLog(self):
        try:
            outs, errs = self.hap_accessory_proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            outs, errs = self.hap_accessory_proc.communicate()
        return outs,errs

    def shutdown(self):
            self.hap_accessory_proc.kill()


if __name__ == '__main__':

    # Check data, log dirs, if not exist, then create them


    test_mote_ip = b'fd00::212:4b00:1005:fdf3'
    #os.mkdir(test_mote_ip)
    #os.rmdir(test_mote_ip)
    ss = None
    accIns = None

    b = bridgeAgent(ipAddress = 'FD00::1')

    #for t in threading.enumerate():
    #    print(t.name)

    try:
        while True:
            # let the server run
            i = input('coap>')
            if i == 'get':
                #print(i)
                b.get_sensor('nbr')
            elif i == 'sim':
                accIns = HAP_ACCESSORY(test_mote_ip, Accessory_Type_Lighting)
            elif i == 'start':
                if accIns:
                    accIns.StartAccessoryInstance()
            elif i == 'log':
                if accIns:
                    print(accIns.ShowState())
            elif i == 'dump':
                print(b.mote_list)
            elif i == 'exit':
                break
    except KeyboardInterrupt:
        print("key interrupt")

    b.shutdown()    
    if accIns:
        print('kill sub process ')
        accIns.shutdown()  

    print('exit')

    sys.exit(0)
