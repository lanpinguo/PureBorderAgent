import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('ota_server')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

import os
import sys
import socket
import time
import readline
import select
import struct
import threading
import util
from coap.socketUdpReal import socketUdpReal 

OTA_FRAME_TYPE_NONE             = 0
OTA_FRAME_TYPE_UPGRADE_REQUEST  = 1
OTA_FRAME_TYPE_DATA_REQUEST     = 2
OTA_FRAME_TYPE_FINISH           = 3
OTA_FRAME_TYPE_DATA             = 4

OTA_UPGRADE_OPTION_FORCE        = 1
OTA_UPGRADE_OPTION_RESTART      = 2
OTA_UPGRADE_OPTION_CONTINUE     = 3
OTA_UPGRADE_OPTION_CHECK        = 4


OTA_FRAME_DATA_BLOCK_SIZE       = 55


class MOTE_FIRMWARE():

    def __init__(self, deviceType, version, path):
        self.deviceType = deviceType
        self.version = version
        self.maxSeqno = 1
        self.checkCode = 0



class OTA():

    def __init__(self,ipAddress,udpPort):
        # initialize the parent class
        self.sock = socketUdpReal(ipAddress = ipAddress, udpPort = udpPort, callback = self.ota_callback)
        self.maxSeqno = 1
        self.checkCode = 0
    def ota_callback(self,timestamp,source,data):
        #print("ota_callback got {2} from {1} at {0}".format(timestamp,source,data))
        frame_type,= struct.unpack_from('B',data,offset=0)
        if frame_type == OTA_FRAME_TYPE_DATA_REQUEST:
            t,deviceType,version,seqno, = struct.unpack_from('<BIIH',data)
            #print("{0} {1} {2} {3}".format(t,deviceType,version,seqno))
            with open("PureSwitch.bin", mode = 'rb') as f: 
                frame_type = OTA_FRAME_TYPE_DATA
                offset = seqno * OTA_FRAME_DATA_BLOCK_SIZE
                f.seek(offset)
                data = f.read(OTA_FRAME_DATA_BLOCK_SIZE)
                dataLen = len(data)
                #print("{0} {1} ".format(seqno,dataLen))
                if dataLen == 0 :
                    frame_type = OTA_FRAME_TYPE_FINISH
                    checkCode = self.checkCode
                    msg = struct.pack("<BIIHI",frame_type,deviceType,version,seqno,checkCode)
                else:
                    msg = struct.pack("<BIIHB",frame_type,deviceType,version,seqno,dataLen) + data
                rc = self.sock.sendUdp(destIp = source[0], destPort = 5678,msg = msg)
                print("\rprogress : {0:.2%}".format(seqno / self.maxSeqno),end='', flush=True)

    def update(self,destIp):
        fileLen = os.path.getsize("PureSwitch.bin") 
        if fileLen > 512 * 1024:
            print("file size %d is too large" % fileLen )
            return
        if fileLen < OTA_FRAME_DATA_BLOCK_SIZE :
            print("file size %d is wrong" % fileLen )
            return

        with open("PureSwitch.bin", mode = 'rb') as f: 
            self.checkCode = util.crc32(f.read(fileLen))

        seqno = int(fileLen / OTA_FRAME_DATA_BLOCK_SIZE)
        if fileLen % OTA_FRAME_DATA_BLOCK_SIZE > 0:
            seqno += 1
        self.maxSeqno = seqno
        frame_type = OTA_FRAME_TYPE_UPGRADE_REQUEST
        deviceType = 1
        version = 0x10000
        primary = 1
        blockSize = OTA_FRAME_DATA_BLOCK_SIZE
        option = OTA_UPGRADE_OPTION_RESTART
        print("File size : {2} bytes, max seqno : {0}, checkcode : {1:#X}".format(self.maxSeqno, self.checkCode, fileLen))
        msg = struct.pack("<BIIBHIB",frame_type,deviceType,version,primary,blockSize,fileLen,option)
        self.sock.sendUdp(destIp = destIp,destPort = 5678,msg = msg)

    def close(self):
        self.sock.close()    


if __name__ == '__main__':

    test_mote_ip = b'fd00::0212:4b00:194a:f47d'

    ota = OTA(ipAddress = 'FD00::1', udpPort = 8756)


    try:
        while True:
            # let the server run
            raw_in = input('ota>')
            args = raw_in.split()
            if len(args) == 0:
                continue
            if args[0] == 'update':
                ota.update(test_mote_ip)
            elif args[0] == "send":
                pass
            elif args[0] == 'exit':
                break
    except Exception as e:
        print("Get Exception: {0}".format(e))
        raise(e)

    ota.close()    

    print('exit')

    sys.exit(0)
    
