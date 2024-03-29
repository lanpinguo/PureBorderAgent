#!/usr/bin/python3

import os
import sys
import time
import select
import socket
import readline
import subprocess
#import logging_setup
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
#log.setLevel(logging.DEBUG)
#log.addHandler(NullHandler())

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

AccessoryTempleteMap = {
    Accessory_Type_Lighting : 'GeneralTemplete_armv7l.OpenSSL',
    Accessory_Type_Sensors : 'GeneralTemplete_armv7l.OpenSSL',
    Accessory_Type_Switches : 'GeneralTemplete_armv7l.OpenSSL'
    }

# mote capability list
MoteCapabilityList = {
    'Sensor-1,0' : {'services' : [  {'type' : 'temperature', 'number' : 1},
                                    {'type' : 'humidity', 'number' : 1}
                                 ],
                    'accessory-type' : Accessory_Type_Sensors

                   },

    'Switch-1,0' : {'services' : [  {'type' : 'switch', 'number' : 8},
                                 ] ,
                    'accessory-type' : Accessory_Type_Switches
                   },

}

MOTE_IP = '' #fd00::212:4b00:1005:fdf3'
TIMEOUT = 2
class mote():
    def __init__(self,ip,desc=''):
        self.ip = ip
        self.desc = desc
        
def read_http_request(raw):
    lines = raw.split(b'\r\n')
    http_header = {}
    http_body = None

    if b'PUT' in lines[0]:
        http_header['method'] = b'PUT'
    elif b'POST' in lines[0]:
        http_header['method'] = b'POST'
    elif b'GET' in lines[0]:
        http_header['method'] = b'GET'
    elif b'DELETE' in lines[0]:
        http_header['method'] = b'DELETE'
    else:
        return http_header,http_body
    http_header['url'] = lines[0].split()[1]
    http_header['version'] = lines[0].split()[2]
    
    if b'Host' in lines[1]:
        http_header['host'] = lines[1].split(b':')[1].strip()
    else:
        return http_header,http_body

    if b'Content-Type' in lines[2]:
        http_header['Content-Type'] = lines[2].split(b':')[1].strip()
    else:
        return http_header,http_body
                
    if b'Content-Length' in lines[3]:
        http_header['Content-Length'] = int(lines[3].split(b':')[1].strip())
    else:
        return http_header,http_body

    body_len = http_header['Content-Length']
    if body_len > 0 :
        http_body = raw[-body_len::]

    return http_header,http_body


