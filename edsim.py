import sys
import time
import traceback
import javascript
import random
import json
import math

from vector import *

from browser import document, window, alert, timer, worker, bind, html, load
from browser.local_storage import storage
from collections import deque

load("js/howler.js")
load("js/planck-with-testbed.js")

# Cursor control and motion
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
KEY_PAGEUP        = 0xff55
KEY_PAGEDOWN      = 0xff56
KEY_END           = 0xff57
KEY_BEGIN         = 0xff58


# In web workers, "window" is replaced by "self".
import time
#from browser import bind, self
import sys
import time
import traceback
import javascript
import random
import json
from browser import bind, self, window

edsim_worker = worker.Worker("executor")

test_buff = None
array = None

pl = window.planck

visual_scale = 0.01

class EDSim():
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
    TIME_SECONDS        =  11
    
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
    SPEED_FULL          =  11
    
    CLAP_DETECTED       = True
    CLAP_NOT_DETECTED   = False
        
    #settings
    EdisonVersion   = V2
    DistanceUnits   = CM
    Tempo           = TEMPO_MEDIUM
    
    def __init__(self, ctx, world, screen_width, screen_height, ED_Sim):
        
        self.ctx = ctx
        self.world = world
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.box = None
        self.reset()
        
        self.ED_Sim = ED_Sim                        
        
    def reset(self):
        self.instruction_queue = deque()
        self.current_instruction = None

        self.position           = Vector(250  * visual_scale, 200 * visual_scale)
        self.speed              = 0
        self.heading            = Vector(0, 1)
        self.orientation        = 0
        
        self.current_rotation   = 0
        self.target_rotation    = 0
        self.rotation_speed     = 0
        
        self.current_distance   = 0
        self.target_distance    = 0
        
        self.leftLED            = False
        self.rightLED           = False
        
        self.lineTracker        = False
                
        self.img = html.IMG(src = "images/edsim/ed.png")  
        self.led_img = html.IMG(src = "images/edsim/led.png")
        
        self.height = 64 * visual_scale
        self.width = 62 * visual_scale
        
        if self.box is not None:        
            self.world.destroyBody(self.box)
                
        self.box = self.world.createDynamicBody(pl.Vec2.new(self.position[0], self.position[1]))

        
        vertices1 = [pl.Vec2(-self.width/2,		3.0 * self.height/4),
                    pl.Vec2(self.width/2, 		3.0 * self.height/4),
                    pl.Vec2(self.width/2, 		0),
                    pl.Vec2(-self.width/2, 		0)]
        shape1 = pl.Polygon.new(vertices1)              
        self.box.createFixture(shape1, 0.0)                   
        
        vertices2 = [pl.Vec2(-self.width/2, 	0),
                    pl.Vec2(self.width/2, 		0),
                    pl.Vec2(self.width/2, 		-self.height/4),
                    pl.Vec2(-self.width/2, 		-self.height/4)]
        shape2 = pl.Polygon.new(vertices2)        
        self.box.createFixture(shape2, 0.0)
        
        
        #self.box.createFixture(pl.Circle.new(30 * visual_scale), 10.0);
                
        self.box.setGravityScale(0)   
        
        
    def update(self):
        if self.current_rotation < self.target_rotation:
            self.current_rotation += abs(self.rotation_speed)
            self.orientation += self.rotation_speed
            # correct for overshoot
            if self.current_rotation > self.target_rotation:
                self.orientation -= math.copysign(self.current_rotation - self.target_rotation, self.rotation_speed)
                
            self.box.setAngularVelocity(self.rotation_speed)
        else:
            self.box.setAngularVelocity(0)
            
        if self.current_distance < self.target_distance:
            self.current_distance += abs(self.speed)            
            #self.position += self.heading.rotate(math.degrees(self.box.getAngle()) * self.speed 
            
            heading = self.heading.rotate(math.degrees(self.box.getAngle())) * self.speed
            
            self.box.setLinearVelocity(pl.Vec2.new(heading[0], heading[1]))
        else:
            self.box.setLinearVelocity(pl.Vec2.new(0, 0))
            
            
    def draw(self):
        return
               

