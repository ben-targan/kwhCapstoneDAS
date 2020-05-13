#!/usr/bin/python
# -*- coding: utf-8 -*-

# Charge Controller Processing

import os, serial, argparse


import subprocess


# debug flag for additional printing
debug = True


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
                    print("Malformed packet")
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
                    packet = self.input(byte.decode('windows-1252'))
                except UnicodeError:
                    if debug:
                        print("NON win1252 CHAR")
                    # packet = self.input(byte.decode('windows-1252')) #Guess another encoding, doesnt error, but inverter returns Euro sign & '/x00'
                else:
                    pass
                if (packet != None):
                    callbackFunction(packet) #packet is complete at this point. type=dict
            else:
                print("No byte, break occured.")
                break


##### EXTRACT OUTPUT DICT FROM THIS METHOD
def print_data_callback(data):

    # TODO: remove unicode, string process dict

    print("-----------------------------------------------------")
    for key in data:
        print("%s : %s" % (key.encode("utf-8"), data[key].encode("utf-8")))


    # print(data)
    print("-----------------------------------------------------")

if __name__ == '__main__':
    # TODO: add dynamic input from command
    # test = subprocess.Popen(["dmesg", "|", "grep", ""], stdout=subprocess.PIPE)
    # output = test.communicate()[0]

    port = "/dev/ttyUSB0"


    ve = vedirect(port)
    ve.read_data_callback(print_data_callback)
    #print(ve.read_data_single())
