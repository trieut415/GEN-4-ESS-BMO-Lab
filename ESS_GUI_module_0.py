## tkinter used for widgets that make up GUI framework
from tkinter import *
import numpy as np #https://scipy-lectures.org/intro/numpy/operations.html
from tkinter import messagebox
import threading
import tkinter.font as tkFont
import random
import logging

#import all dependancies
from settings import Settings as _Settings
from ESS_functions import *
from keyboard import *
from Calibration_window import calibration_window
from help_window import help_window_pop

#from settings_window import settings_popup_window
import settings_window

# create new files and folders
import os

#used for serial comm with arduino
import serial
from time import sleep
import time
 
#saving data to csv
import pandas as pd
import csv

### matplotlib used for plotting data to a canvas
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
import matplotlib.pyplot as plt


################ global variables ###########################
spec_folder_path = '/home/pho512/Desktop/Spectrometer'
spec_folder_settings = '/home/pho512/Desktop/Spectrometer/settings'
settings_file = '/home/pho512/Desktop/Spectrometer/settings/settings.csv'
acquire_file = '/home/pho512/Desktop/Spectrometer/settings/acquire_file.csv'


####################################################################


# create folder to hold all settings and data
if not os.path.exists(spec_folder_path):
        os.makedirs(spec_folder_path)
                
if not os.path.exists(spec_folder_settings):
        os.makedirs(spec_folder_settings)
# create acquire pseudo file if not already within spectrometer folder

try:
    #acquire file holds a temporary data array
    open_acquire_file = open(acquire_file, 'x')
except:
    open_acquire_file = open(acquire_file, 'a')
# open up a serial to allow for reading in of module attachment

def _summarize_bytes(data, limit=64):
    if data is None:
        return "None"
    if not isinstance(data, (bytes, bytearray)):
        return repr(data)
    display = data[:limit]
    hex_sample = " ".join(f"{byte:02X}" for byte in display)
    ascii_sample = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in display)
    remainder = len(data) - len(display)
    suffix = "" if remainder <= 0 else f" ... (+{remainder} bytes)"
    return f"{len(data)} bytes | hex: {hex_sample} | ascii: {ascii_sample}{suffix}"


class SerialDebugWrapper:
    def __init__(self, serial_obj, logger=None, name="serial"):
        object.__setattr__(self, "_ser", serial_obj)
        object.__setattr__(self, "_logger", logger or logging.getLogger(__name__))
        object.__setattr__(self, "_name", name)

    def _serial_id(self):
        port = getattr(self._ser, "port", "unknown")
        baud = getattr(self._ser, "baudrate", "unknown")
        return f"{self._name}@{port} (baud {baud})"

    def write(self, data):
        self._logger.debug("%s.write request: %s", self._serial_id(), _summarize_bytes(data))
        try:
            written = self._ser.write(data)
        except Exception:
            self._logger.exception("%s.write failed", self._serial_id())
            raise
        self._logger.debug("%s.write completed: %s bytes written", self._serial_id(), written)
        return written

    def read(self, size=1):
        in_waiting = None
        try:
            in_waiting = getattr(self._ser, "in_waiting", None)
        except Exception:
            pass
        self._logger.debug("%s.read request: size=%s, in_waiting=%s", self._serial_id(), size, in_waiting)
        start_time = time.time()
        try:
            data = self._ser.read(size)
        except Exception:
            self._logger.exception("%s.read failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.read response (%0.3fs): %s", self._serial_id(), duration, _summarize_bytes(data))
        return data

    def readline(self, *args, **kwargs):
        self._logger.debug("%s.readline request", self._serial_id())
        start_time = time.time()
        try:
            data = self._ser.readline(*args, **kwargs)
        except Exception:
            self._logger.exception("%s.readline failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.readline response (%0.3fs): %s", self._serial_id(), duration, _summarize_bytes(data))
        return data

    def read_until(self, *args, **kwargs):
        self._logger.debug("%s.read_until request", self._serial_id())
        start_time = time.time()
        try:
            data = self._ser.read_until(*args, **kwargs)
        except Exception:
            self._logger.exception("%s.read_until failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.read_until response (%0.3fs): %s", self._serial_id(), duration, _summarize_bytes(data))
        return data

    def reset_input_buffer(self):
        self._logger.debug("%s.reset_input_buffer()", self._serial_id())
        return self._ser.reset_input_buffer()

    def reset_output_buffer(self):
        self._logger.debug("%s.reset_output_buffer()", self._serial_id())
        return self._ser.reset_output_buffer()

    def flush(self):
        self._logger.debug("%s.flush()", self._serial_id())
        return self._ser.flush()

    def close(self):
        self._logger.debug("%s.close()", self._serial_id())
        return self._ser.close()

    def __getattr__(self, item):
        return getattr(self._ser, item)

    def __setattr__(self, key, value):
        if key in {"_ser", "_logger", "_name"}:
            object.__setattr__(self, key, value)
        else:
            setattr(self._ser, key, value)

    def __delattr__(self, item):
        if item in {"_ser", "_logger", "_name"}:
            object.__delattr__(self, item)
        else:
            delattr(self._ser, item)

    def __dir__(self):
        return sorted(set(dir(self.__class__)) | set(self.__dict__.keys()) | set(dir(self._ser)))

    def __repr__(self):
        return f"<SerialDebugWrapper for {self._serial_id()}>"


