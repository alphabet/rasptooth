import requests
import json
import logging as log
log.basicConfig(format='%(levelname)s:%(message)s', filename='blinker.log', level=log.DEBUG)

import fcntl
import struct
import array
import bluetooth
import bluetooth._bluetooth as bt

import time
import os
import datetime

devices = [
        {"name": "Gui's Pixel2", "id": "40:4E:36:4A:B7:58", "blinkt": [0,0,255,0]}, 
        {"name": "Molly's iPhone 5", "id": "DC:A9:04:40:25:AB", "blinkt":[1,0,64,212]}, 
        {"name": "TV", "id": "C0:97:27:1A:4A:C7", "blinkt": [2,128,64,64]},
        {"name": "Fiat","id": "00:21:3E:28:21:D9", "blinkt":[3,255,0,0]},
        {"name": "Fiat Blue & Me", "id": "00:14:09:48:1A:DF", "blinkt":[4,255,64,64]},
        {"name": "Tile #1", "id": "F1:2F:8C:4D:56:65", "blinkt":[5,255,255,255]},
        {"name": "Tile #2", "id": "F7:6F:61:9E:79:B3", "blinkt":[6,255,255,255]},
        ]


def bluetooth_rssi(addr):
    # Open hci socket
    hci_sock = bt.hci_open_dev()
    hci_fd = hci_sock.fileno()

    # Connect to device (to whatever you like)
    bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    bt_sock.settimeout(10)
    result = bt_sock.connect_ex((addr, 1))	# PSM 1 - Service Discovery

    try:
        # Get ConnInfo
        reqstr = struct.pack("6sB17s", bt.str2ba(addr), bt.ACL_LINK, "\0" * 17)
        request = array.array("c", reqstr )
        handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
        handle = struct.unpack("8xH14x", request.tostring())[0]

        # Get RSSI
        cmd_pkt=struct.pack('H', handle)
        rssi = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM,
                bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, cmd_pkt)
        rssi = struct.unpack('b', rssi[3])[0]

        # Close sockets
        bt_sock.close()
        hci_sock.close()

        return rssi

    except:
        return None

def detectProximity(device):

    far = True
    far_count = 0
    near_count = 0

    # assume phone is initially far away
    rssi = -255
    rssi_prev1 = -255
    rssi_prev2 = -255

    near_cmd = 'br -n 1'
    far_cmd = 'br -f 1'

    # begin proximity sensing
    while (far==True and far_count <=9):
        rssi = bluetooth_rssi(device["id"])
        log.info("rssi for %s", device["id"])
        log.info(str(rssi))
        #    rssi = bluetooth_rssi(dagar_addr)

        if rssi == rssi_prev1 == rssi_prev2 == None:
            log.warn("%s can't detect address", str(datetime.datetime.now()))
            time.sleep(3)

        elif rssi == rssi_prev1 == rssi_prev2 == 0:
            # change state if nearby
            log.info("change state if nearby")
            if far:
                far = False
                far_count = 0
                os.system(near_cmd)
                log.info("%s changed to near", str(datetime.datetime.now()))
                near_count += 1
            time.sleep(5)

        elif rssi < -2 and rssi_prev1 < -2 and rssi_prev2 < -2:
            # if was near and signal has been consisitenly low
            log.info("was near, signal consistently low")
            # need 10 in a row to set to far
            far_count += 1
            if not far and far_count > 10:
                # switch state to far
                far = True
                far_count = 0
                os.system(far_cmd)
                log.info("%s changed to far", str(datetime.datetime.now()))
                time.sleep(5)
        else:
            far_count = 0
            log.info("%s far is zero", str(datetime.datetime.now()))

        rssi_prev1 = rssi
        rssi_prev2 = rssi_prev1

    return far
    # end proximity sensing

print ("bluetooth proximity")

def updateServer(device):
    headers = {'content-type': 'application/json', 'device': device['id']}
    response = requests.post('http://sails-project-guiweinmann.codeanyapp.com:3000/l2',
            headers=headers, data=str(json.dumps(device)))
    print 'sending ' + str(device)


while True:
    log.info("checking %s" + time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime()))

    for device in devices:
        #d = devices[device]
        result = bluetooth.lookup_name(device["id"], timeout=5)
        if(result != None):
            log.info("%s is here (%s)", result, device)
            device["far"] = detectProximity(device)
            log.info("%s far away: %s", device, str(device["far"]))
            updateServer(device)
        else:
            log.info("not a recognized device: %s", str(result))
            log.info("%s -- %s ", str(device["id"]), device)
            time.sleep(2)
          #  print ("at least one signal is missing.")


