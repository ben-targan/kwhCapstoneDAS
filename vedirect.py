#!/usr/bin/python
# -*- coding: utf-8 -*-
# Built and tested with Python 2.7.13
# Originally adapted from: https://github.com/karioja/vedirect

# =================================================
# Charge Controller Processing
# 2020 Capstone Team CS 20.10
# Audrey Kan, Ben Targan, Dalena Le, Jesse DuFresne
# =================================================

# Purpose: This Python 2 script scrapes data from a Victron
#          Charge Controller(CC) and stores key(str)/value(int) pairs  
#          into the local MariaDB (database: kwh, table: data).

# General Execution Preconditions: 
#   - A CC is connected to this device via VE.Direct cable
#     If there is no VE.Direct cable connected, the script will search until 
#     one is found.

# General Execution Postconditions:
#   - One packet from the CC is inserted into the local kwh db, in the data table.
#     Each key/value within the packet is inserted separately 



import KWH_MySQL
import sys
import os
import serial
import argparse
import serial.tools.list_ports as listPorts
import subprocess
import time
sys.path.append('/kwh/lib')

# Load environment variables for KWH debug flag
exec(open("/kwh/config/get_config.py").read())
DEBUG = int(config_var['DEBUG'])

# KWH Log function
def log(logText):
    with open("/kwh/log/modbus.log", "a+") as log:
        log.write(str(int(time.time())) + ": " + logText + "\n")


##############################################################################
# This class is used for reading bytes from a VE.Direct connection. 
# Once a full packet is received, it is handled as a dictionary and sent to a 
# specified output stream. ( specified by passing a function to read() )

class vedirect:

# Preconditions: 
#   - timestamp used here is taken from command line argument and should match 
#     timestamps from other data collection scripts, to ensure proper packaging
#     and output
# 
#   - serialport used here should be a valid serial port and should belong
#     to a VE.Direct Cable attached to a Victron CC

# Postconditions: 
#   - Serial Connection is open 
#   - object is ready to have read() called

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

# -----------------------------------------------------------------------------
# Preconditions:
#   - byte contains a byte read from the serial connection to CC
#   - input() is Only called by read(), as input builds the dict byte-by-byte

# Postconditions:
#   - None is returned: the packet is not complete, and input must be called 
#     with the next byte. Input will return None until packet is complete.
# 
#   - the packet dict is returned: the packet is complete, the next call to 
#     input will start building the next packet

# Possible Side Effects:
#   - self.currState is modified to direct the next execution of input()
#   - self.key & self.value can hold incomplete information as each pair is 
#     decoded.  
#   - self.packetDict will also be empty/incomplete as pairs are read in
#   - no class attributes should be modified outside of input

    def input(self, byte):
        if byte == self.colon and self.currState != self.IN_CHECKSUM:
            self.currState = self.HEX

        # ---------------------------------------------------------------------

        if self.currState == self.WAIT_HEADER:

            try:
                self.packetLen += ord(byte)

            except TypeError:
                pass
            if byte == self.carrigeReturn:
                self.currState = self.WAIT_HEADER

            elif byte == self.newLine:
                self.currState = self.IN_KEY

            return None

        # ---------------------------------------------------------------------

        elif self.currState == self.IN_KEY:
            try:
                self.packetLen += ord(byte)

            except TypeError:
                pass
            if byte == self.tab:
                if (self.key == 'Checksum'):
                    self.currState = self.IN_CHECKSUM

                else:
                    self.currState = self.IN_VALUE

            else:
                self.key += byte

            return None

        # ---------------------------------------------------------------------

        elif self.currState == self.IN_VALUE:
            try:
                self.packetLen += ord(byte)

            except TypeError:
                pass
            if byte == self.carrigeReturn:
                self.currState = self.WAIT_HEADER

                self.packetDict[self.key] = self.value
                self.key = ''
                self.value = ''

            else:
                self.value += byte

            return None

        # ---------------------------------------------------------------------

        elif self.currState == self.IN_CHECKSUM:
            try:
                self.packetLen += ord(byte)
            except TypeError:
                pass
            self.key = ''
            self.value = ''
            self.currState = self.WAIT_HEADER

            if (self.packetLen % 256 == 0):
                self.packetLen = 0
                return self.packetDict  # VALID PACKET RETURN

            else:
                self.packetLen = 0

        # ---------------------------------------------------------------------

        elif self.currState == self.HEX:
            self.packetLen = 0

            if byte == self.newLine:
                self.currState = self.WAIT_HEADER

        # ---------------------------------------------------------------------

        else:
            raise AssertionError()


# -----------------------------------------------------------------------------

# Preconditions:
#   - sendingFunction is where the completed key/value pairs should be sent to
#     for valid behavior should be: sendToSQL , for debugging: printToConsole
# 
#   - self.ser contains a valid serial connection to serialPort

