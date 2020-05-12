#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, serial, argparse

class vedirect:
    
    def __init__(self, serialport, timeout):
        self.serialport = serialport
        self.ser = serial.Serial(serialport, 19200, timeout=timeout)
        self.header1 = '\r'
        self.header2 = '\n'
        self.hexmarker = ':'
        self.delimiter = '\t'
        self.key = ''
        self.value = ''
        self.bytes_sum = 0;
        self.state = self.WAIT_HEADER
        self.dict = {}


    (HEX, WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(5)

    def input(self, byte):
        if byte == self.hexmarker and self.state != self.IN_CHECKSUM:
            self.state = self.HEX
            
        
        if self.state == self.WAIT_HEADER:
            try:
		self.bytes_sum += ord(byte)
	    except TypeError:
		print("Malformed packet --wait")
		self.bytes_sum = 0
            if byte == self.header1:
                self.state = self.WAIT_HEADER
            elif byte == self.header2:
                self.state = self.IN_KEY

            return None
        elif self.state == self.IN_KEY:
            try:
		self.bytes_sum += ord(byte)
	    except TypeError:
		print("Malformed packet --inkey")
		self.bytes_sum = 0
            if byte == self.delimiter:
                if (self.key == 'Checksum'):
                    self.state = self.IN_CHECKSUM
                else:
                    self.state = self.IN_VALUE
            else:
                self.key += byte
            return None
        elif self.state == self.IN_VALUE:
            try:
	    	self.bytes_sum += ord(byte)
	    except TypeError: 
		print("Malformed packet --invalue")
		self.bytes_sum = 0
            if byte == self.header1:
                self.state = self.WAIT_HEADER
                self.dict[self.key] = self.value;
                self.key = '';
                self.value = '';
            else:
                self.value += byte
            return None
        elif self.state == self.IN_CHECKSUM:
            try:
		self.bytes_sum += ord(byte)
	    except TypeError:
		print("Malformed packet --checksum")
		self.bytes_sum = 0
            self.key = ''
            self.value = ''
            self.state = self.WAIT_HEADER
            if (self.bytes_sum % 256 == 0):
                self.bytes_sum = 0
                return self.dict
            else:
                print("Malformed packet");
                self.bytes_sum = 0
        elif self.state == self.HEX:
            self.bytes_sum = 0
            if byte == self.header2:
                self.state = self.WAIT_HEADER
        else:
            raise AssertionError()

    def read_data(self):
        while True:
            byte = self.ser.read(1)
            packet = self.input(byte).encode('utf-8').strip()

    def read_data_single(self):
        while True:
            byte = self.ser.read(1)
            packet = self.input(byte).encode('utf-8').strip()
            if (packet != None):
                return packet
            

    def read_data_callback(self, callbackFunction):
        while True:
            byte = self.ser.read(1)
            if byte:
                try:
                    packet = self.input(byte.decode())
                except UnicodeError:
                    packet = self.input(byte.decode('utf-8', errors="ignore")) #THROWS OUT ERRORS
                else:
                    pass
                if (packet != None):
                    callbackFunction(packet) #packet is dict?
            else:
                print("No byte, break occured.");
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