class EdSim():
    # states
    STATE_WAIT      =   0
    STATE_STOP      =   1
    STATE_RUN       =   2
    
    def __init__(self):
        global array
        
        
        self.canvas = document["canvas"]
        self.ctx = self.canvas.getContext('2d')		
        
        self.width = self.canvas.width
        self.height = self.canvas.height   
        
        self.bg = html.IMG(src = "images/edsim/carpet.jpg", id="bg", style={"display": "none"}) 
        document <= self.bg
        
        self.ball_img = html.IMG(src = "images/edsim/ball.png")  
        self.img = html.IMG(src = "images/edsim/ed.png")  
        
        self.bgcolor = Vector(0, 0, 0, 1)
        
        self.clap_timer = 0
        self.clap_time = 500
        
        self.anim_timer = 0
        self.anim_time = 200
        
        self.blink_running = 300
        
        self.starting_text = "Starting up"
        self.show_playing_text = True
        
        self.keys = dict([(a, False) for a in range(255)] +
                         [(a, False) for a in range(0xff00, 0xffff)]) 
                         
        document.bind("keydown", self._keydown)
        document.bind("keyup", self._keyup)           
                
        test_buff = window.SharedArrayBuffer.new(512)
        array = window.Int8Array.new(test_buff)
        
        window.console.log("Attempting to send shared data")
        edsim_worker.send(test_buff) 
        
        howl = window.Howl
        self.clap_sound = howl.new({"src": ["audio/clap.mp3"]})
        self.beep_sound = howl.new({"src": ["audio/beep.mp3"]})

        self.state = self.STATE_WAIT
        self.interval_timer = timer.set_interval(self.update, 16)
        
        self.debug_draw = True
        
        ####### Begin box2d physics

        self.world = pl.World.new(pl.Vec2.new(0, -1000 * visual_scale));
        
        # dictionary of ID to dynamic bodies
        self.bodies = {}
        
        # screen edges
        # bottom
        self.world.createBody().createFixture(pl.Edge.new(pl.Vec2(0.0, 0.0), pl.Vec2.new(self.width * visual_scale, 0.0)), 0.0);
        # left
        self.world.createBody().createFixture(pl.Edge.new(pl.Vec2(0.0, 0.0), pl.Vec2.new(0, self.height * visual_scale)), 0.0);
        # right
        self.world.createBody().createFixture(pl.Edge.new(pl.Vec2(self.width * visual_scale, 0.0), pl.Vec2.new(self.width  * visual_scale, self.height * visual_scale)), 0.0);       
        # top
        self.world.createBody().createFixture(pl.Edge.new(pl.Vec2(self.width * visual_scale, self.height * visual_scale), pl.Vec2.new(0, self.height * visual_scale)), 0.0);
                
        self.lineTrackerRef = [0,0,0,0]

        self.ed = EDSim(self.ctx, self.world, self.width, self.height, self)

        ####### End box2d physics        
        
        self.reset()

    def reset(self):
        self.ed.reset()        
        global array
        array[KEY_ESC] = 0
        
    def removeAllBodies(self):
        for body in self.bodies.keys():
            self.world.destroyBody(body)
        self.bodies = {}
        
    def addBall(self, id, x, y, radius):
        new_ball = self.world.createDynamicBody(pl.Vec2.new(x * visual_scale, y * visual_scale))        
        new_ball.createFixture(pl.Circle.new(radius * visual_scale), {"restitution": 0.2, "friction": 1.0, "density": 1.0})
        new_ball.setAngularDamping(0.1)
        new_ball.setLinearDamping(0.2)
        new_ball.setGravityScale(0)
        self.bodies[id] = new_ball
        
    def removeBall(self, id):
        self.world.destroyBody(self.bodies[id])
        del self.bodies[id]                
        
    def _keydown(self, ev):
        window.console.log("key pressed!" + str(ev.which));
        
        self.keys[ev.which] = True
        
        global array
        
        if ev.which == KEY_C:
            if self.clap_timer <= 0:
                # clapping
                self.clap_timer = self.clap_time
                self.clap_sound.play()
                        
        array[ev.which] = 1

    def _keyup(self, ev):
        self.keys[ev.which] = False      

        global array
        array[ev.which] = 0  

    def playBeep(self):
        self.beep_sound.play()
        
    def stop(self):        
        #timer.clear_interval(self.interval_timer)
        # remove all bodies
        self.removeAllBodies()
        self.ed.reset()
        
    def clearclap(self):
        self.clap_timer = 0
        # no need to change the shared array because the worker would have done this
        
    def drawDebugLine(self):  
        return    
        imageData = Ed.ctx.getImageData(0, 0, self.width, self.height)        
                
        radians = math.radians(90 + self.ed.orientation)
        dx = math.cos(radians)
        dy = math.sin(radians)
        
        x = self.ed.position[0]
        y = self.height - self.ed.position[1]
        
        for n in range(200):        
            imageData.data[(((int(y)) * self.width + int(x)) << 2) + 1] = 0
            #imageData.data[((self.height - int(y)) * self.width + int(x)) * 4 + 1] = 255
            #imageData.data[((self.height - int(y)) * self.width + int(x)) * 4 + 2] = 0
            #imageData.data[((self.height - int(y)) * self.width + int(x)) * 4 + 3] = 255
            
            x += dx
            y -= dy    
            
            if x < 0 or x > self.width:
                break
            elif y < 0 or y > self.height:
                break
            
        Ed.ctx.putImageData(imageData, 0, 0) 
        return
        
    def drawCircle(self, x, y, radius, r=1.0, g=1.0, b=1.0, a=1.0):
        r = min(r, 1.0)
        g = min(g, 1.0)
        b = min(b, 1.0)
        a = min(a, 1.0)

        self.ctx.fillStyle = "rgba(" + str(int(r * 255.0)) + "," + str(int(g * 255.0)) + "," + str(int(b * 255.0)) + "," + str(int(a * 255.0)) + ")"
        self.ctx.beginPath();
        self.ctx.strokeStyle = "rgba(" + str(int(r * 255.0)) + "," + str(int(g * 255.0)) + "," + str(
            int(b * 255.0)) + "," + str(int(a * 255.0)) + ")"

        self.ctx.arc(x, self.height - y, radius, 0, 2 * math.pi, True);

        self.ctx.stroke()   

    def getLineTrackerSensor(self):
        pixel = window.Int8Array.new(4)      
        
        # TODO: adjust this so that the sensor is at the tip of the edison
        # right now it's at the centre of mass
        x = self.ed.box.getPosition().x  / visual_scale
        y = self.height - self.ed.box.getPosition().y / visual_scale
            
        imageData = Ed.ctx.getImageData(x, y, 1, 1);
        
        window.console.log("current pixel:" + str(x), str(y) , str(imageData.data[0]) + ","+ str(imageData.data[1]) + ","+ str(imageData.data[2]) + ","+ str(imageData.data[3]))
        
        return imageData.data
        
    def setReferenceBrightness(self):
        self.ctx.save()
        self.ctx.drawImage(self.bg, 0, 0)#, self.width, self.height)
        pixel = self.getLineTrackerSensor()
        # brightness = sum of squares
        self.ref_brightness = (pixel[0] ** 2 + pixel[1] ** 2 + pixel[2] ** 2)   
        self.ctx.restore()
        
        window.console.log("ref brightness:" + str(self.ref_brightness))      

    def readLineState(self):
        if Ed.ed.lineTracker:
            pixel = self.getLineTrackerSensor()
            brightness = (pixel[0] ** 2 + pixel[1] ** 2 + pixel[2] ** 2)
            
            delta = brightness - self.ref_brightness
            if delta > 50:
                array[511] = 1      # LINE_ON_WHITE
            else:
                array[511] = 0      # LINE_ON_BLACK
        else:
            array[511] = -1         # line tracking is not on, so N/A
        window.console.log(array[511])

    def drawShape(self, points, r=1.0, g=1.0, b=1.0, a=1.0):
        r = min(r, 1.0)
        g = min(g, 1.0)
        b = min(b, 1.0)
        a = min(a, 1.0)

        self.ctx.fillStyle = "rgba(" + str(int(r * 255.0)) + "," + str(int(g * 255.0)) + "," + str(int(b * 255.0)) + "," + str(int(a * 255.0)) + ")"

        self.ctx.strokeStyle = "rgba(" + str(int(r * 255.0)) + "," + str(int(g * 255.0)) + "," + str(
            int(b * 255.0)) + "," + str(int(a * 255.0)) + ")"

        self.ctx.beginPath()        
        
        for n, point in enumerate(points):
            if n == 0:
                self.ctx.moveTo(point[0], - point[1])
            self.ctx.lineTo(point[0], - point[1])
        self.ctx.closePath()

        self.ctx.stroke()      
                
    def update(self):    
        self.anim_timer -= 16
        if self.anim_timer <= 0:
            self.anim_timer = 0
            
        if self.state == self.STATE_WAIT:
            self.ctx.fillStyle = "#000000"; 
            self.ctx.fillRect(0, 0, self.width, self.height)   
            self.ctx.fillStyle = "#ffffff"; 
            self.ctx.font = "40px Georgia";
            
            if self.anim_timer <= 0:
                self.anim_timer = self.anim_time
                
                self.starting_text += "."
                if self.starting_text.count(".") > 5:
                    self.starting_text = self.starting_text[:-5]
            self.ctx.fillText(self.starting_text, 100, 200); 

        else:
            # update


            
            # count down the clap for debounce
            self.clap_timer -= 16
            if self.clap_timer <= 0:
                self.clap_timer = 0
                array[KEY_C] = 0
            else:
                array[KEY_C] = 1
                
            self.ed.update()
                                                       
            # render
            # clear the screen
            
            self.ctx.fillStyle= "rgba(" + str(int(self.bgcolor[0] * 255.0)) + \
                                "," + str(int(self.bgcolor[1] * 255.0)) + \
                                "," + str(int(self.bgcolor[2] * 255.0)) + \
                                "," + str(int(self.bgcolor[3] * 255.0))+ ")"
            
            self.ctx.fillRect(0, 0, self.width, self.height)                          
            self.ctx.drawImage(self.bg, 0, 0)#, self.width, self.height)
            
            # getting the image pixel data underneath the edision
            # need to call this before drawing the edison, otherwise the pixels of the
            # edison will be read instead of the background
            self.readLineState()
            
            self.ctx.save()
            x = self.ed.box.getPosition().x  / visual_scale
            y = self.height - self.ed.box.getPosition().y / visual_scale
            width = self.ed.width  / visual_scale
            height = self.ed.height  / visual_scale
            anchorX = 0.5
            anchorY = 0.75            
            
            orientation = self.ed.box.getAngle()
            
            self.ctx.translate(x, y)
            self.ctx.rotate(-orientation)
            self.ctx.drawImage(self.ed.img, -anchorX * width, -anchorY * height, width, height)
            
            if self.ed.leftLED:
                anchorX = 0.3
                anchorY = 0.75            
                self.ctx.drawImage(self.ed.led_img, -anchorX * width, -anchorY * height)
            
            if self.ed.rightLED:
                anchorX = -0.15
                anchorY = 0.75            
                self.ctx.drawImage(self.ed.led_img, -anchorX * width, -anchorY * height)
            
            self.ctx.restore()
                        


            ### Begin Physics
            
            self.world.step(1/60)
            
            for body in self.bodies.values():
                pos = body.getPosition()
                orientation = body.getAngle()
                radius = body.getFixtureList().getShape().getRadius() / visual_scale
                
                self.drawCircle(pos.x / visual_scale, pos.y / visual_scale, 10, 1, 0, 0)                               
                
                self.ctx.save()
                self.ctx.translate(pos.x / visual_scale, self.height - pos.y / visual_scale)
                self.ctx.rotate(-orientation)
                self.ctx.drawImage(self.ball_img, - radius, - radius, radius * 2, radius * 2)            
                self.ctx.restore()                             
            
            self.ed.draw()
            
            ### End Physics
            
            if self.debug_draw:
                self.drawDebugLine()

            if self.state == self.STATE_RUN:
                if self.anim_timer <= 0:
                    self.anim_timer = self.blink_running
                
                    self.show_playing_text = not self.show_playing_text
                if self.show_playing_text:
                    self.ctx.fillStyle = "#ffffff"; 
                    self.ctx.font = "20px Georgia";                    
                    self.ctx.fillText("Running...", 10, 30);  
            
            #self.ctx.drawImage(self.ed.img, self.ed.position[0] - self.ed.width//2, \
            #                                self.height - self.ed.position[1] - self.ed.height//2)
                                        
