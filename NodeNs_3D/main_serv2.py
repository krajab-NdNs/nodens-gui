## TODO: two versions: diagnostics (D) and user (U)
## TODO: view saved data
## TODO: plot scatter points in range only + different colour for target points - done: read tid for each point but need to check results (tlv is too long).

import os
os.environ["KIVY_LOG_MODE"] = "PYTHON"
from kivy.logger import Logger, LOG_LEVELS
Logger.setLevel(LOG_LEVELS["info"])

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.factory import Factory
from kivy.resources import resource_add_path, resource_find
from kivy.core.window import Window
from kivy.graphics import Line, Color, Bezier
from kivy.graphics import Rectangle as kv_Rectangle
from kivy.logger import Logger, LOG_LEVELS

from random import randint
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from numpy.random import seed
from numpy.random import rand
from math import sqrt as sqrt
from random import random as random
import base64
import paho.mqtt.client as mqtt
import json
import datetime
import time
from os.path import dirname, join as pjoin
from pathlib import Path
import logging
import csv
import nodens_fns as ndns_fns
import nodens_mesh as ndns_mesh
import nodens_gcp as ndns_gcp
import os, sys
from termcolor import colored

seed(1)

global idx_json
global num_json
global json_data
global frame_num
global data10
global size
global mqttDataN, mqttData_SAVE, idx_mqtt
global frame_last
global T
global L6
global nTLV
global client
global sts, track11, UD12
global ud_x, ud_y, ud_z, ud_len, ud_idx
global heartbeat
global file_save
global config_msg

if getattr(sys, 'frozen', False):
    # this is a Pyinstaller bundle
    resource_add_path(sys._MEIPASS)

Logger.setLevel(LOG_LEVELS["info"])

mqttData = 0
json_data = {}
idx_json = 0 # initialise counter to track JSON entries
num_json = 0 # initialise counter to track number of JSON files
frame_num = []
frame_num2 = []
frame_last = 0
T = []
L6 = []
nTLV = []
track11 = []
mqttData_SAVE = []
mqttData_SAVEFull = []
idx_mqtt = 0
idx_write = 0
idx_file_refresh = 0
heartbeat = ""
cfg_idx = 0
config_msg = ''

si = ndns_fns.si
ew = ndns_fns.entry_ways()
oh = ndns_fns.OccupantHist()
sm = ndns_fns.SensorMesh()

#logging.basicConfig(level=logging.info)


  

# ----------- Rx Data, Process, Plot ------ #
class sensorTimeSeries:
    def __init__(self):
        self.frame = []
        self.packet_len = []
        self.num_tlv = []
        self.num_pnts = []
        self.num_tracks = []

    def update(self, sensor_data, max_time_samples = 0):
        self.frame.append(sensor_data.frame)
        self.packet_len.append(sensor_data.packet_len)
        self.num_tlv.append(sensor_data.num_tlv)
        self.num_pnts.append(sensor_data.pc.num_obj)
        self.num_tracks.append(sensor_data.track.num_tracks)

        if max_time_samples < 0:
            print("WARNING: max_time_samples (= {}) must be greater than 0. Setting to 0.")
        elif max_time_samples > 0:
            if len(self.frame) > max_time_samples:
                self.frame = self.frame[1:]
                self.packet_len = self.packet_len[1:]
                self.num_tlv = self.num_tlv[1:]
                self.num_pnts = self.num_pnts[1:]
                self.num_tracks = self.num_tracks[1:]


# --------- Kivy Filechooser ----------- #
class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)
    filechooser = ObjectProperty(None)

    def initialise(self):
        # Load history
        print("load init")
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()
        self.ids.text_input.text = history_settings["Save file"]
        self.ids.filechooser.path = history_settings["Save folder"]
        print("\r init done")


class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)
    filechooser = ObjectProperty(None)
    
    def initialise(self):
        # Load history
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()
        self.ids.text_input.text = history_settings["Save file"]
        self.ids.filechooser.path = history_settings["Save folder"]


def load_switch_callback(instance, value):
    print('the load switch', instance, 'is', value)

def monitor_pc_switch_callback(instance, value):
    print('the monitoring zone point cloud switch', instance, 'is', value)

def alarm_sounds_switch_callback(instance, value):
    print('the alarm sounds switch', instance, 'is', value)


class Root(FloatLayout):
    loadfile = ObjectProperty(None)
    savefile = ObjectProperty(None)
    text_input = ObjectProperty(None)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        print("show_load_0")
        content = LoadDialog(load=self.parent.load, cancel=self.parent.dismiss_popup)
        content.initialise()
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_save(self):
        print("show_save_0")
        content = SaveDialog(save=self.parent.save, cancel=self.parent.dismiss_popup)
        
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        print("load here")
        with open(os.path.join(path, filename[0])) as stream:
            self.text_input.text = stream.read()
            print(self.text_input.text)

        self.dismiss_popup()

    def save(self, path, filename):
        print("Root save")
        with open(os.path.join(path, filename), 'w') as stream:
            stream.write(self.text_input.text)

        self.dismiss_popup()        
        
# --------- Kivy classes ---------- #

class Editor(App):
    pass

class ConfigEntries(BoxLayout):
    entry_min = ObjectProperty(None)
    def __init__(self, **kwargs):
        super(ConfigEntries, self).__init__(**kwargs)

class LEDStatus(BoxLayout):
    def __init__(self, **kwargs):
        super(LEDStatus, self).__init__(**kwargs)

class Tooltip(Label):
    pass

class DrawingScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Window properties
        #Window.maximize()
        Window.bind(on_resize=self.on_window_resize)
        self._window_size = Window.size
        print(f"DS WS. {self._window_size}")

    
    def on_window_resize(self, window, width, height):
        self._window_size = Window.size


# --------- TEMP: move to nodens_fns ---------- #
class UD_params:
    def __init__(self):
        self.tid = []        
        self.num_pnts = []
        self.el_mean = []
        self.el_max = []
        self.el_min = []
        self.dopp_mean = []
        self.dopp_max = []
        self.dopp_min = []
        

    def update(self, raw, ud_len, ud_idx):
        if len(raw) == 0:
            self.num_tracks = 0
        else:
            self.num_tracks = int(np.uint8(raw[8:10]).view(np.uint16))
            if ud_idx == ud_len:
                for i in range(self.num_tracks):
                    self.tid[i] = []
                    self.num_pnts[i] = []
                    self.el_mean[i] = []
                    self.el_max[i] = []
                    self.el_min[i] = []
                    self.dopp_mean[i] = []
                    self.dopp_max[i] = []
                    self.dopp_min[i] = []

        for i in range(self.num_tracks):
            temp_tid = np.uint8(raw[(10+22*i):(12+22*i)]).view(np.uint16)
            if (temp_tid in self.tid):
                temp_ind = self.tid.index(temp_tid)
                self.num_pnts[temp_ind].append(np.uint8(raw[(12+22*i):(14+22*i)]).view(np.uint16))
                
                self.el_mean[temp_ind].append(np.uint8(raw[(17+22*i)]).view(np.int8)*0.01)
                self.el_max[temp_ind].append(np.uint8(raw[(18+22*i)]).view(np.uint8)*0.01)
                self.el_min[temp_ind].append(-(np.uint8(raw[(19+22*i)]).view(np.uint8)*0.01))
                
                self.dopp_mean[temp_ind].append(np.uint8(raw[(26+22*i):(28+22*i)]).view(np.int16))
                self.dopp_max[temp_ind].append(np.uint8(raw[(28+22*i):(30+22*i)]).view(np.uint16))
                self.dopp_min[temp_ind].append(-np.uint8(raw[(30+22*i):(32+22*i)]).view(np.uint16))
            else:
                self.tid.append(temp_tid)
                self.num_pnts.append([np.uint8(raw[(12+22*i):(14+22*i)]).view(np.uint16)])
                self.el_mean.append([np.uint8(raw[(17+22*i)]).view(np.int8)*0.01])
                self.el_max.append([np.uint8(raw[(18+22*i)]).view(np.uint8)*0.01])
                self.el_min.append([-(np.uint8(raw[(19+22*i)]).view(np.uint8)*0.01)])
                self.dopp_mean.append([np.uint8(raw[(26+22*i):(28+22*i)]).view(np.int16)])
                self.dopp_max.append([np.uint8(raw[(28+22*i):(30+22*i)]).view(np.uint16)])
                self.dopp_min.append([-(np.uint8(raw[(30+22*i):(32+22*i)]).view(np.uint16))])

            j = int(ud_idx/5)            
            
            print("elmn = {}. elmx = {}. elmi = {}".format(self.el_mean, self.el_max, self.el_min))

class LED_Indicator(Widget):
    #Widget.color = ListProperty((1, 0, 0, 1))
    color = (1, 0, 0, 1)

   
    def update(self):
        #Widget.color = ListProperty((0, 1, 0, 1))
        self.color = (0, 1, 0, 1)
        #self.color = (self.color[::-1])



