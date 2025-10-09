## tkinter used for widgets that make up GUI framework
from tkinter import *
import numpy as np #https://scipy-lectures.org/intro/numpy/operations.html
from tkinter import messagebox
import tkinter.font as tkFont

## need to acquire spectra
from ESS_functions import *
from settings import Settings as _Settings
import settings_window

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

class calibration_window:
    def __init__(self, master):
        self.master = master
        self.screen_handler = False
        
        #display variables
        self.lbl_counter = 0
        self.known_peaks = []
        self.added_peaks = []
        self.known_peaks_list = ['312.567','365.015', '404.656',
                                 '435.833', '546.074', '578.5']
        self.peak_counter = 0
        
    def create_window(self):
        self.cal_window = Toplevel(self.master)
        self.cal_window.attributes('-fullscreen', True)
        self.cal_window.title("Calibration Window")
        full_screen = False
        if full_screen:
            self.cal_window.attributes('-fullscreen',self.screen_handler) # fullscreen on touchscreen
        else:
            self.cal_window.geometry('800x480') # actual size of RPi touchscreen
        #self.root.attributes('-fullscreen',True)
        self.cal_window.configure(bg= "sky blue")
        self.cal_window.minsize(800,480) # min size the window can be dragged to
        self.cal_window.bind("<Escape>", self.toggle_screen)
        self.cal_window.bind("<Return>", self.add_label)
        
        
        ### create our graph frame and buttons
        #create all the buttons onto to the main window
        button_width = 8
        button_big_height = 4
        button_small_height = 3
        sticky_to = 'nsew' # allows all buttons to resize
        
        battery_font = tkFont.Font(family = "Lucida Grande", size = 9)
        label_font = tkFont.Font(family = "Lucida Grande", size = 12)
        warning_font = tkFont.Font(family = "Lucida Grande", size = 24)
        module_message = 'Module 0: Base ESS'
        # setup Serial port- 
         ## Graphing Frame and fake plot
        self.graph_frame = Frame(self.cal_window, background = "white")
        self.graph_frame.grid(row = 2, column = 0, rowspan = 2, padx = 1, pady = 3, sticky = sticky_to)
        
        #initalize figure
        self.fig = plt.figure()
        plt.xlabel('Pixel #')
        plt.ylabel('ADC Counts')
        plt.xlim(0,300)
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
        
        ## intialize the functions 
        self.func = functions(self.cal_window, self.canvas, self.fig)
        settings_func = _Settings(settings_file)
        
        
        #############################################
        #### allow for selecting pixel locations #####
        
        self.fig.canvas.mpl_connect('button_press_event', self.pick_loc)
                                    
        #####################################################################
        
        
        quit_btn = Button(self.cal_window, text = 'Back', command = self.quit_screen, height = 10)
        quit_btn.grid(row = 0, column = 0, rowspan = 2, padx = 2, pady = 2, sticky = sticky_to)

        ############### add peaks frame ###########################
        self.add_entry_frame = Frame(self.cal_window, bg = 'sky blue')
        self.add_entry_frame.grid(row = 2, column = 1,padx = 1, sticky = sticky_to)
        
        ## acquire and integration time
        self.settings_button = Button(self.add_entry_frame, text = "Settings", fg = 'black', command = lambda: self.window_popup(self.cal_window))
        self.settings_button.grid(row = 0, column = 0, padx = 1, pady = 2, sticky = sticky_to)
        
        self.acquire_button = Button(self.add_entry_frame, text = "Acquire", wraplength = 80, fg = 'black',
                                     command = self.func.calibration_acquire)
        self.acquire_button.grid(row = 1, column = 0, padx = 1, pady = 2, sticky = sticky_to)
       
        self.pixel_number = StringVar()
        add_lbl = Label(self.add_entry_frame, text = "Pixel #", bg = 'sky blue')
        add_lbl.grid(row = 3, column = 0, sticky = sticky_to)
        
        self.add_peak_entry = Entry(self.add_entry_frame, width = 4, textvariable = self.pixel_number)
        self.add_peak_entry.grid(row = 4, column = 0, padx = 2, sticky = sticky_to)
        
        self.known_value = StringVar()
        known_label = Label(self.add_entry_frame, text = "Known Wavelength (nm)", bg = 'sky blue')
        known_label.grid(row = 5, column = 0,sticky = sticky_to)
        
        self.add_known_entry = Entry(self.add_entry_frame, width = 4, textvariable = self.known_value)
        self.add_known_entry.grid(row = 6, column = 0, sticky = sticky_to)
        
        self.add_peak_button = Button(self.add_entry_frame, text = 'Add Peak', command = self.add_label)
        self.add_peak_button.grid(row = 7, column = 0,columnspan = 2, padx = 1, sticky = sticky_to)
        try:
            self.known_value.set(str(self.known_peaks_list[self.peak_counter]))
        except:
            pass
        ############### display peaks frame ##################
        self.display_lbl_frame = Frame(self.cal_window, bg = 'sky blue')
        self.display_lbl_frame.grid(row = 3, column=1, padx = 1, sticky = sticky_to)
        
        ######################################################
        self.create_poly_btn = Button(self.cal_window, fg = 'green', command = self.create_poly,
                                  text = 'Create Calibration Coefficients')
        self.create_poly_btn.grid(row = 4, column = 0, padx = 2, pady = 4, sticky = sticky_to)
        
        title_lbl = Label(self.cal_window, text = "Calibration Window", wraplength = 100, bg = 'sky blue')
        title_lbl.grid(row = 4, column = 1, padx = 2, pady = 2, sticky = sticky_to)
        
       # allow buttons and frames to resize with the resizing of the root window
        self.cal_window.grid_columnconfigure((0,1),weight = 1)
        self.cal_window.grid_rowconfigure((0,1,2,3),weight = 1)
        
    def pick_loc(self, event):
        xdata = event.xdata
        self.pixel_number.set(str(xdata))
        try:
            self.known_value.set(str(self.known_peaks_list[self.peak_counter]))
        except:
            pass
            
    def add_label(self, event = None):
        if self.pixel_number.get() is not None and self.known_value.get() is not None:
            value = int(float(self.pixel_number.get()))
            nm = int(float(self.known_value.get()))
            lbl_str = "Pixel: " + '~' + str(value) + " @ " + str(nm) + "nm"
            known = float(self.known_value.get())
            pixel = float(self.pixel_number.get())
            self.pixel_number.set('')
            self.known_value.set('')
            self.known_peaks +=[known]
            self.added_peaks += [pixel]
            self.label = Label(self.display_lbl_frame, text = lbl_str, bg = 'sky blue')
            self.label.grid(row = self.lbl_counter, column = 0, padx = 1, sticky = 'nsew')
            self.cal_window.update()
            self.cal_window.update_idletasks()
            self.lbl_counter = self.lbl_counter + 1
            self.peak_counter = self.peak_counter +1
            try:
                self.known_value.set(str(self.known_peaks_list[self.peak_counter]))
            except:
                pass
            
    def create_poly(self):
        if len(self.known_peaks) >= 5:
            x = np.array(self.added_peaks)
            y = np.array(self.known_peaks)
            z = np.polyfit(x, y, 5)
            self.func.calibration_acquire(pixel = False, coeff = z)
            
    ### create settings window
    def window_popup(self, master):
        self.popup_window = Toplevel(master)
        self.sett_popup = settings_window.settings_popup_window(self.popup_window, master)
    
    def quit_screen(self):
        self.cal_window.destroy()
        
    def toggle_screen(self, event):
        self.screen_handler = not self.screen_handler
        self.cal_window.attributes('-fullscreen', self.screen_handler)
        ## needed variables
        
    