Ed = EdSim()

@bind(edsim_worker, "message")
def onmessage(e):
    """Handles the messages sent by the worker."""
    Ed.ed.instruction_queue.append((e, False))
    if e.data[0] == "drive":
        window.console.log("New Drive() call.");
        speed = int(e.data[2]) * 0.25
        if e.data[1] == EDSim.BACKWARD or e.data[1] == EDSim.FORWARD: 
            if e.data[1] == EDSim.BACKWARD: 
                Ed.ed.speed = -speed
            else:
                Ed.ed.speed = speed 
            Ed.ed.current_distance = 0
            Ed.ed.target_distance = int(e.data[3] * 5)  # depends on UNITs                
        elif e.data[1] == EDSim.SPIN_RIGHT or e.data[1] == EDSim.SPIN_LEFT:
            if e.data[1] == EDSim.SPIN_RIGHT:
                Ed.ed.rotation_speed = -speed
            else:            
                Ed.ed.rotation_speed = speed
            Ed.ed.current_rotation = 0
            Ed.ed.target_rotation = int(e.data[3])
    elif e.data[0] == "clearclap":
        Ed.clearclap()
    elif e.data[0] == "beep":
        Ed.playBeep()
    elif e.data[0] == "LED":
        if e.data[1] == True:
            Ed.ed.rightLED = e.data[2]         
        else:
            Ed.ed.leftLED = e.data[2]
    elif e.data[0] == "addBall":
        Ed.addBall(e.data[1], e.data[2], e.data[3], e.data[4])
    elif e.data[0] == "removeBall":
        Ed.removeBall(e.data[1])

    elif e.data[0] == "waitdone":
        window.console.log("finished waiting");
        if Ed.state == Ed.STATE_WAIT:
            Ed.state = Ed.STATE_STOP    
        else:
            Ed.state = Ed.STATE_RUN                           
    elif e.data[0] == "stop":
        window.console.log("stopped");            
        Ed.state = Ed.STATE_STOP
    elif e.data[0] == "print":
        do_print(e.data[1])
    elif e.data[0] == "error":
        do_print(e.data[1], "red")        
    elif e.data[0] == "linetracker":
        Ed.ed.lineTracker = e.data[1]
        if e.data[1]:
            Ed.setReferenceBrightness()

