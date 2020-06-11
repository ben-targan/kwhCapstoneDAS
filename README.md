# kwhCaptsoneDAS
This is an open-source utility for reading data off of a Victron Charge Controller.

It was created for <u>Kilowatts for Humanity</u> by CS Capstone team 20.10: 
**Audrey Kan, Ben Targan, Dalena Le, Jesse DuFresne**


## General Information 
- this python script is based on a script found in this repo: <https://github.com/karioja/vedirect>

***The following is a list of all methods in the file in the order they appear:***


### `vedirect` Class Method Descriptions:
The methods in this class have to do with reading from the charge controller and assembling data for sending. All transformation of the data and the actual sending take place outside of this class.
 - **`__init__(self, serialport, timestamp)`**: 
  - Constructor.  Opens a serial connection on `serialport` (which is accessible through `self.ser`)
  - `timestamp` is the timestamp read from the command line, it is stored in `self.timestamp` for later sending.


 - **`input(self, byte)`**:
  - The provided `byte` is processed to determine where it fits within the packet.  
  - This method will return None until it has assembled a complete packet byte by byte.  
  - Once the packet is complete, it is returned as a dictionary.
  - **note: this method should only be called from `read()`** because each time `input()` is executed, class variables are modified to track the state and store the partial packet.

 - **`read(self, sendingFunction)`**:
  - `sendingFunction` is the output destination after a packet has been received
  - `read()` repeatedly calls `input()` until it returns the packet dictionary.  
  - The output stream is specified through an argument to allow for flexibility; it keeps any notion of where this packet is going outside the `vedirect` class.  This allows us to swap output destinations easily, which can be helpful for debugging or software evolution.
  - `read()` also provides the timestamp stored in `self.timestamp` to the `sendingFunction`  


### Sending Method Descriptions: 
These methods are called after the packet from the charge controller has been assembled.  They transform the key/value pairs and send them off to MySQL or display them for debugging.
 - **`convertKeys(data)`**:
  - `data` is the completed packet assembled by `input()`.
  - Key names are converted for readability in this method.  The keys changed are specified in `keysDict`,  as: `{"ToReplace" : "ReplaceWith"}`
  - Keys in `data` which are not in `keysDict` are left as is.

 - **`convertNonNumeric(value)`**:
   - This is a simple method which converts string values into numerical.
      - Currently only: `"ON" -> 1` and `"OFF" -> 0`  
   - This method could be in-lined, but it is left separate in case the need for other value conversions arises, so they do not clutter the sending method

 - **`sendToSQL(data, timestamp)`**:
   - This is the method which handles the insertion into MySQL.
   - `data` is the completed packet assembled by `input()`.
   - `timestamp` is provided by `read()`, and contains `self.timestamp`
   - This method also contains an `excludedKeys` list, which allows for fields to be removed if they are unnecessary. Currently the *Serial Number* is the only thing being excluded, as it does not have a numeric form.
   - Hex values are converted to decimal, and all non-hex values are passed through `convertNonNumeric()` to ensure type adherence.

 - **`printToConsole(data, timestamp)`**:
   - Similar to `sendToSQL`, this method provides an alternative output stream. It prints all of the key/value pairs in `data` to the console. 
   - When this method is used, the data does not end up in MySQL, it is only displayed in printed output.  





##Debugging help
 - Toward the end of main, at the bottom of the file, we see `ve.read(sendToSQL)`, which is the call that begins the process of reading and sending a packet. We can swap `sendToSQL` with `printToConsole` if for some reason we want to inspect the output and avoid inserting it into the db.  

 - The byte-by-byte processing in `input()` can only be triggered if a Serial connection with  VE.Direct cable is available.

 - If no VE.Direct cable is found, the script will look until one is found.  

 - The flow of execution is: `main` -> `read()` -> `input()` --(once packet complete)--> `sendToSQL()` -> `convertKeys()` -> `convertNonNumeric()` -> `DB.INSERT()` -> end