class bridgeAgent(threading.Thread):
    BUFSIZE = 1024
    IPv6_PREFIX = 'FD00'
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
            #print(self.bridge_ip)
        

    def addNewMote(self,ip):
        if ip is None:
            return 
        elif ip == 'NULL':
            return

        if ip in self.mote_list:
            return 
            
        global_ip = self.IPv6_PREFIX + ip[4::]

        log.info("new mote {0} coming".format(global_ip))

        profile = self.get_mote_profile(global_ip)
        log.info("new mote {0} profile: {1}".format(global_ip,profile))
        
        if profile is None:
            return
        
        if profile['model'] not in MoteCapabilityList:
            return
        
        self.mote_list[ip] = HAP_ACCESSORY(ip,profile)
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
            log.critical("The agent need reboot")

    def get_mote_profile(self,mote_ip):
        profile = {}
        try:

            # retrieve value of 'test' resource
            p = self.coap.GET('coap://[%s]/%s' % (mote_ip,'model'),
                    confirmable=True)
            var = ''.join([chr(b) for b in p])
            profile['model'] = var

            p = self.coap.GET('coap://[%s]/%s' % (mote_ip,'hw'),
                    confirmable=True)
            var = ''.join([chr(b) for b in p])
            profile['hw-version'] = var

            p = self.coap.GET('coap://[%s]/%s' % (mote_ip,'sw'),
                    confirmable=True)
            var = ''.join([chr(b) for b in p])
            profile['sw-version'] = var

            p = self.coap.GET('coap://[%s]/%s' % (mote_ip,'uptime'),
                    confirmable=True)
            var = ''.join([chr(b) for b in p])
            profile['uptime'] = var

            return profile

        except Exception as err:
            log.critical(err)
            return None

    def get_motes(self):
        return self.mote_list

    def get(self,ip,res):
        try:

            # retrieve value of 'test' resource
            p = self.coap.GET('coap://[%s]/%s' % (ip,res),
                    confirmable=True)

            result = str(p,encoding='utf8')

            return result
            
        except Exception as err:
            log.critical((err))
            return ''

    def post(self,ip,res,payload):
        try:
            #print(ip)
            #print(res)
            #print(payload)
            # retrieve value of 'test' resource
            p = self.coap.PUT('coap://[%s]/%s' % (ip,res),
                    confirmable=True,payload=payload)
            result = str(p,encoding='utf8')
            return result
            
        except Exception as err:
            log.critical((err))
            return ''

    def http_request_handle(self,hdr,body=None,source=None):

        if hdr['method'] == b'PUT':
            ip = b'fd00::' + hdr['host'].replace(b'.', b':')
            ip = str(ip,encoding='utf8')

            characteristics = None
            if body:
                #print(body)
                characteristics = json.loads(str(body,encoding='utf8'))['characteristics']
            if characteristics is None:
                return
            sw_id = (1<<characteristics[0]["localId"] ) & 0xFF
            if characteristics[0]['value']:
                payload = b'&state=%lx&mask=%lx' % (sw_id,sw_id)
            else:
                payload = b'&state=%lx&mask=%lx' % (0,sw_id)

            response = self.post(ip,'relay-sw',payload)
            log.info('Got response {0} from {1}'.format(response,ip))

        elif hdr['method'] == b'GET':
            ip = b'fd00::' + hdr['host'].replace(b'.', b':')
            ip = str(ip,encoding='utf8')
            http_msg =  'HTTP/1.1 200 OK\r\n' + \
                        'Content-Type: application/hap+json\r\n'

            if hdr['url'] == b'/temperature':
                res = 'temperature'
                response = self.get(ip,res)
                log.info('Got response {0} from {1}'.format(response,ip))
                json_body = json.dumps({'temperature' : float(response)})
                http_msg += 'Content-Length: {0}\r\n\r\n'.format(len(json_body)) + \
                            json_body
            elif hdr['url'] == b'/humidity':
                res = 'humidity'
                response = self.get(ip,res)
                log.info('Got response {0} from {1}'.format(response,ip))
                json_body = json.dumps({'humidity' : float(response)})
                http_msg += 'Content-Length: {0}\r\n\r\n'.format(len(json_body)) + \
                            json_body
            else:
                log.info('unsupport:{0} '.format(hdr['url']))
            log.info('send response {0} '.format(http_msg))
            self.socket_handler.sendto(http_msg.encode(encoding='utf8'),source)
           
               
    def recv_handler(self,timestamp,source,data):
        header,body = read_http_request(data)
        self.http_request_handle(hdr=header,body = body, source=source)

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

        log.info(  'Start poll sockets')
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

    def __init__(self,ip_addr,profile):

        if isinstance(ip_addr, str):
            self.ip_addr = ip_addr.encode(encoding='utf8')
        else:
            self.ip_addr = ip_addr
        self.profile = profile
        self.capability = MoteCapabilityList[profile['model']]
        log.info("new mote {0} capability: {1}".format(ip_addr,self.capability))
        self.category = self.capability['accessory-type']
        self.hap_accessory_proc = None
        self.instanceKeyName = self.ip_addr.replace(b':',b'_')
        self.accessory_dir = os.path.abspath(os.path.join(
            os.getcwd().encode(encoding='utf8'),
            self.data_dir,
            self.instanceKeyName))
        self.log = None

        self.CreateAccessoryInstance(self.ip_addr)

    def GetInstanceKeyName(self):
            return self.instanceKeyName


    def CreateAccessoryInstance(self,ip_address):
        
        accessory_base_info = {
            "aid"                   : 1,
            "category"              : self.category,
            "name"                  : str(ip_address[6::].replace(b':',b'.'),encoding='utf8'),
            "manufacturer"          : "Pure",
            "model"                 : self.profile['model'],
            "serialNumber"          : str(ip_address[6::].replace(b':',b''),encoding='utf8'),
            "firmwareVersion"       : self.profile['sw-version'],
            "hardwareVersion"       : self.profile['hw-version'],
            "services"              : self.capability['services']
        }

        if not os.path.exists(self.data_dir) :
            os.mkdir(self.data_dir)

        accessory_dir = self.accessory_dir
        if os.path.exists(accessory_dir):
            log.warning("accessory_dir:%s exists" % accessory_dir)
            return

        os.mkdir(accessory_dir)
        self.accessory_dir = accessory_dir


        accessory_store_dir = os.path.join(accessory_dir,b'.HomeKitStore')
        os.mkdir(accessory_store_dir)

        with open(os.path.join(accessory_store_dir,b'00.01'), 'w') as info_file:
            json.dump(accessory_base_info,info_file)
        
        #category = 5
        setupCode = '518-08-582'
        #setupGenerator = os.path.join(os.getcwd(),"AccessorySetupGenerator_arm64")
        setupGenerator = os.path.join(os.getcwd(),"AccessorySetupGenerator_armv7l")
        command = "%s --ip --category %d --setup-code \'%s\'" % (setupGenerator, self.category, setupCode)
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

            if self.log is None:
                self.log = open(os.path.join(self.accessory_dir, b'running.log'),'w')

            #command = "%s --root %s" % (hap_templete_app, self.accessory_dir.decode('utf8'))
            #print(command)
            #self.hap_accessory_proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            self.hap_accessory_proc = subprocess.Popen(
                                            hap_templete_app, 
                                            cwd=self.accessory_dir,
                                            stdout=self.log,
                                            stderr=subprocess.STDOUT)

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
            self.log.close()


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
            raw_in = input('coap>')
            args = raw_in.split()
            if len(args) == 0:
                continue
            if args[0] == 'get':
                #print(i)
                b.get_sensor('nbr')
            elif args[0] == 'sim':
                accIns = HAP_ACCESSORY(test_mote_ip, Accessory_Type_Lighting)
            elif args[0] == 'start':
                if accIns:
                    accIns.StartAccessoryInstance()

            elif args[0] == 'sw':
                if len(args) != 2:
                    continue
                payload = b'&state=0xFF&mask=%lx' % (1 & 0xFF)
                response = b.post(b'fd00::212:4b00:1940:c0d5',b'relay_sw',payload)
                print(response)
                response = b.post(b.bridge_ip,b'relay_sw',payload)
                print(response)

            elif args[0] == 'dump':
                print(b.mote_list)
            elif args[0] == 'exit':
                break
    except KeyboardInterrupt:
        print("key interrupt")

    b.shutdown()    
    if accIns:
        print('kill sub process ')
        accIns.shutdown()  

    print('exit')

    sys.exit(0)
