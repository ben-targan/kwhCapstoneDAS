#!/usr/bin/python
# -*- coding: utf-8 -*-

# Charge Controller Processing

import os, serial, argparse

import serial.tools.list_ports as listPorts
import subprocess
import time

# import KWH_MySQL


# debug flag for additional printing
debug = False


class vedirect:
    
    def __init__(self, serialport):
        self.serialport = serialport
        self.ser = serial.Serial(serialport, 19200)
        self.carrigeReturn = '\r'
        self.newLine = '\n'
        self.colon = ':'
        self.tab = '\t'
        self.key = ''
        self.value = ''
        self.packetLen = 0
        self.currState = self.WAIT_HEADER
        self.packetDict = {}


    # constants
    (HEX, WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(5)

    # input loop, one byte at a time
    def input(self, byte):
        if byte == self.colon and self.currState != self.IN_CHECKSUM:
            self.currState = self.HEX
            
#---------------------------------------------------------------------
        
        if self.currState == self.WAIT_HEADER:

            if debug:
                print("### In Wait, ord: ", ord(byte))
            try:
                self.packetLen += ord(byte) #ord throws: given char arr len 0

            except TypeError:
                if debug:
                    print("Malformed packet --wait") #inverter hangs here

            if byte == self.carrigeReturn:
                self.currState = self.WAIT_HEADER
            
            elif byte == self.newLine:
                self.currState = self.IN_KEY

            return None

#---------------------------------------------------------------------

        elif self.currState == self.IN_KEY:
            if debug:
                print("### In Key")
            try:
                self.packetLen += ord(byte)

            except TypeError:
                if debug:
                    print("Malformed packet --inkey")
            
            if byte == self.tab:
                if (self.key == 'Checksum'):
                    self.currState = self.IN_CHECKSUM
                
                else:
                    self.currState = self.IN_VALUE
            
            else:
                self.key += byte
            
            return None
        
#---------------------------------------------------------------------        

        elif self.currState == self.IN_VALUE:
            if debug:
                print("### In Value")
            try:
                self.packetLen += ord(byte)

            except TypeError: 
                if debug:
                    print("Malformed packet --invalue")
            
            if byte == self.carrigeReturn:
                self.currState = self.WAIT_HEADER
                
                self.packetDict[self.key] = self.value
                self.key = ''
                self.value = ''
            
            else:
                self.value += byte
            
            return None

#---------------------------------------------------------------------

        elif self.currState == self.IN_CHECKSUM:
            if debug:
                print("### In Checksum")
            try:
                self.packetLen += ord(byte)
            except TypeError:
                if debug:
                    print("Malformed packet --checksum")
            
            self.key = ''
            self.value = ''
            self.currState = self.WAIT_HEADER
            
            if (self.packetLen % 256 == 0):
                self.packetLen = 0
                return self.packetDict #VALID PACKET RETURN

            else:
                if debug:
                    print("Malformed packet --incorrect packetLen")
                self.packetLen = 0

#---------------------------------------------------------------------                

        elif self.currState == self.HEX:
            if debug:
                print("### In Hex")
            self.packetLen = 0

            if byte == self.newLine:
                self.currState = self.WAIT_HEADER

#---------------------------------------------------------------------

        else:
            if debug:
                print("### In assertionError")
            raise AssertionError()
            

    def read_data_callback(self, callbackFunction):
        while True:
            byte = self.ser.read(1)
            if byte:
                try:
                    packet = self.input(byte.decode('windows-1252', errors="ignore"))
                except UnicodeError:
                    if debug:
                        print("NON win1252 CHAR")
                    packet = self.input(byte.decode('utf-8', errors="ignore"))
                    # packet = self.input(byte.decode('windows-1252')) #Guess another encoding, doesnt error, but inverter returns Euro sign & '/x00'
                else:
                    pass
                if (packet != None):
                    callbackFunction(packet) #packet is complete at this point. type=dict
            else:
                print("No byte, break occured.")
                break



def convertKeys(data):
    keysDict = {
        "PPV" : "PV Array Power",
        "VPV" : "PV Array Voltage",
        "LOAD" : "Load",
        "H19" : "h19",
        "Relay" : "Relay",
        "ERR" : "Error #",
        "FW" : "FW",
        "I" : "Main Current",
        "H21" : "h21",
        "PID" : "Process ID",
        "H20" : "h20",
        "H23" : "h23",
        "MPPT" : "Maximum Power Point",
        "HSDS" : "HSDS",
        "SER#" : "Serial #",
        "V" : "Main Voltage",
        "CS" : "CS",
        "H22" : "h22"
    }
    newdata = {}

    for key in data:

        try:
            newdata[keysDict[key]] = data[key]
        except KeyError:
            newdata[key] = data[key]

    return newdata


##### EXTRACT OUTPUT DICT FROM THIS METHOD
def print_data_callback(data):

    data = convertKeys(data)

    file = open("/home/pi/testOutput", "a")

    print("-----------------------------------------------------")
    for key in data:
        print("%s : %s" % (key.encode("utf-8"), data[key].encode("utf-8")))
        file.write("%s : %s" % (key.encode("utf-8"), data[key].encode("utf-8")))


    # DB = KWH_MySQL.KWH_MySQL()

    # for key in data:
    #     timestamp = time.time()
    #     sql="INSERT INTO data VALUES (" + timestamp +","+ key.encode("utf-8") 
    #         + "," + data[key].encode("utf-8") + ");"
    #     DB.INSERT(sql)


    print("-----------------------------------------------------")

    file.close()



if __name__ == '__main__':
    correctPort = ''


    possiblePorts = listPorts.comports()

    for port in possiblePorts:
        if port.description == 'VE Direct Cable':
            correctPort = port.device


    


    ve = vedirect(correctPort)
    ve.read_data_callback(print_data_callback)
    #print(ve.read_data_single())