# Postconditions:
#   - A single packet has been passed to sendingFunction 

# Possible Side Effects:
#   - If the byte read is neither windows-1252 or utf-8 decode-able, reading is
#     aborted.  This problem is mitigated due to scheduled execution of this file.
    def read(self, sendingFunction):
        foundCompletePacket = False
        # sends one packet per execution
        while not foundCompletePacket:
            byte = self.ser.read(1)
            if byte:
                try:
                    packet = self.input(byte.decode('windows-1252', errors="ignore"))
                except UnicodeError:
                    packet = self.input(byte.decode('utf-8', errors="ignore"))

                if (packet != None):
                    foundCompletePacket = True
                    sendingFunction(packet, self.timestamp)
            else:
                log("No byte read over serial, break occured.")
                break
# End class definition 
##############################################################################

# Precondition:
#   - data should contain the packet dict passed by read()

# Postcondition:
#   - Key name changes specified in keysDict will be changed.  All other keys 
#     and all values will remain unchanged
def convertKeys(data):
    # unnecessary substitutions commented out, left here to show complete packet keys
    keysDict = {
#       "ToReplace" : "ReplaceWith"
        "PPV": "PVArrayPower",
        "VPV": "PVArrayVoltage",
        # "LOAD" : "Load",
        # "H19" : "h19",
        # "Relay" : "Relay",
        "ERR": "Error",
        # "FW" : "FW",
        "I": "MainCurrent",
        # "H21" : "h21",
        # "PID" : "PID",
        # "H20" : "h20",
        # "H23" : "h23",
        "MPPT": "MaximumPowerPoint",
        # "HSDS" : "HSDS",
        "SER#": "Serial",
        "V": "MainVoltage"  # ,
        # "CS" : "CS",
        # "H22" : "h22",
        # "OR" : "OR"
    }
    newdata = {}

    for key in data:

        try:
            newdata[keysDict[key]] = data[key]
        except KeyError:
            newdata[key] = data[key]

    return newdata

# -----------------------------------------------------------------------------

def convertNonNumeric(value):
    if value == "ON":
        return 1

    elif value == "OFF":
        return 0

    # Other value conversions can be added here

    # if none of these cases, already numeric
    return value

# -----------------------------------------------------------------------------

# Preconditions:
#   - data contains a complete packet, passed from read()
# 
#   - timestamp contains value taken from command line

# Postconditions:
#   - A single packet has been inserted into the data table within the kwh db

# Possible Side Effects:
#   - Keys listed in excludedKeys will not be inserted
def sendToSQL(data, timestamp):
    data = convertKeys(data)
    DB = KWH_MySQL.KWH_MySQL()

    # keys added here will be excluded from insertion into SQL
    excludedKeys = [
        "Serial"  # Serial number cannot be converted to numeric
    ]

    for key in data:
        if key in excludedKeys:
            continue

        # if value is hex, convert it to decimal
        if data[key][:2] == "0x":
            convertedHex = int(data[key], 16)
            sql = "INSERT INTO data VALUES (" + str(timestamp) + ",\"" + str(key) + "\"," + str(convertedHex) + ");"

        else:
            value = convertNonNumeric(data[key])

            sql = "INSERT INTO data VALUES (" + str(timestamp) + ",\"" + str(key) + "\"," + str(value) + ");"

        DB.INSERT(sql)
        if DEBUG:
            log(sql)

# -----------------------------------------------------------------------------


# Preconditions:
#   - data contains a complete packet, passed from read()
# 
#   - timestamp contains value taken from command line

# Postconditions:
#   - A single packet has been printed out to the console

# This is an alternative output stream to sending the packet to SQL, and can be
# useful for debugging. 
def printToConsole(data, timestamp):

    data = convertKeys(data)

    print("-----------------------------------------------------")
    for key in data:
        # if value is hex, convert it to decimal
        if data[key][:2] == "0x":
            i = int(data[key], 16)
            print("(%s)%s : %s" % (timestamp, key.encode("utf-8"), str(i)))
        else:
            value = convertNonNumeric(data[key])
            print("(%s)%s : %s" % (timestamp, key.encode("utf-8"), str(value)))
    print("-----------------------------------------------------")

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # timestamp must be given at command line
    timestamp = sys.argv[1]
    correctPort = ''

    while correctPort == '':

        possiblePorts = listPorts.comports()

        for port in possiblePorts:
            if port.description == 'VE Direct cable':
                correctPort = port.device

        if correctPort == '':
            log("Serial Port for Charge Controller not found, retrying...")

    ve = vedirect(correctPort, timestamp)

    # swap sendToSQL with printToConsole for debugging
    ve.read(sendToSQL)

    log("Packet sent, exiting...")