class Module_0:
    def __init__(self, master):
        global settings_file
        log_level_name = os.getenv("ESS_SERIAL_DEBUG_LEVEL", "DEBUG").upper()
        log_level = getattr(logging, log_level_name, logging.DEBUG)
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            logging.basicConfig(level=log_level,
                                format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
        if root_logger.level == logging.NOTSET or root_logger.level > log_level:
            root_logger.setLevel(log_level)
        self.logger = logging.getLogger(f"{__name__}.Module_0")
        self.logger.setLevel(log_level)
        self.logger.debug("Module_0 initialization started with log level %s",
                          logging.getLevelName(log_level))
        self._raw_serial_handle = None
        self._serial_debug_wrapper = None
        self.root = master
        self.root.title("ESS System Interface")
        self.screen_handler = True
        full_screen = True
        if full_screen:
            self.root.attributes('-fullscreen',self.screen_handler) # fullscreen on touchscreen
        else:
            self.root.geometry('800x480') # actual size of RPi touchscreen
        #self.root.attributes('-fullscreen',True)
        self.root.configure(bg= "sky blue")
        self.root.minsize(800,480) # min size the window can be dragged to
    
        self.open_loop_stop = None # control open Loop button
        # parameters for buttons and frames
        #create all the buttons onto to the main window
        button_width = 8
        button_big_height = 4
        button_small_height = 3
        sticky_to = 'nsew' # allows all buttons to resize
        
        # battery check functions
        self.percent = 0 # battery percent variable
        self.charging = False
        self.battery_array = []
        battery_font = tkFont.Font(family = "Lucida Grande", size = 9)
        label_font = tkFont.Font(family = "Lucida Grande", size = 12)
        warning_font = tkFont.Font(family = "Lucida Grande", size = 24)
        module_message = 'Module 0: Base ESS'
        # setup Serial port- 
         ## Graphing Frame and fake plot
        self.graph_frame = Frame(self.root, background = "white")
        self.graph_frame.grid(row = 1, column = 1, columnspan = 7, rowspan = 5, padx = 1, pady = 3, sticky = sticky_to)
        
        #initalize figure
        self.fig = plt.figure()
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('ADC Counts')
        plt.xlim(300,900)
        plt.ylim(0,66500)
        plt.subplots_adjust(bottom =0.14, right = 0.95, top = 0.96)
        
        #initalize canvas for plotting
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)  # A tk.DrawingArea.
        # create toolbar for canvas
        NavigationToolbar2Tk.toolitems = [t for t in NavigationToolbar2Tk.toolitems if
             t[0] not in ('Subplots',)]
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.graph_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill = BOTH, expand = True)
        
        ### bind an escape button to allow for minimizing and maximizing window
        self.root.bind("<Escape>", self.toggle_screen)
        self.root.bind_all("<ISO_Left_Tab>", self.open_cal_window)
        self.root.bind_all("<F3>", self.check_seq_foot)
        self.root.bind_all("<exclam>", self.check_seq_foot)
        #toolbar.children['Subplots'].pack_forget()
        # create function object for calling functions
        settings_func = _Settings(settings_file)
        
        
        
        try:
            settings_func.create_settings()
        except Exception:
            self.logger.exception("settings_func.create_settings() raised an exception")
        
        #(self.settings, self.wavelength) = settings_func.settings_read()
        self.logger.debug("Instantiating functions helper")
        self.func = functions(self.root, self.canvas, self.fig)
        self.logger.debug("functions helper instantiated: %s", self.func)
        self._wrap_serial_for_debugging()
        self._log_serial_state("post functions init")
        self.calibration_win = calibration_window(self.root)
        #self.func.home()
        
        
        # allow buttons and frames to resize with the resizing of the root window
        self.root.grid_columnconfigure((0,1,2,3,4,5,6,7),weight = 1)
        self.root.grid_rowconfigure((0,1,2,3,4,5,6),weight = 1)
        
        
        # with all their corresponding functions (command)
        self.quit_button = Button(self.root, text = "Quit", fg = 'Red', command = self.quit_button, width = button_width, height = button_big_height)
        self.quit_button.grid(row = 0, column = 6, padx = 1, sticky = sticky_to)
        
        self.help_button = Button(self.root, text = "Help", fg = 'black', command = lambda: help_window_pop(self.root), width = button_width, height = button_big_height)
        self.help_button.grid(row = 0, column = 5, sticky = sticky_to)
        
        self.settings_button = Button(self.root, text = "Settings", fg = 'black', command = lambda: self.window_popup(self.root), width = button_width, height = button_big_height)
        self.settings_button.grid(row = 0, column = 4, padx = (1,1), sticky = sticky_to)
        
        self.save_spectra_button = Button(self.root, text = "Save as Spectra", wraplength = 80, fg = 'black', command = self.check_spectra, width = button_width, height = button_big_height, state = NORMAL)
        self.save_spectra_button.grid(row = 0, column = 3, padx = (1,1), sticky = sticky_to)
        
        self.save_reference_button = Button(self.root, text = "Save as Reference", wraplength = 80, fg = 'black', command = self.check_ref_number, width = button_width, height = button_big_height, state = NORMAL)
        self.save_reference_button.grid(row = 0, column = 2, padx = (1,0), sticky = sticky_to)
        
        self.open_new_button = Button(self.root, text = "New Experiment", wraplength = 80, fg = 'black', command = self.func.open_new_experiment, width = button_width, height = button_big_height)
        self.open_new_button.grid(row = 0, column = 1, padx = (0,1), sticky = sticky_to)
        
        self.open_experiment_button = Button(self.root, text = "Open Experiment", wraplength = 80, fg = 'black', command = self.check_scan_number_open_file, width = button_width, height = button_big_height)
        self.open_experiment_button.grid(row = 0, column = 0, sticky = sticky_to)
        
        self.acquire_button = Button(self.root, text = "Acquire", wraplength = 80, fg = 'black',
                                     command = lambda: self.func.acquire(save = False), width = button_width, height = button_big_height)
        self.acquire_button.grid(row = 1, column = 0, pady = (3,1), sticky = sticky_to)
        
        self.acquire_save_button = Button(self.root, text = "Acquire and Save", fg = 'black', wraplength = 80,
                                          command = self.check_scan_number
                                          , width = button_width, height = button_big_height, state = NORMAL)
        self.acquire_save_button.grid(row = 2, column = 0, pady = (0,1), sticky = sticky_to)
        
        self.autorange_button = Button(self.root, text = "Auto-Range", fg = 'black', wraplength = 80,
                                       command = self.func.autorange,width = button_width,
                                       height = button_big_height)
        self.autorange_button.grid(row = 3, column = 0, pady = (0,5), sticky = sticky_to)
        
        self.open_loop_button = Button(self.root, text = "Open Loop", fg = 'black',state = NORMAL, command = self.open_loop, width = button_width, height = button_big_height)
        self.open_loop_button.grid(row = 4, column = 0, pady = (5,1), sticky = sticky_to)
        
        self.sequence_button = Button(self.root, text = "Sequence", fg = 'black', wraplength = 80, command = lambda: self.func.sequence(save = False), width = button_width, height = button_big_height)
        self.sequence_button.grid(row = 5, column = 0, sticky = sticky_to)
        
        self.sequence_save_button = Button(self.root, text = "Sequence and Save", fg = 'black', wraplength = 80, command = self.check_seq_number, width = button_width, height = button_big_height)
        self.sequence_save_button.grid(row = 6, column = 0, sticky = sticky_to)
        
        #self.scan_button = Button(self.root, text = "Scan", fg = 'black', wraplength = 80, command = lambda: self.func.scan(save = True), width = button_width, height = button_small_height)
        #self.scan_button.grid(row = 6, column = 1, padx = 1, sticky = sticky_to)
        
        self.ratio_view_button = Button(self.root, text = "Ratio View", fg = 'black', wraplength = 80, command = self.ratio_view_toggle, width = button_width, height = button_small_height, state = NORMAL)
        self.ratio_view_button.grid(row = 6, column = 1, padx = 1, sticky = sticky_to)
        
        self.autoscale_button = Button(self.root, text = "Autoscale", fg = 'black', wraplength = 80, command = self.autoscale_toggle, width = button_width, height = button_small_height)
        self.autoscale_button.grid(row = 6, column = 2, padx = 1, sticky = sticky_to)
        
        self.plot_selected_button = Button(self.root, text = "Plot Selected", fg = 'black', wraplength = 80, command = self.func.plot_selected, state = NORMAL, width = button_width, height = button_small_height)
        self.plot_selected_button.grid(row = 6, column = 3, padx = 1, sticky = sticky_to)
        
        self.clear_button = Button(self.root, text = "Clear", fg = 'black', wraplength = 80, command = self.func.clear, width = button_width, height = button_small_height)
        self.clear_button.grid(row = 6, column = 4, padx = 1, sticky = sticky_to)
        
        self.add_remove_button = Button(self.root, text = "Add/Remove Plots", fg = 'black', wraplength = 85, state = NORMAL, command = self.func.add_remove_func, width = button_width, height = button_small_height)
        self.add_remove_button.grid(row = 6, column = 5, columnspan = 2, padx = 5, pady = 1, sticky = sticky_to)
        
        module_label = Label(self.root, bg = 'sky blue', text = module_message, wraplength = 80, font = label_font)
        module_label.grid(row = 6, column = 7, padx = 5, pady = 1,  sticky = sticky_to)
        
        self.scan_label = Label(self.root, bg = 'sky blue', text = "Scan: ", wraplength = 80)
        self.scan_label.grid(row = 0, column = 7, padx = 5, pady = 1, sticky = 'nsew')
        

        self.battery_frame = Frame(self.root, bg = 'sky blue', width = 4)
        self.battery_frame.grid(row = 0, column = 7, padx = (0,1), pady = 1, sticky = 'nsew')
        
        battery_width = 6
        
        self.battery_label_1 = Label(self.battery_frame, bg = "green", height = 1, width = battery_width)
        self.battery_label_1.grid(row = 0, column = 0, padx = 1, sticky = 'nsew')
        
        self.battery_label_2 = Label(self.battery_frame, text = "%", font = battery_font, height = 1, bg = "green", width = battery_width)
        self.battery_label_2.grid(row = 1, column = 0, padx = 1, sticky = 'nsew')
        
        self.battery_label_3 = Label(self.battery_frame, bg = "green", height = 1,width = battery_width)
        self.battery_label_3.grid(row = 2, column = 0, padx = 1, sticky = 'nsew')
        
        self.battery_label_4 = Label(self.battery_frame, bg = "green",height = 1, width = battery_width)
        self.battery_label_4.grid(row = 3, column = 0, padx = 1, sticky = 'nsew')
        
        self.scan_label = Label(self.battery_frame, bg = 'sky blue', text = "Scan: ", font = battery_font, height = 1, width = battery_width, wraplength = 80)
        self.scan_label.grid(row = 4, column = 0, padx = 1, sticky = 'nsew')
        
        self.battery_frame.grid_rowconfigure((0,1,2,3,4),weight = 1)
        self.battery_frame.grid_columnconfigure((0),weight = 1)
        
        # show module connected
        #messagebox.showinfo('Module #','Module 0: Base ESS System connected (No attachments)')
        
        # check battery percent from arduino
        def battery_percent_check():
            self.logger.debug("battery_percent_check triggered")
            raw_percent = self.func.battery_check()
            self.logger.debug("battery_percent_check raw response: %s", raw_percent)
            self._log_serial_state("battery_percent_check.post-read")
            self.charging = False
            try:
                percent_int = int(raw_percent)
            except Exception:
                self.logger.exception("Unable to convert battery percent '%s' to int", raw_percent)
                percent_int = 0
            if percent_int == 1000:
                self.charging = True
            self.battery_array.append(percent_int)
            
            if len(self.battery_array) > 10:
                del self.battery_array[0]
                
            #average battery_array
            if self.battery_array:
                self.percent = int(sum(self.battery_array)/(len(self.battery_array)))
            else:
                self.percent = percent_int
            if  self.percent >100:
                self.percent = 100
            elif self.percent < 0:
                self.percent = 1
            self.logger.debug("battery_percent_check processed: averaged=%s charging=%s history=%s",
                              self.percent, self.charging, list(self.battery_array))
            if self.charging:
                self.battery_label_1.configure(bg = 'green')
                self.battery_label_2.configure(font = battery_font, text = "Charging", bg = 'green')
                self.battery_label_3.configure(bg = 'green')
                self.battery_label_4.configure(bg = 'green')
            else:
                if int(self.percent) >=75:
                    
                    self.battery_label_1.configure(bg = 'green')
                    self.battery_label_2.configure(font = battery_font, text = str(self.percent) + " %", bg = 'green')
                    self.battery_label_3.configure(bg = 'green')
                    self.battery_label_4.configure(bg = 'green')
                
                elif int(self.percent) <75 and int(self.percent) >= 50:
                    self.battery_label_2.configure(font = battery_font, text = str(self.percent) + " %",bg = 'green')
                    self.battery_label_1.configure(bg = 'red')
                    self.battery_label_3.configure(bg = 'green')
                    self.battery_label_4.configure(bg = 'green')
                    
                elif int(self.percent) <50 and int(self.percent) >=25:
                    self.battery_label_1.configure(bg = 'red')
                    self.battery_label_2.configure(font = battery_font, text = str(self.percent) + " %",bg = 'red')
                    self.battery_label_3.configure(bg = 'green')
                    self.battery_label_4.configure(bg = 'green')
                    
                elif int(self.percent) < 25 and int(self.percent) >= 15:
                    self.battery_label_1.configure(bg = 'red')
                    self.battery_label_2.configure(font = battery_font, text = str(self.percent) + " %",bg = 'red')
                    self.battery_label_3.configure(bg = 'red')
                    self.battery_label_4.configure(bg = 'yellow')
                else:
                    self.battery_label_1.configure(bg = 'red')
                    self.battery_label_2.configure(font = battery_font, text = "LOW",bg = 'red')
                    self.battery_label_3.configure(bg = 'red')
                    self.battery_label_4.configure(bg = 'red')
                    
                    error_top = Toplevel(self.root, bg = "red")
                    message = Label(error_top, bg = "white", text = "Low Battery! Plug In device and Save Data", font = warning_font, wraplength = 250)
                    message.grid(row = 0, column = 0, padx = 10, pady = 10)
                    error_top.title("Warning")
                    error_top.lift()
                    
                    error_top.after(3000, error_top.destroy)


            try:
                self.root.after(10000, battery_percent_check)
            except Exception:
                self.logger.exception("Failed to schedule battery_percent_check via root.after")
            
        battery_percent_check()

    def check_scan_number(self):
        self.logger.debug("check_scan_number invoked (save=True)")
        self._log_serial_state("check_scan_number.before")
        message = self.func.acquire(save = True)
        self.logger.debug("check_scan_number response: %s", message)
        self._log_serial_state("check_scan_number.after")
        print(message)
        self.scan_label.config(text = message)
    
    def check_ref_number(self):
        self.logger.debug("check_ref_number invoked")
        self._log_serial_state("check_ref_number.before")
        message = self.func.save_reference()
        self.logger.debug("check_ref_number response: %s", message)
        self._log_serial_state("check_ref_number.after")
        self.scan_label.config(text = message)
    
    def check_spectra(self):
        self.logger.debug("check_spectra invoked")
        self._log_serial_state("check_spectra.before")
        message = self.func.save_spectra()
        self.logger.debug("check_spectra response: %s", message)
        self._log_serial_state("check_spectra.after")
        self.scan_label.config(text = message)
        
    def check_seq_number(self):
        self.logger.debug("check_seq_number invoked (save=True)")
        self._log_serial_state("check_seq_number.before")
        message = self.func.sequence(save=True)
        self.logger.debug("check_seq_number response: %s", message)
        self._log_serial_state("check_seq_number.after")
        self.scan_label.config(text = message)
                       
    def check_scan_number_open_file(self):
        self.logger.debug("check_scan_number_open_file invoked")
        self._log_serial_state("check_scan_number_open_file.before")
        message = self.func.OpenFile()
        self.logger.debug("check_scan_number_open_file response: %s", message)
        self._log_serial_state("check_scan_number_open_file.after")
        self.scan_label.config(text = message)
                       
    def check_seq_foot(self, event):
        self.logger.debug("check_seq_foot invoked via event: %s", event)
        self._log_serial_state("check_seq_foot.before")
        message = self.func.sequence(save=True)
        self.logger.debug("check_seq_foot response: %s", message)
        self._log_serial_state("check_seq_foot.after")
        self.scan_label.config(text = message)
                       
   # allows for popup of settings window
    def window_popup(self, master):
        self.logger.debug("Opening settings popup window")
        self.popup_window = Toplevel(master)
        self.sett_popup = settings_window.settings_popup_window(self.popup_window, master)
        self.popup_window.wait_window()
        self.logger.debug("Settings popup closed; applying lamp voltage adjustments")
        self._log_serial_state("window_popup.before set_lamp_voltage")
        try:
            self.func.set_lamp_voltage()
        except Exception:
            self.logger.exception("self.func.set_lamp_voltage() raised an exception")
            raise
        self._log_serial_state("window_popup.after set_lamp_voltage")
        command = b"read\n"
        self.logger.debug("Sending serial command from window_popup: %s", _summarize_bytes(command))
        try:
            self.func.ser.write(command)
        except Exception:
            self.logger.exception("Serial write failed during window_popup")
            raise
        self._log_serial_state("window_popup.after write")
        try:
            blahdata = self.func.ser.read(576)
        except Exception:
            self.logger.exception("Serial read failed during window_popup")
            raise
        self.logger.debug("Serial read result in window_popup: %s", _summarize_bytes(blahdata))
        self._log_serial_state("window_popup.after read")

    #open calibration window
    def open_cal_window(self, event):
        self.calibration_win.create_window()

    def _wrap_serial_for_debugging(self):
        if not hasattr(self, "func"):
            self.logger.debug("_wrap_serial_for_debugging called before functions helper was created")
            return
        ser = getattr(self.func, "ser", None)
        if ser is None:
            self.logger.warning("functions helper does not expose 'ser'; serial debugging disabled")
            return
        if isinstance(ser, SerialDebugWrapper):
            self.logger.debug("Serial port already wrapped for debugging")
            self._serial_debug_wrapper = ser
            return
        self._raw_serial_handle = ser
        wrapper = SerialDebugWrapper(ser, logger=self.logger, name="functions.ser")
        self.func.ser = wrapper
        self._serial_debug_wrapper = wrapper
        port = getattr(wrapper, "port", "unknown")
        baud = getattr(wrapper, "baudrate", "unknown")
        self.logger.info("Serial debug wrapper attached to port=%s baud=%s", port, baud)
        self._log_serial_state("wrap_serial.after")

    def _log_serial_state(self, context):
        if not hasattr(self, "func"):
            self.logger.debug("Serial state [%s]: functions helper not ready", context)
            return
        ser = getattr(self.func, "ser", None)
        if ser is None:
            self.logger.debug("Serial state [%s]: no serial handle available", context)
            return
        details = {}
        for attr in ("port", "is_open", "baudrate", "timeout", "write_timeout"):
            try:
                details[attr] = getattr(ser, attr)
            except Exception as exc:
                details[attr] = f"error: {exc}"
        for attr in ("in_waiting", "out_waiting"):
            try:
                details[attr] = getattr(ser, attr)
            except Exception as exc:
                details[attr] = f"error: {exc}"
        self.logger.debug("Serial state [%s]: %s", context, details)

    # send values to change visualization of data in functions class
    def autoscale_toggle(self):
        if self.autoscale_button['relief'] == SUNKEN:
            self.autoscale_button.config(bg = 'light grey', relief = RAISED)
        else:
            self.autoscale_button.config(bg = 'gold', relief = SUNKEN)
        self.func.autoscale()
                        
    def ratio_view_toggle(self):
        if  self.ratio_view_button['relief'] == SUNKEN:
            self.open_loop_button.config(state = NORMAL)
            self.autorange_button.config(state = NORMAL)
            self.ratio_view_button.config(bg = 'light grey', relief = RAISED)
        else:
            self.open_loop_button.config(state = DISABLED)
            self.autorange_button.config(state = DISABLED)
            self.ratio_view_button.config(bg = 'gold', relief = SUNKEN)
        self.func.ratio_view()
        
    # handle the button appearance and handles openloop functionality
    def open_loop_state(self):
        if self.open_loop_stop is not None:
            self.settings_button.config(state = NORMAL)
            self.acquire_button.config(state = NORMAL)
            self.acquire_save_button.config(state = NORMAL)
            self.sequence_button.config(state = NORMAL)
            self.sequence_save_button.config(state = NORMAL)
            self.autorange_button.config(state=NORMAL)
            self.open_loop_button.config(command = self.open_loop,
                                         relief = RAISED, bg = 'light grey')
            self.ratio_view_button.config(state = NORMAL)
            self.plot_selected_button.config(state = NORMAL)
            self.save_spectra_button.config(state = NORMAL)
            self.add_remove_button.config(state = NORMAL)
            self.save_reference_button.config(state = NORMAL)
            self.open_new_button.config(state = NORMAL)
            self.open_experiment_button.config(state = NORMAL) 
            self.help_button.config(state = NORMAL)
            
            
            self.root.after_cancel(self.open_loop_stop)
    
    def open_loop(self):
        self.logger.debug("open_loop triggered")
        self.settings_button.config(state = DISABLED)
        self.acquire_button.config(state = DISABLED)
        self.acquire_save_button.config(state = DISABLED)
        self.sequence_button.config(state = DISABLED)
        self.sequence_save_button.config(state = DISABLED)
        self.autorange_button.config(state=DISABLED)
        self.ratio_view_button.config(state = DISABLED)
        self.plot_selected_button.config(state = DISABLED)
        self.save_spectra_button.config(state = DISABLED)
        self.add_remove_button.config(state = DISABLED)
        self.save_reference_button.config(state = DISABLED)
        self.open_new_button.config(state = DISABLED)
        self.open_experiment_button.config(state = DISABLED) 
        self.help_button.config(state= DISABLED)
        
        
        self.open_loop_button.config(command = self.open_loop_state,
                                     relief = SUNKEN, bg = 'gold')
        self._log_serial_state("open_loop.before")
        self.func.open_loop_function()
        self._log_serial_state("open_loop.after")
        self.open_loop_stop = self.root.after(1 , self.open_loop)
    
    def quit_button(self):
        self.root.destroy()
        self.root.quit()
    def toggle_screen(self, event):
        self.screen_handler = not self.screen_handler
        self.root.attributes('-fullscreen', self.screen_handler)
    
        
                    
