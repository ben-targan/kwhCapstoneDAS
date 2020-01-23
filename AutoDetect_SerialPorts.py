import fnmatch
import serial

def auto_detect_serial_unix(preferred_list=['*']):
    '''try to auto-detect serial ports on posix based OS'''
    import glob
    glist = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    ret = []

    # try preferred ones first
    for d in glist:
        for preferred in preferred_list:
            if fnmatch.fnmatch(d, preferred):
                #ret.append(SerialPort(d))
                ret.append(d)
    if len(ret) > 0:
        return ret
    # now the rest
    for d in glist:
        #ret.append(SerialPort(d))
        ret.append(d)
    return ret

def main():
	available_ports = auto_detect_serial_unix()
	port = serial.Serial(available_ports[0], 115200,timeout=1)
	return 0

if __name__ == '__main__':
	main()
