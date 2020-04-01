"""Web Worker script."""

# In web workers, "window" is replaced by "self".
import time
#from browser import bind, self
import sys
import time
import traceback
import javascript
import random
import json
from browser import bind, self
KEY_HOME          = 0xff50
KEY_ESC           = 27
KEY_LEFT          = 37
KEY_UP            = 38
KEY_RIGHT         = 39
KEY_DOWN          = 40
KEY_W             = 87
KEY_A             = 65
KEY_C             = 67
KEY_S             = 83
KEY_D             = 68
KEY_SPACE         = 32
KEY_PAGEUP        = 0xff55
KEY_PAGEDOWN      = 0xff56
KEY_END           = 0xff57
KEY_BEGIN         = 0xff58

console = self.console
window = self

def run_code(src, globals, locals):
    global array
    self.console.log("running code...")
    send_message(["waitdone"])
    try:
        exec(src , globals, locals)
    except Exception as e:
        # TODO: change the QUIT to an exception type
        if str(e)[:4] == "QUIT":
            return
        
        self.console.log("Exception:" + str(e))
        send_message(["error", "Error: " + str(e) + "\n"])
    #graphics.reveal()
       
def send_message(message):
    self.console.log("Worker sending to main thread.." + str(message))
    self.send(message)    
    
class EdSim():
    # Unique constants
    V2                  =   1
    CM                  =   2
    TEMPO_MEDIUM        =   3
    ON                  =   True
    OFF                 =   False
    FORWARD             =   6
    BACKWARD            =   7
    SPIN_RIGHT          =   8
    SPIN_LEFT           =   9
    TIME_MILLISECONDS   =  10
    
    # values       
    SPEED_1             =   1
    SPEED_2             =   2
    SPEED_3             =   3
    SPEED_4             =   4
    SPEED_5             =   5
    SPEED_6             =   6
    SPEED_7             =   7
    SPEED_8             =   8
    SPEED_9             =   9
    SPEED_10            =  10    
    SPEED_FULL          =   0
    
    CLAP_DETECTED       = True
    CLAP_NOT_DETECTED   = False
    
    LINE_ON_WHITE       = True
    LINE_ON_BLACK       = False
        
    #settings
    EdisonVersion   = V2
    DistanceUnits   = CM
    Tempo           = TEMPO_MEDIUM
    
    
    
    def __init__(self):
        self.body_id_counter = 0
        
    def __checkQuit(self):
        global array
        if array[KEY_ESC] == 1:
            console.log("Escape detected!")
            send_message(["stop"])
            raise Exception("QUIT requested")    
            
    def LineTrackerLed(self, state):
        send_message(["linetracker", state])      

    def ReadLineState(self):
        # the linestate is constantly updated by pyangeloEDSim in the sharedarraybuffer
        if array[511] == 0:
            return EdSim.LINE_ON_BLACK
        elif array[511] == 1:
            return EdSim.LINE_ON_WHITE
        else:
            return None
    
    def Drive(self, direction, speed, duration):
        console.log("Trying to drive")
        
        if speed == EdSim.SPEED_FULL:
            speed = 11
            
        self.__checkQuit()
        
        send_message(["drive", direction, speed, duration])
        
    def TimeWait(self, time, unit):
        # block!
        currTime = window.performance.now()
        
        # TODO: assuming units are in milliseconds for now
        while (window.performance.now() - currTime < time):
            self.__checkQuit()
            
    def RightLed(self, state):
        send_message(["LED", True, state])
        
    def LeftLed(self, state):
        send_message(["LED", False, state])
        
    def PlayBeep(self):
        send_message(["beep"])
        
    def AddBall(self, x, y, radius):
        id = self.body_id_counter
        
        self.body_id_counter += 1
        
        send_message(["addBall", id, x, y, radius])
        
        return id
        
    def ReadClapSensor(self):
        global array
        
        result = EdSim.CLAP_NOT_DETECTED
        if array[KEY_C] == 1:
            result = EdSim.CLAP_DETECTED
            # clear the clap
            array[KEY_C] = 0
            send_message(["clearclap"])
            
        self.__checkQuit()
        return result

        
Ed = EdSim()        
 
array = None
shared = None


@bind(self, "message")
def onmessage(evt):
    global clear, array, shared, Ed
    """Handle a message sent by the main script.
    evt.data is the message body.
    """
    if not isinstance(evt.data, list):
        self.console.log("Receiving shared data...")
        shared = evt.data
        array = self.Int8Array.new(evt.data)
        workerResult = f'Result: {array[0]}'
        self.console.log(workerResult)  
        
        send_message(["waitdone"])
        return    
    
    command = evt.data[0]
    if command.lower() == "run":
        #alert("Executing!")
        self.console.log("Executing on the worker thread!");
        src = evt.data[1]    
        success = True
        try:
            namespace = globals()
            namespace["__name__"] = "__main__"
            
            run_code(src, namespace, namespace)                            
        except Exception as exc:
            self.console.log("exception attempting to run code:" + str(exc))
  
class PrintOutput:
    def write(self, data):
        send_message(["print", str(data)])
    def flush(self):
        pass

class ErrorOutput:
    def write(self, data):
        send_message(["error", str(data)])
    def flush(self):
        pass

sys.stdout = PrintOutput()
sys.stderr = ErrorOutput()
