#!/usr/bin/python
# -*- coding: utf-8 -*-

# Charge Controller Processing
import sys
import os, serial, argparse
import serial.tools.list_ports as listPorts
import subprocess
import time

# KWH debug, spans system
# DEBUG = int(config_var['DEBUG'])

# Log function
def log(logText):
    with open("/kwh/log/modbus.log", "a+") as log:
        log.write(str(int(time.time())) + ": " + logText +"\n")


# debug flag for additional printing
debug = False


class vedirect:
    
    def __init__(self, serialport, timestamp):
        self.timestamp = timestamp
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
            

#-----------------------------------------------------------------------------
    def read(self, sendingFunction):
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
                    sendingFunction(packet, self.timestamp) #packet is complete at this point. type=dict
            else:
                print("No byte, break occured.")
                break


#-----------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------



def INSERT(sql):
    import MySQLdb
    from MySQLdb import Error

    db = MySQLdb.connect('localhost','pi','','test')
    cursor = db.cursor()
    result = cursor.execute(sql)
    try:
        db.commit()
        cursor.close()
        db.close()
        print("TRY INSERT")
        
    except MySQLdb.Error as error:
        db.rollback()
        cursor.close()
        db.close()
        print("ROLLBACK")
        return [1, error]

    return [0]



def sendToSQL(data, timestamp):

    data = convertKeys(data)

    # insert in format timestamp, label, value

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    for key in data:
        sql="INSERT INTO data VALUES (\"" + timestamp +"\",\""+ str(key) + "\",\"" + str(data[key]) + "\");"
        print("going into insert")
        INSERT(sql)
        # if DEBUG: log(sql)


def printToConsole(data, timestamp):

    data = convertKeys(data)

    print("-----------------------------------------------------")
    for key in data:
        print("(%s)%s : %s" % (timestamp, key.encode("utf-8"), data[key].encode("utf-8")))
    print("-----------------------------------------------------")



if __name__ == '__main__':
    correctPort = ''
    timestamp = sys.argv[1]

    possiblePorts = listPorts.comports()

    for port in possiblePorts:
        if port.description == 'VE Direct cable':
            correctPort = port.device


    #TODO: add logging
    if correctPort == '':
        log("Serial Port for Charge Controller not found, exiting...")
        sys.exit(0)


    ve = vedirect(correctPort, timestamp)
    # ve.read(sendToSQL)
    ve.read(sendToSQL)