class NodeNsUpdateProcedure(Widget):
    global client
    global sts, UD12
    global ud_x, ud_y, ud_z, ud_len, ud_idx
    global file_save
    global cfg_idx

    box = ObjectProperty(None)
    led_1 = ObjectProperty(LED_Indicator)
    fig1 = ObjectProperty(None)
    fig2 = ObjectProperty(None)
    fig3 = ObjectProperty(None)
    fig4 = ObjectProperty(None)
    fig5 = ObjectProperty(None)
    ax4 = ObjectProperty(None)
    btn_1 = ObjectProperty(None)
    ai_sense_config = ObjectProperty(None)
    ai_room_config = ObjectProperty(None)
    text_room_config = ObjectProperty(None)

    #loadfile = ObjectProperty(None)
    #savefile = ObjectProperty(None)
    #text_input = ObjectProperty(None)
    #filechooser = ObjectProperty(None)

    ud_len = 40
    ud_num_chirps = 64
    ud_idx = 0
    sts = sensorTimeSeries()
    UD12 = UD_params()
    
    ny, nx = (ud_num_chirps, ud_len)
    X = range(nx)
    Y = range(ny)
    ud_x, ud_y = np.meshgrid(X, Y)
    ud_z = np.zeros((ud_num_chirps, ud_len))

    Factory.register('Root', cls=Root)
    Factory.register('LoadDialog', cls=LoadDialog)
    Factory.register('SaveDialog', cls=SaveDialog)
    
    _area_size = ListProperty()
    _area_pos = ListProperty()
    _window_size = ListProperty()
    tooltip = Tooltip(text='')

    _drawing_state = 2
    _drawing_init = 1
    _touch = []
    line = []
    line_xy = []
    line_status = []
    line_zone_type = []
    line_draw_type = []
    zone_type = "safe"
    zone_color = [0,1,0,1]
    zone_msg_sent_status = 'none'
    clock = []

    boundary_xy = []
    border_xy = [0.25,0.5,0.1,0.8]
    

    load_file = ""
    load_data = []
    full_data_flag = False
    
    
    #player1 = ObjectProperty(None)
    #player2 = ObjectProperty(None)

    def initialise(self):
        print("initialise")
        global ud_x, ud_y, ud_z, sd, file_save, T_jwt_refresh
        #self.led_1.center = self.center
        sd = ndns_fns.parseTLV(3)
        #cp = ndns_fns.config_params()


        plt.rcParams.update({'font.size': 20})

        ## ~~~~~~~ Initialise plots ~~~~~~~~~ ##
        self.initialise_plots()

        self._window_size = Window.size
        self._area_pos = [0.25*self._window_size[0] + self.ids.drawing_screen.pos[0], 0.1*self._window_size[1]]
        self._area_size = [0.5*self._window_size[0], 0.8*self._window_size[1]]
        Window.bind(on_resize=self.on_window_resize)

        Window.bind(mouse_pos=self.on_mouse_pos)
        Window.add_widget(self.tooltip)  
        self.X_OFFSET = 0.11*self._window_size[0]

        # ~~~~~~~ Boundaries ~~~~~~~~~~~~ #
        

        ##
        ##~~~~~~~~ Load history ~~~~~~~~
        ##
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()
        print(history_settings)

        # ~~~~~~~ Boundaries ~~~~~~~~~~~~ #
        if 'Room' in history_settings:
            X = history_settings['Room']['X']
            Y = history_settings['Room']['Y']
            self.ids.room_x_min.text = f"{X[0]}"
            self.ids.room_x_max.text = f"{X[1]}"
            self.ids.room_y_min.text = f"{Y[0]}"
            self.ids.room_y_max.text = f"{Y[1]}"
        else:
            X = [float(self.ids.room_x_min.hint_text), float(self.ids.room_x_max.hint_text)]
            Y = [float(self.ids.room_y_min.hint_text), float(self.ids.room_y_max.hint_text)]
            if self.ids.room_x_min.text != '':
                X[0] = float(self.ids.room_x_min.text)
            if self.ids.room_x_max.text != '':
                X[1] = float(self.ids.room_x_max.text)
            if self.ids.room_y_min.text != '':
                Y[0] = float(self.ids.room_y_min.text)
            if self.ids.room_y_max.text != '':
                Y[1] = float(self.ids.room_y_max.text)
        
        self.boundary_xy = [X[0], X[1], Y[0], Y[1]]
        #self.ids.sensor_id.text = history_settings["Sensor id"]
        #self.ids.root_id.text = history_settings["Root id"]

        self.ids.ip_add.text = history_settings["ip"]
        file_save = pjoin(history_settings["Save folder"], 
                          history_settings["Save file"])
        print(f"file: {file_save}")
        load_switch = Switch()
        load_switch.bind(active=load_switch_callback)
        if history_settings["Save state"] == 'True':
            self.ids.load_switch.active = True
            self.ids.load_button.disabled = False
            ndns_fns.cp.WRITE_FLAG = 1
            self.load(history_settings["Save folder"],history_settings["Save file"])
        else:
            self.ids.load_switch.active = False
            self.ids.load_button.disabled = True
            ndns_fns.cp.WRITE_FLAG = 0

        # ~~~~~~~ Monitoring zone ~~~~~~~~~~~~ #
        if 'Zones' in history_settings:
            self._window_size = Window.size
            #self.ids.monitor_zones_config.collapse = False
            with self.canvas:
                for zones in history_settings["Zones"]:
                    # Define colour based on zone type
                    if zones["Zone"].lower() == "safe":
                        self.zone_color = [0,1,0,0]
                    else:
                        self.zone_color = [1,0,0,0]
                    Color(self.zone_color[0],self.zone_color[1],self.zone_color[2],self.zone_color[3])

                    # Zone type (safe/exclusion)
                    self.line_zone_type.append(zones["Zone"].lower())
                    self.line_status.append(0)
                    # Check which sort of zone
                    if zones["Type"].lower() == "rectangle":
                        
                        self.line_xy.append(kv_Rectangle(pos=(zones["X"][0], zones["Y"][0]), size=(zones["X"][1], zones["Y"][1]), width=2, rgba=self.zone_color))
                        screen_xy = self.transform_xy_to_screen([zones["X"][0],zones["Y"][0]], self.boundary_xy, self.border_xy)
                        screen_xy1 = self.transform_xy_to_screen([zones["X"][1],zones["Y"][1]], self.boundary_xy, self.border_xy)
                        self.line.append(kv_Rectangle(pos=(screen_xy[0], screen_xy[1]), size=(screen_xy1[0], screen_xy1[1]), width=2, rgba=self.zone_color))
                        self.line_draw_type.append('r')
                    else:                       
                        for i in range(len(zones["X"])):
                            xy = self.transform_xy_to_screen([zones["X"][i],zones["Y"][i]], self.boundary_xy, self.border_xy)
                            if i == 0:
                                self.line_status.append(0)
                                if zones["Type"].lower() == "line":
                                    self.line_draw_type.append(['l'])
                                    self.line_xy.append(Line(points=[zones["X"][i],zones["Y"][i]], width=2))
                                    self.line.append(Line(points=[xy[0], xy[1]], width=2))
                                elif zones["Type"].lower() == "bezier":
                                    self.line_draw_type.append(['b'])
                                    self.line_xy.append(Bezier(points=[zones["X"][i],zones["Y"][i]], width=20))
                                    self.line.append(Bezier(points=[xy[0], xy[1]], width=20))
                                elif zones["Type"].lower() == "mixed":
                                    if "draw_type" in zones:
                                        self.line_draw_type.append([zones["draw_type"][i]])  
                                    else:
                                        self.line_draw_type.append(['l'])      
                            else:
                                self.line_xy[-1].points += (zones["X"][i],zones["Y"][i])
                                self.line[-1].points += (xy[0], xy[1])
                                if zones["Type"].lower() == "line":
                                    self.line_draw_type[-1].append('l')
                                elif zones["Type"].lower() == "bezier":
                                    self.line_draw_type[-1].append('b')
                                elif zones["Type"].lower() == "mixed":
                                    if "draw_type" in zones:
                                        self.line_draw_type[-1].append([zones["draw_type"][i]])  
                                    else:
                                        self.line_draw_type[-1].append(['l'])
            #self.ids.monitor_zones_config.collapse = True

            # The following is to resize the rectangles for the canvas
            self._window_size = Window.size
            self._area_pos = [0.25*self._window_size[0] + self.ids.drawing_screen.pos[0], 0.1*self._window_size[1]]
            self._area_size = [0.5*self._window_size[0], 0.8*self._window_size[1]]
            # self._area_pos = self._area_pos
            # self._area_size = self._area_size


            for i, line_xy in enumerate(self.line_xy):
                if self.line_zone_type == "safe":
                    self.zone_color = [0,1,0,0]
                else:
                    self.zone_color = [1,0,0,0]
                if self.line_draw_type[i] == 'r':
                    screen_xy = self.transform_xy_to_screen(line_xy.pos, self.boundary_xy, self.border_xy)
                    screen_xy1 = [0,0]
                    screen_xy1[0] = line_xy.pos[0] + line_xy.size[0]
                    screen_xy1[1] = line_xy.pos[1] + line_xy.size[1]
                    screen_xy1 = self.transform_xy_to_screen(screen_xy1, self.boundary_xy, self.border_xy)
                    screen_xy1[0] -= screen_xy[0]
                    screen_xy1[1] -= screen_xy[1]
                    self.line[i].pos = screen_xy#kv_Rectangle(pos=(screen_xy[0], screen_xy[1]), size=(screen_xy1), width=2, rgba=self.zone_color)
                    self.line[i].size = screen_xy1


        ## ~~~~~~~ Monitoring zone ~~~~~~~~~ ##
        monitor_pc_switch = Switch()
        monitor_pc_switch.bind(active=monitor_pc_switch_callback)

        alarm_sounds_switch = Switch()
        alarm_sounds_switch.bind(active=alarm_sounds_switch_callback)
        
        ##~~~~~~~~ Initialise spinner with list of root and sensor IDs ~~~~~~~~##
        self.ids.root_spinner.text = "Not connected..."
        self.ids.root_spinner.values = ["None"]
        self.ids.sensor_spinner.text = "Not connected..."
        self.ids.sensor_spinner.values = ["None"]



        sm = ScreenManager()
        self.drawing_screen = DrawingScreen(name="drawing")

        
        self.drawing_screen._area_pos = self._area_pos
        self.drawing_screen._area_size = self._area_size

        # Draw rectangle
        self.ids.draw_rectangle_button.bind(on_press=self.draw_rectangle)
        #self.drawing_screen.add_widget(self.ids.draw_rectangle_button)

        # Draw line
        self.ids.draw_line_button.bind(on_release=self.draw_line)
        #self.drawing_screen.add_widget(self.ids.draw_line_button)

        # Draw arc
        self.ids.draw_arc_button.bind(on_release=self.draw_arc)
        #self.drawing_screen.add_widget(self.ids.draw_arc_button)

        # Draw free
        self.ids.draw_free_button.bind(on_release=self.draw_free)
        #self.drawing_screen.add_widget(self.ids.draw_free_button)

        # Undo button
        self.ids.undo_button.bind(on_release=self.undo_last)
        #self.drawing_screen.add_widget(self.ids.undo_button)

        # Define zones (green/red)
        self.ids.zone_type_button.bind(on_release=self.zone_switch)
        #self.drawing_screen.add_widget(self.zone_type_button)

        # Close shape
        self.ids.close_shape_button.bind(on_release=self.close_shape)
        #self.drawing_screen.add_widget(self.close_shape_button)

        # Accordion buttons
        self.ids.monitor_zones_config.bind(collapse=self.close_monitor_zone)
        self.ids.ai_sensor_config.bind(collapse=self.open_monitor_zone)
        self.ids.sensor_data_plots.bind(collapse=self.open_sensor_data_plots)

        #sm.add_widget(self.drawing_screen)
        l = Label(text='Hello world')


        # Bit of a hacky solution to activate the blue monitor zone area
        if self.clock == []:
            self.clock = Clock.schedule_once(self.update_mon_zone, 0.005)
            #self.clock.cancel()

        return sm
    
    def initialise_plots(self):
        idx_file_refresh = 0

        x = np.array([0])
        y = np.array([1])
        z = np.array([0])

        levels = MaxNLocator(nbins=15).tick_values(ud_z.min(), ud_z.max())

        # pick the desired colormap, sensible levels, and define a normalization
        # instance which takes data values and translates those into levels.
        cmap = plt.get_cmap('cool')
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

        self.fig1 = plt.figure()
        ax1 = self.fig1.add_subplot()
        cf = ax1.contourf(ud_x, ud_y, ud_z,
                  levels=levels,
                  cmap=cmap)
        #self.fig1.colorbar(cf, ax=ax1)
        ax1.set_title('Micro-Doppler spectrum')
        ax1.set_xlabel('Doppler')
        ax1.set_ylabel('Time')
        self.box_1.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig1.number)))

        self.fig2 = plt.figure()
        ax2 = self.fig2.add_subplot(projection='3d')
        ax2.scatter(x,y,z)
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        ax2.set_zlabel('Z (m)')
        self.box_2.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig2.number)))
        
        self.fig3 = plt.figure()
        plt.plot([])
        plt.title('Micro-Doppler parameters')
        plt.xlabel('Time')
        plt.ylabel('Height')
        self.box_3.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig3.number)))
        
        self.fig4 = plt.figure()
        plt.plot([])
        plt.title('Parameter checks')
        plt.xlabel('Frame')
        self.box_4.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig4.number)))

        self.fig5 = plt.figure()
        plt.plot([])
        plt.title('Number of points')
        plt.xlabel('Frame')
        self.box_5.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig5.number)))

        # Room config figure
        self.fig_room_cfg = plt.figure()
        ax_rc = self.fig_room_cfg.add_subplot()
        ax_rc.add_patch( Rectangle((-4,0),
                        8, 6,
                        fc ='none', 
                        ec ='g',
                        lw = 2) )
        ax_rc.scatter(x,y)
        
        ax_rc.set_xlabel('X (m)')
        ax_rc.set_ylabel('Y (m)')
        ax_rc.set_ylim(0, 6)
        ax_rc.set_xlim(-3, 3)
        #self.fig_room_cfg.set_tight_layout()
        self.fig_room_cfg.tight_layout()

        # Monitoring zone point cloud
        self.fig_mon_zone = plt.figure()
        ax_mz = self.fig_mon_zone.add_subplot()
        self.fig_mon_zone.subplots_adjust(left=0, right=1, top=1, bottom=0.)
        ax_mz.scatter(x,y)
        ax_mz.set_ylim(0.5, 4)
        ax_mz.set_xlim(-2, 2)
        ax_mz.set_facecolor((1.0, 0, 0,1))
        # self.fig_mon_zone.set_facecolor((0, 1, 0, 1))
        ax_mz.get_xaxis().set_visible(False)
        ax_mz.get_yaxis().set_visible(False)
        self.fig_mon_zone.tight_layout()
        ax_mz.axis('off')
        self.box_monitoring_zone.add_widget(FigureCanvasKivyAgg(plt.figure(self.fig_mon_zone.number)))
    
    def parse_data(self,Tf):

        #getting data from mqtt
        global T
        global idx_mqtt, idx_write, idx_file_refresh
        global file_save, file_time
        global temp
        global mqttData_SAVE, mqttData_SAVEFull
        global heartbeat

        global si, sv, sd, sts, sm
        global cfg_idx
        global config_msg

        
        # ---- Parse Data ---- #
        
        if self.load_full_data[idx_file_refresh][0] != 'Time':
        
            #sen_idx = si.check(self.load_full_data[idx_file_refresh][1])
            try:
                T.append(datetime.datetime.strptime(self.load_full_data[idx_file_refresh][0], '%Y-%m-%dT%H:%M:%S.%fZ'))

                data = base64.b64decode(self.load_full_data[idx_file_refresh][3])
                str_data = str(data[0])
                data_int = [data[0]]
                for i in range(7):
                    str_data = str_data + str(data[i+1])
                    data_int.append(data[i+1])

                # Check if full data packet received
                if self.full_data_flag == True:
                    for i in range(len(data)-8):
                        data_int.append(data[i+8])

                
                    # Parse TLVs
                    sd.update(3, data_int, 5)
                    sts.update(sd,1000)
                    ndns_fns.class_eng.framewise_calculation(sd, 0)
                    ndns_fns.class_eng.classify()

                # Otherwise process occupancy info
                else:
                    pass
                    # sm.update(mqttData)
                    # #print("Sensors: {}. Roots: {}. T: {}".format(sm.sensor_id, sm.root_id, sm.last_time_connected))
                    # mqttOcc = json.loads(data)
                    # mqttTime = json.loads("{\"Time\": \"" + str(T) + "\"}")
                    # mqttDataFinal = {**mqttTime, **mqttData, **mqttOcc}
                    # si.last_t[sen_idx] = T
                    # #mqttData_SAVE.append(mqttOcc)
                    
                    # if ('Number of Occupants' in mqttDataFinal):
                    #     mqttDataTemp = [T.strftime("%Y-%m-%dT%H:%M:%S.%fZ")]
                    #     mqttDataTemp.append(mqttData['addr'])
                    #     si.num_occ[sen_idx] = mqttDataFinal['Number of Occupants']
                    #     mqttDataTemp.append(mqttDataFinal['Number of Occupants'])

                    #     if ('Occupancy Info' in mqttDataFinal):
                    #         mqttOccInfo = mqttDataFinal['Occupancy Info']
                    #         for i in range(min(si.num_occ[sen_idx],2)):
                    #             mqttDataTemp.append(mqttOccInfo[i]['Occupant ID'])
                    #             mqttDataTemp.append(mqttOccInfo[i]['X'])
                    #             mqttDataTemp.append(mqttOccInfo[i]['Y'])
                    #             mqttDataTemp.append(mqttOccInfo[i]['Z'])
                    #         while 1:
                    #             if i < 1:
                    #                 for j in range(4):
                    #                     mqttDataTemp.append('')
                    #                 i += 1
                    #             else:
                    #                 break

                    #         if 'Heatmap energy' in mqttOccInfo[-1]:
                    #             mqttDataTemp.append(mqttOccInfo[-1]['Heatmap energy'])
                    #             mqttDataTemp.append(mqttOccInfo[-1]['Heatmap'])
                    #         else:
                    #             mqttDataTemp.append(0)
                    #             mqttDataTemp.append('')
                    #     else:
                    #         for i in range(8):
                    #             mqttDataTemp.append('')
                    #         mqttDataTemp.append(0)
                    #         mqttDataTemp.append('')

                    #     mqttData_SAVE.append(mqttDataTemp)
                        

                    #     # Update max number of occupants
                    #     if (si.num_occ[sen_idx] > si.max_occ[sen_idx]):
                    #         si.max_occ[sen_idx] = si.num_occ[sen_idx]
                    #     # If there are occupants, what are their locations?
                    #     if (si.num_occ[sen_idx] > 0):
                    #         try:
                    #             occ_info = mqttDataFinal['Occupancy Info']
                    #         except:
                    #             occ_info = mqttDataFinal['Occupancy Info'][0]
                    #         # logging.debug('OCCUPANCY INFO')
                    #         for i in range(len(occ_info)):      # NodeNs FIX KZR: update ESP to create new payload
                    #             temp = occ_info[i]
                    #             oh.update(mqttData['addr'],int(temp['Occupant ID']),temp['X'],temp['Y'])
                    #             # Check if occupant has crossed entryway
                    #             oh.entryway(mqttData['addr'],int(temp['Occupant ID']),ew)
                    #             # logging.debug('Occupant no.: {}. X: {}. Y = {}.'.format(temp['Occupant ID'],temp['X'],temp['Y']))
                    #     # Update time period occupancy data
                    #     if mqttData['addr'] not in ew.id:
                    #         ew.update(mqttData['addr'])
                    #     send_idx_e = ew.id.index(mqttData['addr'])

                    

                    # else:
                    #     si.num_occ[sen_idx] = 0

                if idx_file_refresh + 1 < len(self.load_full_data):
                    self.ids.timestamp_print.text = f"{self.load_full_data[idx_file_refresh][0][0:10]}\n{self.load_full_data[idx_file_refresh][0][12:-6]}"
                    time.sleep(Tf*(datetime.datetime.strptime(self.load_full_data[idx_file_refresh+1][0], '%Y-%m-%dT%H:%M:%S.%fZ') - T[idx_file_refresh]).total_seconds())
                    idx_file_refresh += 1
            except:
                pass
        else:
            T.append("")
            idx_file_refresh += 1
            
                    

    def update(self, dt):
        global sts, UD12, sd

        self.parse_data(1)

        # PLOT: Micro-Doppler spectrum
        #levels = MaxNLocator(nbins=15).tick_values(sd.ud_sig.min(), sd.ud_sig.max())
        levels = MaxNLocator(nbins=64).tick_values(20, 230)
        cmap = plt.get_cmap('cool')
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=False)
        self.box_1.clear_widgets()
        plt.figure(self.fig1.number)
        plt.clf()
        ax1 = self.fig1.add_subplot()

        # Check Zone occupancy
        #print("here Z1")
        self.check_zone_occupancy(sd.track)

        if '01B' in ndns_fns.sv.radar_version:
            cf = ax1.contourf(ud_x, ud_y, sd.ud_sig,
                      levels=levels,
                      cmap=cmap)
            ax1.set_title('Micro-Doppler spectrum')
            ax1.set_xlabel('Doppler')
            ax1.set_ylabel('Time')

        elif '02A' in ndns_fns.sv.radar_version:
        
            if sd.vs.heart_rate_raw[0] != None:
                try:
                    ax1.plot(sd.vs.heart_waveform)
                except:
                    print(sd.vs.heart_waveform)
                ax1.set_title(sd.vs.heart_msg)
            #self.fig1.colorbar(cf, ax=ax1)
        
            ax1.set_ylim((-1,1))

        self.box_1.add_widget(FigureCanvasKivyAgg(self.fig1))

        # PLOT: Point cloud
        self.box_2.clear_widgets()
        plt.figure(self.fig2.number)
        plt.clf()
        #ax2 = self.fig2.add_subplot(projection='3d')
        ax2 = self.fig2.add_subplot()
        if sd.track.num_tracks > 0:
            
            ax2.scatter(sd.pc.X, sd.pc.Y, s=10, c='#FF0000')
            
            ax2.scatter(sd.track.X, sd.track.Y, s=100, marker='x')
            try:
                for i in range(sd.track.num_tracks):
                    sens_idx = oh.sens_idx.index(self.ids.sensor_spinner.text)

                    track_idx = oh.id[sens_idx].index(sd.track.tid[i])
                    ax2.plot(oh.xh[sens_idx][track_idx], oh.yh[sens_idx][track_idx])
            except Exception as e:
                # self.handleError(e)
                print(e)
            
            if -1 in self.line_status:
                ax2.set_facecolor("red")
            elif 1 in self.line_status:
                ax2.set_facecolor("green")
            else:
                ax2.set_facecolor("white")

        else:
            ax2.scatter(sd.pc.X, sd.pc.Y, s=10, c='#000000')

        # point cloud history
        for i in range(1,len(sd.pc_history.X)):
            ax2.scatter(sd.pc_history.X[i], sd.pc_history.Y[i], s=1, c='k', alpha=max(0,(11-i)*0.1))

        #if sd.track.num_tracks > 0:
        #ax2.scatter(sd.track.X, track7.Y, track7.Z, s=100)
        #else:
            #ax2.scatter([],[],[])
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        #ax2.set_zlabel('Z (m)')

        X0 = float(ndns_fns.rcp.ROOM_X_MIN)
        X1 = float(ndns_fns.rcp.ROOM_X_MAX)
        Y0 = float(ndns_fns.rcp.ROOM_Y_MIN)
        Y1 = float(ndns_fns.rcp.ROOM_Y_MAX)

        ax2.set_xlim((X0-1, X1+1))
        ax2.set_ylim((0,Y1+1))
        ax2.add_patch( Rectangle((X0,Y0),
                    X1-X0, Y1-Y0,
                    fc ='none', 
                    ec ='g',
                    lw = 2) )
        plt.title('Point cloud')
        self.box_2.add_widget(FigureCanvasKivyAgg(self.fig2))

        # PLOT: Micro-Doppler parameters or VS
        self.box_3.clear_widgets()
        plt.figure(self.fig3.number)
        plt.clf()
        if sd.ud.dopp.mean != []:
            x = [(sd.ud.dopp.high_freq_env -sd.ud.dopp.mean)*(np.cos(np.pi/50*i)) + sd.ud.dopp.mean for i in range(26)]
            y = [(sd.ud.z.high_freq_env-sd.ud.z.mean)*(np.sin(np.pi/50*i)) + sd.ud.z.mean for i in range(26)]
            plt.plot(x,y)
            x = [(sd.ud.dopp.mean -sd.ud.dopp.low_freq_env)*(np.cos(np.pi/50*i)) + sd.ud.dopp.mean for i in range(25,51)]
            y = [(sd.ud.z.high_freq_env-sd.ud.z.mean)*(np.sin(np.pi/50*i)) + sd.ud.z.mean for i in range(25,51)]
            plt.plot(x,y)
            x = [(sd.ud.dopp.mean -sd.ud.dopp.low_freq_env)*(np.cos(np.pi/50*i)) + sd.ud.dopp.mean for i in range(50,76)]
            y = [(sd.ud.z.mean-sd.ud.z.low_freq_env)*(np.sin(np.pi/50*i)) + sd.ud.z.mean for i in range(50,76)]
            plt.plot(x,y)
            x = [(sd.ud.dopp.high_freq_env -sd.ud.dopp.mean)*(np.cos(np.pi/50*i)) + sd.ud.dopp.mean for i in range(75,101)]
            y = [(sd.ud.z.mean-sd.ud.z.low_freq_env)*(np.sin(np.pi/50*i)) + sd.ud.z.mean for i in range(75,101)]
            plt.plot(x,y)
            plt.title('Micro-Doppler parameters')
            plt.xlabel('Velocity')
            plt.ylabel('Height')
            plt.gca().set_xlim((-4,4))
            plt.gca().set_ylim((-1,2))

        

        self.box_3.add_widget(FigureCanvasKivyAgg(self.fig3))

        ## ~~~~~~~ Update text box ~~~~~~~ ##
        temp_text = ''
        for i in range(min(3, len(ndns_mesh.MESH.status.info_history))):
            temp_text += ndns_mesh.MESH.status.info_history[i] + ' @ ' 
            temp_text += ndns_mesh.MESH.status.info_timestamp_history[i] + '\n'
        self.ids.text_sensor_msg.hint_text = temp_text

        
        if len(sts.frame) == len(sts.num_pnts):            
            # PLOT: Occupancy
            N = min(50,len(sts.num_pnts))
            self.box_4.clear_widgets()
            plt.figure(self.fig4.number)
            plt.clf()
            plt.plot(sts.frame[-N:], sts.num_tracks[-N:], label="Occupancy")
            plt.title('Room occupancy')
            plt.legend(loc="upper left")
            self.box_4.add_widget(FigureCanvasKivyAgg(self.fig4))
            # Format labels
            plt.gca().set_ylim((0,5))
            current_values = plt.gca().get_yticks()
            plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values])
            
            

            # PLOT: Number of points
            self.box_5.clear_widgets()
            plt.figure(self.fig5.number)
            plt.clf()
            plt.plot(sts.frame[-N:], sts.num_pnts[-N:])
            plt.title('Number of points')
            self.box_5.add_widget(FigureCanvasKivyAgg(self.fig5))
   
        

    def update_mon_zone(self, dt):
        global sts, UD12, sd

        self.parse_data(1)

        ## ~~~~~~~ Monitoring zone point cloud ~~~~~~~ ##

        self.box_monitoring_zone.clear_widgets()
        #self.box_2.clear_widgets()
        #plt.figure(self.fig2.number)
        #plt.clf()
        #ax2 = self.fig2.add_subplot(projection='3d')
        ax2 = self.fig2.add_subplot()

        plt.figure(self.fig_mon_zone.number)
        plt.clf()
        #ax2 = self.fig2.add_subplot(projection='3d')
        ax_mz = self.fig_mon_zone.add_subplot()
        ax_mz.set_facecolor((1, 1, 1,0))
        self.fig_mon_zone.set_facecolor((1, 1, 1, 0))
        if -1 in self.line_status:
            ax_mz.set_facecolor((1, 0, 0, 0.5))
            if self.zone_msg_sent_status != 'exclusion':
                json_msg = {'alert':'exclusion'}
                json_payload = [json_msg]
                ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP, ndns_fns.cp.SENSOR_PORT, 60, "monitor_msg", json_payload)
                self.zone_msg_sent_status = 'exclusion'
        elif 1 in self.line_status:
            ax_mz.set_facecolor((0, 1, 0, 0.5))
            if self.zone_msg_sent_status != 'safe':
                json_msg = {'alert':'safe'}
                json_payload = [json_msg]
                ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP, ndns_fns.cp.SENSOR_PORT, 60, "monitor_msg", json_payload)
                self.zone_msg_sent_status = 'safe'
        else:
            ax_mz.set_facecolor((1.0, 1, 1,0))
            if self.zone_msg_sent_status != 'none':
                json_msg = {'alert':'none'}
                json_payload = [json_msg]
                ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP, ndns_fns.cp.SENSOR_PORT, 60, "monitor_msg", json_payload)
                self.zone_msg_sent_status = 'none'
        ax_mz.set_xlim((-2, 2))
        ax_mz.set_ylim((0.5,4))
        ax_mz.get_xaxis().set_visible(False)
        ax_mz.get_yaxis().set_visible(False)
        
        # point cloud history
        for i in range(1,len(sd.pc_history.X)):
            ax_mz.scatter(sd.pc_history.X[i], sd.pc_history.Y[i], s=40, c='w', alpha=max(0,(11-i)*0.1))

        if sd.track.num_tracks > 0:
            ax_mz.scatter(sd.pc.X, sd.pc.Y, s=40, color=[1, 1, 1, 1])
            ax_mz.scatter(sd.track.X, sd.track.Y, s=1000, marker='P', color=[1, 0.5, 0, 1])
        else:
            ax_mz.scatter(sd.pc.X, sd.pc.Y, s=40, color=[1, 1, 1, 1])  

        try:
            for i in range(sd.track.num_tracks):
                sens_idx = oh.sens_idx.index(self.ids.sensor_spinner.text)

                track_idx = oh.id[sens_idx].index(sd.track.tid[i])
                ax_mz.plot(oh.xh[sens_idx][track_idx], oh.yh[sens_idx][track_idx], linewidth=3, color=[1, 0.5, 0, 1])
        except Exception as e:
            # self.handleError(e)
            print(e)

        self.box_monitoring_zone.add_widget(FigureCanvasKivyAgg(self.fig_mon_zone))

    def mqtt_connect(self):
        global client, sm, T_jwt_refresh

        sensor_id = self.ids.sensor_spinner.text
        root_id = self.ids.root_spinner.text
        if self.ids.ip_add.text == '':
            ndns_fns.cp.SENSOR_IP = self.ids.ip_add.hint_text
        else: 
            ndns_fns.cp.SENSOR_IP = self.ids.ip_add.text
        print("sensor id = {}. root id = {}. ip = {}".format(sensor_id, root_id, ndns_fns.cp.SENSOR_IP))
        print(f"load file:{self.load_file}")

        LED_Indicator.update(LED_Indicator)

    def data_restart(self):
        global idx_file_refresh

        self.initialise_plots()

    def btn_config(self):
        print('Config')
        pass

    def btn_stop_full_data(self):
        global cp

        ndns_fns.sendCMDtoSensor.full_data_off(ndns_fns.rcp,ndns_fns.cp)
        self.ids.led_connect.color = [1, 0.75, 0, 1]


    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        content.initialise()
        self._popup = Popup(title="Loading file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_save(self):
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        content.initialise()
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        self.load_file = os.path.join(path, filename)
        if self.load_file[-8:].lower() == "full.csv":
            self.load_file = f"{self.load_file[:-9]}.csv"

        # Check if full data file exists
        self.full_data_flag = os.path.exists(f"{self.load_file[:-4]}_FULL.csv")

        self.load_data = []
        self.load_full_data = []

        try:
            with open(self.load_file) as stream:
                reader = csv.reader(stream)
                for row in reader:
                    self.load_data.append(row)
            print(self.load_data[0:2])
            
            if self.full_data_flag == True:
                print(f"{self.load_file[:-4]}_FULL.csv")
                with open(f"{self.load_file[:-4]}_FULL.csv") as stream:
                    reader = csv.reader(stream)
                    for row in reader:
                        self.load_full_data.append(row)

            # Update history.cfg
            history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
            history_data = open(history_file,"r")
            history_settings = json.loads(history_data.read())
            history_data.close()
            history_settings["Save file"] = filename
            history_settings["Save folder"] = path
            file_save = pjoin(history_settings["Save folder"], 
                            history_settings["Save file"])
            history_data = open(history_file,"w")
            json.dump(history_settings, history_data)
            history_data.close()
        except Exception as e:
            print(f"Exception {e}")

        try:
            self.dismiss_popup()
        except:
            pass

        # What to do if there is no full data.
        if (self.full_data_flag == False):
            # Create the popup content
            content = Label(text=f"No full data file!!\n\nPlease load a different file to visualise the point cloud.", halign="center", valign="center")
            content.bind(width=lambda *x: content.setter('text_size')(content, (content.width, None)))

            # Create the popup
            popup = Popup(title='WARNING: NO FULL DATA FILE', content=content, auto_dismiss=True, size_hint=(0.5,0.5))

            # Open the popup
            popup.open()
        elif (len(self.load_full_data) <= 1):
            # Create the popup content
            content = Label(text=f"Full data file is empty!\n\nPlease load a different file to visualise the point cloud.", halign="center", valign="center")
            content.bind(width=lambda *x: content.setter('text_size')(content, (content.width, None)))

            # Create the popup
            popup = Popup(title='WARNING: EMPTY FULL DATA FILE', content=content, auto_dismiss=True, size_hint=(0.5,0.5))

            # Open the popup
            popup.open()
        else:
            LED_Indicator.update(LED_Indicator)
            self.led_1.update()

    def save(self, path, filename):
        print("saving here")
        global file_save
        with open(os.path.join(path, filename), 'w') as stream:
            stream.write("testing 1..2..3..")

        # Load history
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()
        history_settings["Save file"] = filename
        history_settings["Save folder"] = path
        file_save = pjoin(history_settings["Save folder"], 
                          history_settings["Save file"])
        history_data = open(history_file,"w")
        json.dump(history_settings, history_data)
        history_data.close()

        self.dismiss_popup()

    def load_switch_callback(self, switchObject, switchValue):
        if switchValue is False:
            self.ids.load_button.disabled = True
            ndns_fns.cp.WRITE_FLAG = 0
        else:
            self.ids.load_button.disabled = False
            ndns_fns.cp.WRITE_FLAG = 1
        history_file = (Path(pjoin(os.getcwd(), 'history.cfg')))
        with open(history_file, "r+") as f:
            history_settings = json.load(f)
            history_settings["Save state"] = str(switchValue)
            f.seek(0)
            json.dump(history_settings,f)
            #f.write(output)
            f.truncate()


    def monitor_pc_switch_callback(self, switchObject, switchValue):
        if switchValue is False:
            if self.clock != []:
                self.clock.cancel()
                self.clock = []
        else:
            if self.full_data_flag == True:
                if self.clock == []:
                    self.clock = Clock.schedule_interval(self.update_mon_zone, 0.005)
            else:
                # Create the popup content
                content = Label(text=f"File not loaded!!\n\nPlease load a file before switching on the point cloud.", halign="center", valign="center")
                content.bind(width=lambda *x: content.setter('text_size')(content, (content.width, None)))

                # Create the popup
                popup = Popup(title='WARNING: NO DATA FILE LOADED', content=content, auto_dismiss=True, size_hint=(0.5,0.5))

                # Open the popup
                popup.open()

                # Switch off
                switchObject.active = False
        

    def alarm_sounds_switch_callback(self, switchObject, switchValue):
        if switchValue is False:
            json_msg = {'sound':'off'}
            json_payload = [json_msg]
            print('sound off')
            ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP, ndns_fns.cp.SENSOR_PORT, 60, "monitor_msg", json_payload)
        else:
            json_msg = {'sound':'on'}
            json_payload = [json_msg]
            print('sound on')
            ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP, ndns_fns.cp.SENSOR_PORT, 60, "monitor_msg", json_payload)

    # Select root and sensor
    def root_spinner_callback(self):
        global sm
        if len(sm.root_id) > 0:
            self.ids.sensor_spinner.values = [sm.sensor_id[index] for index, element in enumerate(sm.root_id) if element == self.ids.root_spinner.text]
            if len(self.ids.sensor_spinner.values) == 0:
                self.ids.sensor_spinner.text = "No detected sensors" # This shouldn't happen because we'll always have the root. But just in case...
            else:
                self.ids.sensor_spinner.text = self.ids.sensor_spinner.values[0]
            
                ndns_fns.rcp.SENSOR_TARGET = self.ids.sensor_spinner.text
                ndns_fns.rcp.SENSOR_ROOT = self.ids.root_spinner.text

    def sensor_spinner_callback(self):
        ndns_fns.rcp.SENSOR_TARGET = self.ids.sensor_spinner.text

    def btn_read_current_config(self):
        print("Room BEFORE: X: ({},{}). Y: ({},{})".format(ndns_fns.rcp.ROOM_X_MAX,ndns_fns.rcp.ROOM_X_MIN,ndns_fns.rcp.ROOM_Y_MAX,ndns_fns.rcp.ROOM_Y_MIN))
        print(ndns_fns.cp.SENSOR_IP, cfg_idx)
        
        ndns_fns.sendCMDtoSensor.request_config(ndns_fns.rcp,ndns_fns.cp)
        time.sleep(0.2)
        while ndns_fns.rcp.cfg_idx != 0:
            time.sleep(0.01)

        self.ids.room_x_min.hint_text = ndns_fns.rcp.ROOM_X_MIN
        self.ids.room_x_max.hint_text = ndns_fns.rcp.ROOM_X_MAX
        self.ids.room_y_min.hint_text = ndns_fns.rcp.ROOM_Y_MIN
        self.ids.room_y_max.hint_text = ndns_fns.rcp.ROOM_Y_MAX
        
        print("Room AFTER: X: ({},{}). Y: ({},{})".format(ndns_fns.rcp.ROOM_X_MAX,ndns_fns.rcp.ROOM_X_MIN,ndns_fns.rcp.ROOM_Y_MAX,ndns_fns.rcp.ROOM_Y_MIN))


    def btn_send_config_update(self):
        # ADD sensorPosition
        global ew
        ew = ndns_fns.entry_ways()
        # Update room dimensions
        # print(f"3. rcp.config_radar: {ndns_fns.rcp.config_radar}")

        # print(f"4. rcp.config_radar: {ndns_fns.rcp.config_radar}")
        print("Room BEFORE: X: ({},{}). Y: ({},{})".format(ndns_fns.rcp.ROOM_X_MAX,ndns_fns.rcp.ROOM_X_MIN,ndns_fns.rcp.ROOM_Y_MAX,ndns_fns.rcp.ROOM_Y_MIN))
        ndns_fns.rcp.RADAR_SEND_FLAG = 1
        if self.ids.room_x_max.text == '':
            ndns_fns.rcp.ROOM_X_MAX = self.ids.room_x_max.hint_text
        else:
            ndns_fns.rcp.ROOM_X_MAX = self.ids.room_x_max.text
        if self.ids.room_x_min.text == '':
            ndns_fns.rcp.ROOM_X_MIN = self.ids.room_x_min.hint_text
        else:
            ndns_fns.rcp.ROOM_X_MIN = self.ids.room_x_min.text
        if self.ids.room_y_max.text == '':
            ndns_fns.rcp.ROOM_Y_MAX = self.ids.room_y_max.hint_text
        else:
            ndns_fns.rcp.ROOM_Y_MAX = self.ids.room_y_max.text
        if self.ids.room_y_min.text == '':
            ndns_fns.rcp.ROOM_Y_MIN = self.ids.room_y_min.hint_text
        else:
            ndns_fns.rcp.ROOM_Y_MIN = self.ids.room_y_min.text
        ndns_fns.rcp.MONITOR_X = ndns_fns.rcp.ROOM_X_MIN + "," + ndns_fns.rcp.ROOM_X_MAX
        ndns_fns.rcp.MONITOR_Y = ndns_fns.rcp.ROOM_Y_MIN + "," + ndns_fns.rcp.ROOM_Y_MAX

        # Update history.cfg file
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()
        history_settings["Room"] = {}
        history_settings["Room"]["X"] = [float(ndns_fns.rcp.ROOM_X_MIN), float(ndns_fns.rcp.ROOM_X_MAX)]
        history_settings["Room"]["Y"] = [float(ndns_fns.rcp.ROOM_Y_MIN), float(ndns_fns.rcp.ROOM_Y_MAX)]
        history_data = open(history_file,"w")
        json.dump(history_settings, history_data)
        history_data.close()
        print("Room AFTER: X: ({},{}). Y: ({},{})".format(ndns_fns.rcp.ROOM_X_MAX,ndns_fns.rcp.ROOM_X_MIN,ndns_fns.rcp.ROOM_Y_MAX,ndns_fns.rcp.ROOM_Y_MIN))
        


    # ~~~~~~~ DRAWING SCREEN ~~~~~~~~~~~~ #
    def print_zones_to_history(self):
        # Update history.cfg file
        history_file = Path(pjoin(os.getcwd(), 'history.cfg'))
        history_data = open(history_file,"r")
        history_settings = json.loads(history_data.read())
        history_data.close()

        history_settings["Zones"] = []
        for i,line in enumerate(self.line_xy):
            temp = {}
            if self.line_draw_type[i] == 'r':
                temp["Type"] = "rectangle"
                temp["X"] = [np.round(line.pos[0],2).astype(dtype=float), np.round(line.size[0],2).astype(dtype=float)]
                temp["Y"] = [np.round(line.pos[1],2).astype(dtype=float), np.round(line.size[1],2).astype(dtype=float)]
            else:
                if (all(x == self.line_draw_type[i][0] for x in self.line_draw_type[i])):
                    if self.line_draw_type[i][0] == 'l':
                        temp["Type"] = "line"
                    elif self.line_draw_type[i][0] == 'b':
                        temp["Type"] = "bezier"
                    else:
                        print(f"No correct type {self.line_draw_type[i][0]}")
                else:
                    temp["Type"] = "mixed"
                    temp["draw_type"] = []
                    for draw_type in self.line_draw_type[i]:
                        temp["draw_type"].append(draw_type)
                
                temp["X"] = []
                temp["Y"] = []
                for j, point_xy in enumerate(line.points):
                    if j % 2 == 0:
                        temp["X"].append(np.round(point_xy,2).astype(dtype=float))
                    else:
                        temp["Y"].append(np.round(point_xy,2).astype(dtype=float))
            temp["Zone"] = self.line_zone_type[i].lower()
            #temp["draw_type"] = self.line_draw_type
            history_settings["Zones"].append(temp)
        history_data = open(history_file,"w")
        json.dump(history_settings, history_data)
        history_data.close()

    def draw_rectangle(self, instance):
        self._drawing_state = 0
        self._drawing_init = 1
        print(f"Drawing state: 0 (rectangle) {self._drawing_state} {self._drawing_init}")

    def draw_line(self, instance):
        print(f"Drawing state: 1 (line)")
        if self._drawing_state == 0:
            self._drawing_init = 1
        self._drawing_state = 1
        

    def draw_arc(self, instance):
        print(f"Drawing state: 2 (arc)")
        if self._drawing_state == 0:
            self._drawing_init = 1
        self._drawing_state = 2

    def draw_free(self, instance):
        print(f"Drawing state: 3 (free)")
        if self._drawing_state == 0:
            self._drawing_init = 1
        self._drawing_state = 3

    def undo_last(self, instance):        
        if len(self.line) > 0:
            item = self.line.pop(-1)
            self.canvas.remove(item)
            self.line_xy.pop(-1)
            self.line_status.pop(-1)
            self.line_zone_type.pop(-1)
            self._drawing_init = 1
            print(f"Remove last zone")

            # Update history.cfg file
            self.print_zones_to_history()

        else:
            print(f"Nothing left to delete")

    def zone_switch(self, instance):
        if self.zone_type == "safe":
            self.zone_type = "exclusion"
            self.ids.zone_type_button.text = "EXCLUSION zone"
            self.zone_color = [1,0,0,1]
            self.ids.zone_type_button.background_color = self.zone_color
        else:
            self.zone_type = "safe"
            self.ids.zone_type_button.text = "SAFE zone"
            self.zone_color = [0,1,0,1]
            self.ids.zone_type_button.background_color = self.zone_color

    def close_shape(self, instance): 
        if self._drawing_state == 0:
            print("Rectangle is already a closed area")
        else:
            self.line[-1].points += (self.line[-1].points[0], self.line[-1].points[1])
            self.line_xy[-1].points += (self.line_xy[-1].points[0], self.line_xy[-1].points[1])

            # self.line_xy.append()
            # num_pts = int(len(self.line[-1].points))
            # for i in range(num_pts/2):
            #     screen_xy = [self.line[-1].points[2*i],self.line[-1].points[2*i+1]]
            #     temp_xy = self.transform_screen_to_xy(screen_xy,self.boundary_xy, self.border_xy)
            #     self.line_xy[-1].points.append(temp_xy[0])
            #     self.line_xy[-1].points.append(temp_xy[1])
            # print(f"Line: {self.line_xy[-1].points}")
            self._drawing_init = 1
            print("Shape closed") 

            # Update history.cfg file
            self.print_zones_to_history()

    def open_monitor_zone(self, *args):
        with self.canvas:
            for i in range(len(self.canvas.children)):
                try:
                    self.canvas.children[i].rgba[3] = 0
                except:
                    pass
        if self.clock != []:
            self.clock.cancel()
            self.clock = []

    def close_monitor_zone(self, *args):
        with self.canvas:
            for i in range(len(self.canvas.children)):
                try:
                    self.canvas.children[i].rgba[3] = 1
                except:
                    pass
        if self.clock != []:
            try:
                self.clock.cancel()
                self.clock = []
            except Exception as e: print(e)
        # if self.clock == []:
        #     self.clock = Clock.schedule_interval(self.update, 0.25)

    def open_sensor_data_plots(self, *args):
        with self.canvas:
            for i in range(len(self.canvas.children)):
                try:
                    self.canvas.children[i].rgba[3] = 0
                except:
                    pass
        if self.clock == []:
            self.clock = Clock.schedule_interval(self.update, 0.005)
        

    def on_window_resize(self, window, width, height):
        self._window_size = Window.size
        self._area_pos = [0.25*self._window_size[0] + self.ids.drawing_screen.pos[0], 0.1*self._window_size[1]]
        self._area_size = [0.5*self._window_size[0], 0.8*self._window_size[1]]
        # self._area_pos = self._area_pos
        # self._area_size = self._area_size


        for i, line_xy in enumerate(self.line_xy):
            # Zone Colour
            # if self.line_zone_type == "safe":
            #     self.zone_color = [0,1,0,0]
            # else:
            #     self.zone_color = [1,0,0,0]

            # Resize zones
            if self.line_draw_type[i] == 'r':
                screen_xy = self.transform_xy_to_screen(line_xy.pos, self.boundary_xy, self.border_xy)
                screen_xy1 = [0,0]
                screen_xy1[0] = line_xy.pos[0] + line_xy.size[0]
                screen_xy1[1] = line_xy.pos[1] + line_xy.size[1]
                screen_xy1 = self.transform_xy_to_screen(screen_xy1, self.boundary_xy, self.border_xy)
                screen_xy1[0] -= screen_xy[0]
                screen_xy1[1] -= screen_xy[1]
                self.line[i].pos = screen_xy#kv_Rectangle(pos=(screen_xy[0], screen_xy[1]), size=(screen_xy1), width=2, rgba=self.zone_color)
                self.line[i].size = screen_xy1
            else:
                point_xy = [0,0]
                j = 0
                # self.line[i] = []
                

                for j,point in enumerate(line_xy.points):
                    if j % 2 == 0:
                        point_xy[0] = point
                    else:
                        point_xy[1] = point
                        screen_xy = self.transform_xy_to_screen(point_xy, self.boundary_xy, self.border_xy)
                        # if j == 1:
                        #     if self.line_draw_type[i][0] == 'b':
                        #         self.line.append(Bezier(points=[screen_xy[0], screen_xy[1]], width=20))
                        #     else:
                        #         self.line.append(Line(points=[screen_xy[0], screen_xy[1]], width=2))
                        # else:
                        #     self.line[-1].points += (screen_xy[0], screen_xy[1])
                        self.line[i].points[j-1] = screen_xy[0]
                        self.line[i].points[j] = screen_xy[1]

            

        
        

    def on_mouse_pos(self, *args):
        if self.ids.monitor_zones_config.collapse == True:
            return
        else:
            self._window_size = Window.size
            X = [float(self.ids.room_x_min.hint_text), float(self.ids.room_x_max.hint_text)]
            Y = [float(self.ids.room_y_min.hint_text), float(self.ids.room_y_max.hint_text)]
            if self.ids.room_x_min.text != '':
                X[0] = float(self.ids.room_x_min.text)
            if self.ids.room_x_max.text != '':
                X[1] = float(self.ids.room_x_max.text)
            if self.ids.room_y_min.text != '':
                Y[0] = float(self.ids.room_y_min.text)
            if self.ids.room_y_max.text != '':
                Y[1] = float(self.ids.room_y_max.text)
            pos = args[1]
    
            self.tooltip.pos = [pos[0] - self._window_size[0]/2 - 0*self.ids.drawing_screen.pos[0], pos[1] - self._window_size[1]/2]
            temp_x = X[0] + (X[1] - X[0])*(pos[0] - 0.25*self._window_size[0] - self.ids.drawing_screen.pos[0])/(0.5*self._window_size[0])
            temp_y = Y[0] + (Y[1] - Y[0])*(pos[1] - 0.1*self._window_size[1])/(0.8*self._window_size[1])
            if (temp_x >= X[0]) and (temp_x <= X[1]) and (temp_y >= Y[0]) and (temp_y <= Y[1]):
                self.tooltip.text = str(f"X:{temp_x:.1f}, Y:{temp_y:.1f}\nX:{pos[0]:.1f}, Y:{pos[1]:.1f}")
            else:
                self.tooltip.text = ""

    def close_tooltip(self, *args):
        Window.remove_widget(self.tooltip)

    def display_tooltip(self, *args): 
        colored(self.tooltip.text, 'red')

    def on_touch_down(self, _touch):
        try:
            if self.ids.monitor_zones_config.collapse == True:
                pass
            else:
                with self.canvas:
                    self._area_pos[0] = 0.25*self._window_size[0] + self.ids.drawing_screen.pos[0]
                    Color(self.zone_color[0],self.zone_color[1],self.zone_color[2],self.zone_color[3])
                    if (_touch.x >= self._area_pos[0]) & (_touch.x <= self._area_pos[0]+self._area_size[0]):
                        if (_touch.y >= self._area_pos[1]) & (_touch.y <= self._area_pos[1]+self._area_size[1]):
                            if self._drawing_state == 0:
                                if self._drawing_init == 1:
                                    self.line.append(kv_Rectangle(pos=(_touch.x, _touch.y), size=(100, 100), width=2, rgba=self.zone_color))

                                    s_x = self.line[-1].size[0]*(self.boundary_xy[1]-self.boundary_xy[0])/(self.border_xy[1])/self._window_size[0] 
                                    s_y = self.line[-1].size[1]*(self.boundary_xy[3]-self.boundary_xy[2])/(self.border_xy[3])/self._window_size[1] 
                                    p_xy = self.transform_screen_to_xy(self.line[-1].pos, self.boundary_xy, self.border_xy)
                                    self.line_xy.append(kv_Rectangle(pos=(p_xy[0], p_xy[1]), size=(1, 1), width=2, rgba=self.zone_color))
                                    self.line_status.append(0)
                                    self.line_zone_type.append(self.zone_type)
                                    self._drawing_init = 0
                                else:
                                    temp_x = _touch.x - self.line[-1].pos[0]
                                    temp_y = _touch.y - self.line[-1].pos[1]
                                    self.line[-1].size = (temp_x, temp_y)

                                    s_x = temp_x*(self.boundary_xy[1]-self.boundary_xy[0])/(self.border_xy[1])/self._window_size[0] 
                                    s_y = temp_y*(self.boundary_xy[3]-self.boundary_xy[2])/(self.border_xy[3])/self._window_size[1] 
                                    #p_xy = self.transform_screen_to_xy(self.line[-1].pos, self.boundary_xy, self.border_xy)
                                    self.line_xy[-1].size = (s_x, s_y)
                                    #self.line_xy.append(kv_Rectangle(pos=(p_xy[0], p_xy[1]), size=(s_x, s_y), width=2, rgba=self.zone_color))
                                    self.line_draw_type.append('r')
                                    self.print_zones_to_history()

                            elif self._drawing_state == 1:
                                if self._drawing_init == 1:
                                    self.line.append(Line(points=[_touch.x, _touch.y], width=2))
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy.append(Line(points=xy, width=2))
                                    self.line_status.append(0)
                                    self.line_zone_type.append(self.zone_type)
                                    self._touch = _touch
                                    self._drawing_init = 0
                                    self.line_draw_type.append(['l'])
                                else:
                                    self.line[-1].points += (_touch.x, _touch.y)
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy[-1].points += (xy[0], xy[1])
                                    self.line_draw_type[-1].append('l')

                            elif self._drawing_state == 2:
                                if self._drawing_init == 1:
                                    self.line.append(Bezier(points=[_touch.x, _touch.y], width=20))
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy.append(Bezier(points=xy, width=20))
                                    self.line_status.append(0)
                                    self.line_zone_type.append(self.zone_type)
                                    self._touch = _touch
                                    self._drawing_init = 0
                                    self.line_draw_type.append(['b'])
                                else:
                                    self.line[-1].points += (_touch.x, _touch.y)
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy[-1].points += (xy[0], xy[1])
                                    self.line_draw_type[-1].append('b')


                            else:

                                if self._drawing_init == 1:
                                    self.line.append(Line(points=[_touch.x, _touch.y], width=2))
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy.append(Line(points=xy, width=2))
                                    self.line_status.append(0)
                                    self.line_zone_type.append(self.zone_type)
                                    self._drawing_init = 0
                                    self.line_draw_type.append(['l'])
                                else:
                                    self.line[-1].points += (_touch.x, _touch.y)
                                    xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                    self.line_xy[-1].points += (xy[0], xy[1])
                                    self.line_draw_type[-1].append('l')
                    
                    
        except Exception as e: print(e)
        
        
        
                            
        
        return super(NodeNsUpdateProcedure, self).on_touch_down(_touch)

    def on_touch_move(self, _touch):
        if self.ids.monitor_zones_config.collapse == True:
            pass
        else:
            if (_touch.x >= self._area_pos[0]) & (_touch.x <= self._area_pos[0]+self._area_size[0]):
                    if (_touch.y >= self._area_pos[1]) & (_touch.y <= self._area_pos[1]+self._area_size[1]):
                        if self._drawing_init == 0:
                            if self._drawing_state == 0:    # rectangle
                                temp_x = _touch.x - self.line[-1].pos[0]
                                temp_y = _touch.y - self.line[-1].pos[1]
                                self.line[-1].size = (temp_x, temp_y)

                                s_x = temp_x*(self.boundary_xy[1]-self.boundary_xy[0])/(self.border_xy[1])/self._window_size[0] 
                                s_y = temp_y*(self.boundary_xy[3]-self.boundary_xy[2])/(self.border_xy[3])/self._window_size[1] 
                                self.line_xy[-1].size = (s_x, s_y)
                                self.line_draw_type.append('r')
                                self.print_zones_to_history()

                            elif self._drawing_state == 1:  # line
                                self.line[-1].points[-1] = (_touch.x, _touch.y)
                                xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                self.line_xy[-1].points[-1] = (xy[0], xy[1])
                                self.line_draw_type.append('l')
                            elif self._drawing_state == 2:  # arc
                                self.line[-1].points += (_touch.x, _touch.y)
                                xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                self.line_xy[-1].points += (xy[0], xy[1])
                                self.line_draw_type.append('b')
                            elif self._drawing_state == 3:  # free
                                self.line[-1].points += (_touch.x, _touch.y)
                                xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                self.line_xy[-1].points += (xy[0], xy[1])
                                self.line_draw_type[-1].append('l')
                            else:
                                self.line[-1].points += (_touch.x, _touch.y)
                                xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                self.line_xy[-1].points += (xy[0], xy[1])
                                self.line_draw_type[-1].append('l')
                        else:
                            if self._drawing_state == 3:
                                self.line.append(Line(points=[_touch.x, _touch.y], width=2))
                                xy = self.transform_screen_to_xy([_touch.x, _touch.y], self.boundary_xy, self.border_xy)
                                self.line_xy.append(Line(points=xy, width=2))
                                self.line_status.append(0)
                                self.line_zone_type.append(self.zone_type)
                                self._drawing_init = 0

        return super(NodeNsUpdateProcedure, self).on_touch_down(_touch)
    
    def check_zone_occupancy(self, track):
        BORDER_VIEW_X = [0.25,0.5]
        BORDER_VIEW_Y = [0.1, 0.8]

        X = [float(self.ids.room_x_min.hint_text), float(self.ids.room_x_max.hint_text)]
        Y = [float(self.ids.room_y_min.hint_text), float(self.ids.room_y_max.hint_text)]
        if self.ids.room_x_min.text != '':
            X[0] = float(self.ids.room_x_min.text)
        if self.ids.room_x_max.text != '':
            X[1] = float(self.ids.room_x_max.text)
        if self.ids.room_y_min.text != '':
            Y[0] = float(self.ids.room_y_min.text)
        if self.ids.room_y_max.text != '':
            Y[1] = float(self.ids.room_y_max.text)

        num_occ = np.zeros(len(self.line))

        for j in range(len(track.X)):
            temp_rand_x = (track.X[j]-X[0])*(BORDER_VIEW_X[1]*self._window_size[0])/(X[1]-X[0]) + (BORDER_VIEW_X[0]*self._window_size[0] + self.ids.drawing_screen.pos[0])
            temp_rand_y = (track.Y[j]-Y[0])*(BORDER_VIEW_Y[1]*self._window_size[1])/(Y[1]-Y[0]) + (BORDER_VIEW_Y[0]*self._window_size[1])

            for idx,line in enumerate(self.line):
                num_intercepts = 0
                num_pts = len(line.points)/2
                
                if num_pts > 1:
                    for i in range(int(num_pts)-1):
                        # To check if a point is within a closed area, draw a line from the point to infinity. It should intercept boundaries N times where N is odd.
                        # Select the point at yp = inf + x0 (x0 is the x coord of the point)
                        temp_x1 = line.points[2*i]-temp_rand_x
                        temp_x2 = line.points[2*(i+1)]-temp_rand_x
                        temp_y1 = line.points[2*i+1] - temp_rand_y
                        temp_y2 = line.points[2*(i+1)+1] - temp_rand_y
                        if temp_x1/(temp_x2+np.finfo(float).eps) < 0: # One point should be x<0 and the other x >0
                            temp_y_intercept = (temp_y1*temp_x2 - temp_y2*temp_x1)/(temp_x2-temp_x1)
                            if temp_y_intercept > 0:
                                num_intercepts += 1
                    
                    if (num_intercepts/2 == round(num_intercepts/2)):
                        # print(f"Track: {track.X[j],track.Y[j]} is outside a boundary.")
                        pass
                        
                    else:
                        # print(f"OCCUPANT! Track: {track.X[j],track.Y[j]} is inside a boundary.")
                        num_occ[idx] += 1

        for idx in range(len(self.line)):
            if num_occ[idx] > 0:
                print(f"Occupant in ZONE {idx}. type: {self.line_zone_type[idx]}")
                if self.line_zone_type[idx] == "safe":
                    self.line_status[idx] = 1
                elif self.line_zone_type[idx] == "exclusion":
                    self.line_status[idx] = -1
                else:
                    print(f"Unrecognised zone type: {self.line_zone_type[idx]}")
            else:
                self.line_status[idx] = 0

    def transform_screen_to_xy(self,screen_xy,boundary_xy, border_xy):
        #x = (screen_xy[0] - border_xy[0]*self._window_size[0] - self.ids.drawing_screen.pos[0])*(boundary_xy[1]-boundary_xy[0])/(border_xy[1]*self._window_size[0]) + boundary_xy[0]
        x = (screen_xy[0] - border_xy[0]*self._window_size[0] - self.X_OFFSET)*(boundary_xy[1]-boundary_xy[0])/(border_xy[1]*self._window_size[0]) + boundary_xy[0]
        y = (screen_xy[1] - border_xy[2]*self._window_size[1])*(boundary_xy[3]-boundary_xy[2])/(border_xy[3]*self._window_size[1]) + boundary_xy[2]

        xy = [x,y]
        return xy
    
    def transform_xy_to_screen(self,xy,boundary_xy, border_xy):
        #screen_x = (xy[0] - boundary_xy[0])*(border_xy[1]*self._window_size[0])/(boundary_xy[1]-boundary_xy[0]) + border_xy[0]*self._window_size[0] + self.ids.drawing_screen.pos[0]
        screen_x = (xy[0] - boundary_xy[0])*(border_xy[1]*self._window_size[0])/(boundary_xy[1]-boundary_xy[0]) + border_xy[0]*self._window_size[0] + self.X_OFFSET
        screen_y = (xy[1] - boundary_xy[2])*(border_xy[3]*self._window_size[1])/(boundary_xy[3]-boundary_xy[2]) + border_xy[2]*self._window_size[1]

        screen_xy = [screen_x,screen_y]
        return screen_xy