def format_string_HTML(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("\"", "&quot;").replace("'", "&apos;").replace(" ", "&nbsp;")

def do_print(s, color=None):
    if color is not None: window.writeOutput("<p style='display:inline;color:" + color + ";'>" + format_string_HTML(s) + "</p>", True)
    else: window.writeOutput("<p style='display:inline;'>" + format_string_HTML(s) + "</p>", True)

def clear_button_run():
    document["runPlay"].style.display = "none"
    document["runPlayLoad"].style.display = "none"
    document["runPause"].style.display = "none"
    document["runResume"].style.display = "none"
    for event in document["run"].events("click"):
        document["run"].unbind("click", event)
    document["run"].bind("click", save_code)

def button_play(event):   
    if Ed.state == Ed.STATE_WAIT:
        return
    window.console.log("resetting..")
    Ed.reset()
    
    clear_button_run()
    document["runPlayLoad"].style.display = "inherit"
    document["run"].bind("click", button_pause)
    do_play()

def do_play():
    window.console.log("Getting code")
    src = window.getCode()
    
    window.console.log(src)
    try:
        success = True
        try:
            # try and run the code in the web worker!!!!
            edsim_worker.send(["run", src])
        except Exception as exc:
            alert("Error!");
            traceback.print_exc(file=sys.stderr)
            handle_exception()
            success = False
        clear_button_run()
        document["runPause"].style.display = "inherit"
        document["run"].bind("click", button_pause)
    except:
        pass

def button_pause(event):
    Ed.stop()
    global array
    array[KEY_ESC] = 1
    clear_button_run()
    document["runResume"].style.display = "inherit"
    document["run"].bind("click", button_play)

def button_resume(event):
    clear_button_run()
    document["runPause"].style.display = "inherit"
    document["run"].bind("click", button_pause)

def save_code(event):
    window.saveCode()        
        
###################################################################################        




