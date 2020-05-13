#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, serial, argparse

class vedirect:
    
    def __init__(self, serialport, timeout):
        self.serialport = serialport
        self.ser = serial.Serial(serialport, 19200, timeout=timeout)
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
            print("### In Wait, ord: ", ord(byte))
            try:
                self.packetLen += ord(byte) #ord throws: given char arr len 0

            except TypeError:
                print("Malformed packet --wait") #inverter hangs here

            if byte == self.carrigeReturn:
                self.currState = self.WAIT_HEADER
            
            elif byte == self.newLine:
                self.currState = self.IN_KEY

            return None

#---------------------------------------------------------------------

        elif self.currState == self.IN_KEY:
            print("### In Key")
            try:
                self.packetLen += ord(byte)

            except TypeError:
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
            print("### In Value")
            try:
                self.packetLen += ord(byte)

            except TypeError: 
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
            print("### In Checksum")
            try:
                self.packetLen += ord(byte)
            except TypeError:
                print("Malformed packet --checksum")
            
            self.key = ''
            self.value = ''
            self.currState = self.WAIT_HEADER
            
            if (self.packetLen % 256 == 0):
                self.packetLen = 0
                return self.packetDict #VALID PACKET RETURN

            else:
                print("Malformed packet")
                self.packetLen = 0

#---------------------------------------------------------------------                

        elif self.currState == self.HEX:
            print("### In Hex")
            self.packetLen = 0

            if byte == self.newLine:
                self.currState = self.WAIT_HEADER

#---------------------------------------------------------------------

        else:
            print("### In assertionError")
            raise AssertionError()

    # unused methods:
    # def read_data(self):
    #     while True:
    #         byte = self.ser.read(1)
    #         packet = self.input(byte).encode('utf-8').strip()

    # def read_data_single(self):
    #     while True:
    #         byte = self.ser.read(1)
    #         packet = self.input(byte).encode('utf-8').strip()
    #         if (packet != None):
    #             return packet
            

    def read_data_callback(self, callbackFunction):
        while True:
            byte = self.ser.read(1)
            if byte:
                try:
                    packet = self.input(byte.decode())
                except UnicodeError:
                    #print("NON UTF CHAR")
                    packet = self.input(byte.decode('windows-1252')) #Guess another encoding, doesnt error, but inverter returns Euro sign & '/x00'
                else:
                    pass
                if (packet != None):
                    callbackFunction(packet) #packet is complete at this point. type=dict
            else:
                print("No byte, break occured.")
                break


##### EXTRACT OUTPUT DICT FROM THIS METHOD
def print_data_callback(data):
    print(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process VE.Direct protocol')
    parser.add_argument('--port', help='Serial port')
    parser.add_argument('--timeout', help='Serial port read timeout', type=int, default='60')
    args = parser.parse_args()
    ve = vedirect(args.port, args.timeout)
    ve.read_data_callback(print_data_callback)
    #print(ve.read_data_single())