class NodeNsApp(App):
    _area_size = ListProperty()
    _area_pos = ListProperty()
    _window_size = ListProperty()
    tooltip = Tooltip(text='Hello world')
    _refresh_rate = 0.25

    def build(self):
        self._window_size = Window.size
        #self._area_pos = [0.25*self._window_size[0], 0.1*self._window_size[1]]
        #self._area_size = [0.5*self._window_size[0], 0.8*self._window_size[1]]

        Window.bind(on_resize=self.on_window_resize)

        nodens_updates = NodeNsUpdateProcedure()
        nodens_updates.initialise()

        #save_dialog = SaveDialog()
        #save_dialog.initialise()

        if nodens_updates.ids.sensor_data_plots.collapse == False:
            print("here A")
            #Clock.schedule_interval(nodens_updates.update, self._refresh_rate)
        return nodens_updates
    
    def on_window_resize(self, window, width, height):
        self._window_size = Window.size
        print(f"Window: {self._window_size}")
        self._area_pos = [0.25*self._window_size[0], 0.1*self._window_size[1]]
        self._area_size = [0.5*self._window_size[0], 0.8*self._window_size[1]]
        self._area_pos = self._area_pos
        self._area_size = self._area_size

    # On subscribe callback
def on_subscribe(unused_client, unused_userdata, mid, granted_qos):
    print('MESH: on_subscribe: mid {}, qos {}'.format(mid, granted_qos))

def on_connect(client, userdata, flags, rc):
    print('MESH: on_connect: {} userdata: {}. flags: {}.'.format(mqtt.connack_string(rc), userdata, flags))

def on_disconnect(client, userdata, rc):
    print('MESH: on_disconnect: {} userdata: {}.'.format(mqtt.connack_string(rc), userdata))

def on_unsubscribe(client, userdata, mid):
    print('MESH: on_unsubscribe: mid {}. userdata: {}.'.format(mid, userdata))

if __name__ == '__main__':
    NodeNsApp().run()