from tkinter import *
from tkinter.ttk import *
import matplotlib.pyplot
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import time

import serial
from settings import Settings as _Settings
from keyboard import *
from add_remove_popup import *
import tkinter.font as tkfont

import pandas as pd
import numpy as np
import csv
from tkinter import messagebox

from tkinter.filedialog import askopenfilename
import os
import matplotlib.pyplot as plt

import RPi.GPIO as GPIO
import spidev
from smbus import SMBus

################# Global Variables ############################
global settings_file
global acquire_file
global path

settings_file = '/home/pi/Desktop/Spectrometer/settings/settings.csv'
acquire_file = '/home/pi/Desktop/Spectrometer/settings/acquire_file.csv'
path = '/home/pi/Desktop/Spectrometer/'
#################################################################


class functions:
    def __init__(self, parent, _canvas, figure):
        global settings_file
        global acquire_file
        global ESS_module
        self.parent = parent # whatever parent 
        self.save_file = None # initalize file for saving data
        self.scan_file = None #initialize Scan File for saving scan data
        self.scan_number = 1 # ID for saving to csv
        self.reference_number = 1 # ref ID for saving to csv
        self.exp_folder = '/home/pi/Desktop/Spectrometer' # experiment folder used for saving
        self.df = None # data frame array used for storing and plotting data
        self.df_scan = None
        self.serial_check = False #variable for flagging serial connection
        self.battery_check_flag = False
        self.battery_percent = 100
        
        
        self.buzzer_pin = 7 # set buzzer to pin 7 (GPIO4)
        self.lamp_pin = 33
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.buzzer_pin, GPIO.OUT)
        GPIO.setup(self.lamp_pin, GPIO.OUT)
        
        
        # attributes to select data to be plotted
        self.ref = np.ones((288))*1000 # temporary reference
        self.scan_ref = None
        
        # plotting view attributes
        self.ratio_view_handler = False
        self.autoscale_handler = False
        self.prime_pump_handler = False  # handle turning on/off pump
        self.indicator_window = True
        
        # these are two possible port names for the arduino attachment
        port = "/dev/ttyUSB0"
        port2 = "/dev/ttyUSB1"
        
        try:
            self.ser = serial.Serial(port, baudrate = 115200, timeout = 5)
        except:
            self.ser = serial.Serial(port2, baudrate = 115200, timeout =5)
        
        ### set up SPI on the RPi to allow for data transfer to external devices
        self.spi = spidev.SpiDev()
        self.spi.open(0,0)
        self.spi.max_speed_hz = 12000
        self.SPI = True
        
        # set up I2C for digitalPot
        self.i2c = SMBus(1)
        
    
        # two pseudo reads to initalize the spectrometer
        
        self.ser.write(b"read\n")
        blahdata = self.ser.read(576)
        self.ser.write(b"read\n")
        blahdata = self.ser.read(576)
        
        
        # intialize attributes for handling data and files
        self.acquire_file = acquire_file
        self.settings_file = settings_file
        self.canvas = _canvas
        self.fig = figure
        
        
        # create objects for different modules needs for some functions
        self.settings_func = _Settings(settings_file)
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        self.add_remove_top = add_remove_popup(self.parent)
   
    def foot_pedal_1(self, event):
        self.acquire(save =False)
        
    def foot_pedal_2(self, event):
        self.pump_prime()
        
    def tone(self, sleep_time):
        # check buzzer setting
        if int(self.settings[43][1]):
            GPIO.output(self.buzzer_pin, True) # PWM to make sound after measurement
            time.sleep(sleep_time/1000) # sleep for given time in mSec
            GPIO.output(self.buzzer_pin, False) 
    
    #take a measurement every 30 seconds for 2 hours
    def battery_cycle(self):
        for x in range (0,240):
            self.acquire(save = False)
            time.sleep(30)
            
    def home(self):
        self.ser.write(b"home\n")
        
    def battery_check(self):
        if not self.battery_check_flag:
            self.ser.write(b"battery\n")
            percent = self.ser.readline().decode()
            self.battery_percent = percent
            return percent
        else:
            return self.battery_percent
    
    def save_scan_reference(self):
        if self.scan_file is not None:
            self.scan_ref = pd.DataFrame(np.loadtxt(self.acquire_file, delimiter = ','))
            self.df_scan['Reference %d'] = self.scan_ref
            self.df_scan.to_csv(self.scan_file, mode = 'w', index = False)
        else:
            messagebox.showerror('Error', 'No Save File selected, create save file to save reference')
        
    def save_reference(self):
        ref_message = None
        if self.save_file is not None:
            self.ref = pd.DataFrame(np.loadtxt(self.acquire_file, delimiter = ','))
            self.df['Reference %d' % self.reference_number] = self.ref
            self.df.to_csv(self.save_file, mode = 'w', index = False)
            self.reference_number = self.reference_number +1 
            ref_message = "Ref #: " + str(self.reference_number-1)
            self.ref = self.ref.to_numpy().reshape((288))
            plt.clf()
            self.plotting(np.zeros((288)), None) # send a fake value to plot updated ref
            
        else:
            messagebox.showerror('Error', 'No Save File selected, create save file to save reference')
        return ref_message
    
    def save_spectra(self):
        scan_message = None
        if self.save_file is not None:
            temp_data = pd.DataFrame(np.loadtxt(self.acquire_file, delimiter = ','))
            self.df['Scan_ID %d' % self.scan_number] = temp_data
            self.df.to_csv(self.save_file, mode = 'w', index = False)
            scan_message = "Scan: " + str(self.scan_number)
            self.scan_number = self.scan_number +1 
        else:
            messagebox.showerror('Error', 'No Save File selected, create save file to save Spectra')
        return scan_message
    
    def add_remove_func(self):
        self.add_remove_top.create_add_remove(self.save_file)
        
        if self.add_remove_top.ref_ratio is not None:
            self.ref = self.df[[self.add_remove_top.ref_ratio]].to_numpy() 
            self.ref = self.ref.reshape((288))
            
    def ratio_view(self):
        self.ratio_view_handler = not self.ratio_view_handler
        data = np.loadtxt(self.acquire_file, delimiter = ',')
        self.plotting(data, "Data")
    
    def autoscale(self):
        self.autoscale_handler = not self.autoscale_handler
        if self.autoscale_handler:
            plt.autoscale(enable= True, axis = 'y')
            self.fig.canvas.draw()
        elif not self.autoscale_handler and self.ratio_view_handler:
            plt.autoscale(enable = False, axis = 'y')
            plt.ylim(0,110)
            self.fig.canvas.draw()
        else:
            plt.autoscale(enable = False, axis = 'y')
            plt.ylim(0,66500)
            self.fig.canvas.draw()
    
    def plot_labels_axis(self):
        plt.subplots_adjust(bottom =0.14, right = 0.95, top = 0.96)

        if self.ratio_view_handler:
        
            plt.plot(self.wavelength, np.ones((288))*100, 'r--')
            if not self.autoscale_handler:
                plt.ylim(0,110)
            plt.xlim(300,900)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Ratio (%)')
        elif not self.ratio_view_handler:
            if not self.autoscale_handler:
                plt.ylim(0,66500)
            plt.xlim(300,900)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('ADC counts')
        #self.fig.canvas.draw()
        
    def plotting(self, data, label_view):
        
        data = pd.DataFrame(data).to_numpy().reshape((288))
        self.plot_labels_axis() # configure axis
        if self.ratio_view_handler:
            plt.clf()
            self.plot_labels_axis() # configure axis
            
            if self.add_remove_top.ref_ratio is not None:
                self.ref = self.df[[self.add_remove_top.ref_ratio]].to_numpy()
                self.ref = self.ref.reshape((288))
            try:
                self.ref = self.ref.to_numpy().reshape((288))
            except:
                pass

            data = np.true_divide(data, self.ref)*100
            if self.add_remove_top.data_headers is not None:
                data_sel = pd.read_csv(self.save_file, header = 0)
                data_sel = data_sel[self.add_remove_top.data_headers]
                for col in range(0, len(self.add_remove_top.data_headers)):
                    data_new = data_sel[str(self.add_remove_top.data_headers[col])]
                    data_new = data_new.to_numpy()
                    data_plot = np.true_divide(data_new, self.ref)*100
                    plt.plot(self.wavelength, data_plot, label = self.add_remove_top.data_headers[col])
                #plt.legend(self.add_remove_top.data_headers, loc = "upper right", prop = {'size': 6})
        else:
            if self.add_remove_top.data_headers is not None:
                data_sel = pd.read_csv(self.save_file, header = 0)
                data_sel = data_sel[self.add_remove_top.data_headers]
                for col in range(0,len(self.add_remove_top.data_headers)):
                    plt.plot(self.wavelength, data_sel.iloc[:,col], label = self.add_remove_top.data_headers[col])
       
                #for col in range(0,len(self.add_remove_top.data_headers)):
                #plt.legend(self.add_remove_top.data_headers, loc = "upper right", prop = {'size': 6})
            else:
                pass
            
            try:
                self.ref = self.ref.to_numpy()
                plt.plot(self.wavelength,self.ref, 'r--', label = 'Reference')
            except:
                plt.plot(self.wavelength,self.ref,'r--', label = "Reference")
                
        plt.plot(self.wavelength, data, label = label_view)
        plt.xlim(int(self.settings[9][1]), int(self.settings[10][1]))
        plt.legend()
        self.fig.canvas.draw()
        
    def open_new_experiment(self):
        global path
        keyboard = key_pad(self.parent)
        try:
            (save_file, save_folder) = keyboard.create_keypad()
            self.save_file = save_folder + '/' + save_file + "_save.csv"
        
            self.exp_folder = str(save_folder)
            if not os.path.exists(self.exp_folder):
                os.makedirs(self.exp_folder)
        
            open(self.save_file, 'w+')
            
            #reset add_remove attributes
            self.add_remove_top.data_headers = None
            self.add_remove_top.data_headers_idx = None
            self.add_remove_top.ref_ratio_idx = None
            self.add_remove_top.ref_ratio = None
            
            #create data frame for saving data to csv files
            self.df = pd.DataFrame(self.wavelength)
            self.df.columns = ['Wavelength (nm)']
            save_csv = self.df.to_csv(self.save_file, mode = 'a', index=False)
            # reset scan and ref number for saving data when new file created
            self.scan_number = 1
            self.reference_number = 1
            
        except NameError:
           messagebox.showerror("Error", "No Filename Found! Please input again to create Experiment")
                       
    def plot_selected(self):
        plt.clf()
        self.plot_labels_axis()
        
        if self.add_remove_top.data_headers is not None:
            self.plotting(np.zeros((288)), None)
        else:
            messagebox.showerror('Error','No data selected. Select data to plot')
    
    
    def clear(self):
        plt.clf()
        plt.ylim(0,66500)
        plt.xlim(300,900)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('ADC Counts')
        self.fig.canvas.draw()
        
        
        
    def dark_subtract_func(self):
        self.battery_check_flag = True
        #(self.settings, self.wavelength) = self.settings_func.settings_read()
        number_avg = int(self.settings[11][1])
        integ_time = float(self.settings[3][1])
        smoothing_used = int(self.settings[12][1])
        smoothing_width = int(self.settings[8][1])
        pulses = int(self.settings[1][1])
        dark_subtract = int(self.settings[4][1])
        pulse_rate = int(self.settings[2][1])
        
        try:
            self.ser.write(b"pulse 0\n")
            self.ser.write(b"set_integ %0.6f\n" % integ_time)
            self.ser.write(b"pulse_rate %0.6f\n" % pulse_rate)
            # tell spectromter to send data
            self.ser.write(b"read\n")
            data_read = self.ser.read(288*2)
            data_dark = np.frombuffer(data_read, dtype = np.uint16)
            '''
            #for x in range(0,1,1): #take scans then average for dark subtract
            #read data and save to pseudo csv to plot
            data_read = self.ser.readline()
            #data = self.ser.read_until('\n', size=None)
            data_dark = np.array([int(i) for i in data_read.split(b",")])
            '''
            
            #if x == 0:  # reached number of averages
            #data_dark = data_dark #take average of data and save
            #if smoothing_used == 1:  # if smoothing is checked smooth array
            #    dummy = np.ravel(data_dark)
            #    for i in range(1,286,1):
            #        data_dark[i] = sum(dummy[i-1:i+2])/(3)
            self.battery_check_flag = False
            return data_dark
        except serial.serialutil.SerialException:
            self.battery_check_flag = False
            messagebox.showerror('Error', 'Spectrometer Not connected, Connect and restart')
    
    def acquire_avg(self, pulses):
        self.battery_check_flag = True        
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        number_avg = int(self.settings[11][1])
        integ_time = float(self.settings[3][1])
        lamp_voltage = int(self.settings[5][1])
        smoothing_used = int(self.settings[12][1])
        smoothing_width = int(self.settings[8][1])
        dark_subtract = int(self.settings[4][1])
        pulse_rate = int(self.settings[2][1])
        
        self.set_lamp(lamp_voltage)
        
        #self.serial_check = self.check_serial() # always check serial before a measurement
        #if self.serial_check:
        if dark_subtract == 1:
            data_dark = self.dark_subtract_func()
        else: 
            data_dark = np.zeros((288))
        try:
            #self.set_lamp_voltage(voltage = lamp_voltage)
            self.ser.write(b"set_integ %0.6f\n" % integ_time)
            self.ser.write(b"pulse %d\n" % pulses)
            self.ser.write(b"pulse_rate %0.6f\n" % pulse_rate)        
            data = 0
            
            # tell spectromter to send data
            for x in range(0,number_avg,1): #take scans then average
                self.ser.write(b"read\n") # tell arduino to read spectrometer
                data_read = self.ser.read(288*2)
                data_temp = np.frombuffer(data_read, dtype = np.uint16)
                #data_read = self.ser.readline()
                #data_temp = np.array([int(p) for p in data_read.split(b",")])
                data = data + data_temp 
            
                if x == number_avg-1:  # reached number of averages
                    data = data/number_avg #take average of data and save
                    data = data-data_dark
                    if smoothing_used == 1:  # if smoothing is checked smooth array
                        dummy = np.ravel(data)
                        for i in range(1,286,1):
                            data[i] = sum(dummy[i-1:i+2])/(3)
                                 
            self.battery_check_flag = False
            data = np.where(data<=0,0,data)
            #self.set_lamp_voltage()
            #for idx in range(0,len(data)):
            #    if data[idx] <=0:
            #        data[idx] = 1
            return data
        
        except serial.serialutil.SerialException:
            self.battery_check_flag = False
            messagebox.showerror('Error', 'Spectrometer Not connected, Connect and Restart')
            return None
    
    def acquire(self, save):
        scan_message = None
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        self.battery_check_flag = True
        #start = time.time()
        data = self.acquire_avg(int(self.settings[1][1]))
        #end = time.time()
        if data is not None:
            if save:
                if self.save_file == None:
                    messagebox.showerror('Error', 'No Experiment File Found, create or open File to save Data')
                else:
                    # save data array to save_file
                    df_data_array = pd.DataFrame(data)
                    self.df['Scan_ID %d' %self.scan_number] = df_data_array
                    self.df.to_csv(self.save_file, mode = 'w', index = False)
                    data = self.df[['Scan_ID %d' %self.scan_number]]
                    self.scan_number = 1 + self.scan_number
                    scan_message = "Scan #: " + str(self.scan_number-1)
                    plt.clf()
                    self.plotting(data, "Scan: " +str(self.scan_number-1))
            else: # temporary save
                np.savetxt(self.acquire_file, data, fmt="%d", delimiter=",")
                data1 = pd.read_csv(self.acquire_file, header = None)
                plt.clf()
                self.plotting(data, "Scan: " +str(self.scan_number))
        self.battery_check_flag = False
        self.tone(50)
        
        #print(end-start)
        return scan_message
    
    def set_lamp(self, lamp_Voltage):
        in_max = 600
        in_min = 400
        out_max = 3854
        out_min = 2570
        voltage = int((lamp_Voltage-in_min)*(out_max-out_min)/(in_max-in_min) + out_min) 
        lamp = [(voltage >> 4) & 0xFF, (voltage << 4) & 0xFF]
        self.i2c.write_i2c_block_data(0x62, 0x40, lamp)
    
    def set_lamp_voltage(self):
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        lamp_Voltage = int(self.settings[5][1])
        in_max = 600
        in_min = 400
        out_max = 3854
        out_min = 2570
        voltage = int((lamp_Voltage-in_min)*(out_max-out_min)/(in_max-in_min) + out_min) 
        lamp = [(voltage >> 4) & 0xFF, (voltage << 4) & 0xFF]
        self.i2c.write_i2c_block_data(0x62, 0x40, lamp)
        
    def calibration_acquire(self, pixel = True, coeff = None):
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        data = self.acquire_avg(int(self.settings[1][1]))
        if data is not None:
                np.savetxt(self.acquire_file, data, fmt="%d", delimiter=",")
                data1 = pd.read_csv(self.acquire_file, header = None)
                plt.clf()
                pixel_array = np.zeros(288)
                for x in range(1,289,1):
                    pixel_array[x-1] = x
                if pixel:
                    plt.plot(pixel_array, data1)
                    self.fig.canvas.draw()
                    plt.xlabel('Pixel #')
                    plt.ylabel('ADC Counts')
                else:
                    wavelength = np.zeros(288)
                    for pixel in range(1,289,1):
                        wavelength[pixel-1] = (coeff[5] + coeff[4]*pixel + coeff[3]*(pixel**2) + coeff[2]*(pixel**3) + coeff[1]*(pixel**4) + coeff[0]*(pixel**5))
                    plt.xlabel('Pixel #')
                    plt.ylabel('ADC Counts')
                    plt.xlim(300,900)
                    
                    plt.plot(wavelength, data1)
                    
                    self.fig.canvas.draw()
                    
    
    def open_loop_function(self):
        if self.ser.is_open:
            (self.settings, self.wavelength) = self.settings_func.settings_read()
            plt.xlim(int(self.settings[9][1]), int(self.settings[10][1]))
            plt.ylabel('ADC counts')
            plt.xlabel('Wavelength (nm)')
            
            plt.clf()
            dark_subtract = int(self.settings[4][1])
            self.settings[4][1] = 0
            data = self.acquire_avg(0)
            self.settings[4][1] = dark_subtract
            data = pd.DataFrame(data)
            np.savetxt(self.acquire_file, data, fmt="%d", delimiter= ",")
            self.plotting(data, "Open Loop")
        
    def sequence(self, save):
        scan_message = None
        
        if self.ser.is_open:
            (self.settings, self.wavelength) = self.settings_func.settings_read()       
            # make sure we have a save destination if acquire and save
            if save and self.save_file == None:
                messagebox.showerror('Error', 'No Experiment File Found, create or open File to save Data')
    
            else:
                plt.clf()
                number_avg = int(self.settings[11][1])
                integ_time = int(self.settings[3][1])
                dark_subtract = int(self.settings[4][1])
                burst_number = int(self.settings[22][1])
                burst_delay = float(self.settings[21][1])
                                
                plt.xlim(int(self.settings[9][1]), int(self.settings[10][1]))
                self.plot_labels_axis() # configure axis
                self.tone(30)
                for burst in range(0,burst_number):
                    number_measurements_burst = int(self.settings[23+burst][1])
                    measurement = 0 # hold measurement number for each burst
                    pulses = int(self.settings[33+burst][1])
                    
                    #set integ time
                    self.settings[3][1] = float(40 + (pulses - 1)*(1000000/int(self.settings[2][1])))
                    if pulses > 1:
                        self.settings[3][1] = float(self.settings[3][1] + 1000000/int(self.settings[2][1]))
                    else:
                        self.settings[3][1] = 40
                    # take a dark measurement before each burst
                    if dark_subtract ==1:
                        self.settings[4][1] = 40
                        dark = self.dark_subtract_func()
                        #dark = self.acquire_avg(0)
                    else:
                        dark = np.zeros((288))
                    
                    for i in range(0,number_measurements_burst):
                        graph_label = 'Burst ' + str(burst+1) + ' measurement ' + str(i+1)
                        data = []
                        pulses = int(self.settings[33+burst][1])
                        data = self.acquire_avg(pulses)
                        data = data - dark
                        data = np.where(data<=0,0,data)
                        #check if we are in ratio view
                        if self.ratio_view_handler:
                            data_new = np.true_divide(data, self.ref)*100
                            plt.plot(self.wavelength, data_new, label = graph_label)
                        else:
                            plt.plot(self.wavelength, data, label = graph_label)
                        
                        data = pd.DataFrame(data).to_numpy()
                        
                        
                        plt.subplots_adjust(bottom = 0.14, right = 0.95)
                        plt.legend(loc = "center right", prop = {'size': 6})
                        
                        
                        
                        if save:
                            df_data_array = pd.DataFrame(data)
                            self.df['Scan_ID %d' % (self.scan_number)] = df_data_array
                            
                            self.scan_number = self.scan_number + 1
                            measurement = measurement+1
                            
                            
                    self.settings[4][1] = dark_subtract
                    self.settings[3][1] = integ_time
                    self.fig.canvas.draw()
                    time.sleep(burst_delay)
                    self.indicator_window = int(self.settings[44][1])
                    
                # after all data is taken save to sequence csv
                if save:
                    self.df.to_csv(self.save_file, mode = 'w', index = False)
                    if self.SPI:
                        cols = []
                        for x in range(0,number_measurements_burst):
                            cols += ["Scan_ID %d" % (self.scan_number - number_measurements_burst+x)]
                        SPI_array = self.df[cols].astype(float).mean(axis=1)
                        values = SPI_array
                        SPI_array = SPI_array/self.ref
                        if self.indicator_window ==1:
                            x = 250
                            y = 140
                            error_top = Toplevel(self.parent, bg = "Green")
                            error_top.geometry(f'+{x}+{y}')
                            error_top.geometry("300x250")
                            message = Label(error_top, text = "All Good", bg = "green",
                                                font = tkfont.Font(family = "Helvetica", weight = "bold", size = 15), wraplength = 300)
                            message.pack()
                            if max(values) > 60000 or max(values) < 26000:
                                error_top.configure(bg = 'red')
                                message.configure(text = 'Data Out Of Range', bg = 'red')
                                
                            error_top.after(1000, error_top.destroy)
                        self.SPI_send(SPI_array)
                scan_message = "Scan: " + str(self.scan_number-1)
        
        self.tone(30)
        time.sleep(0.05)
        self.tone(80)
        end = time.time()
        #print(end-start)
        return scan_message
    
    def autorange(self):
        (self.settings, self.wavelength) = self.settings_func.settings_read()       
        max_autorange = int(self.settings[7][1])
        autorange_thresh = int(self.settings[6][1])
        integ_time = int(self.settings[3][1])
        pulses = 1 # start with one pulse then increment
        plt.clf()
        
        plt.xlim(int(self.settings[9][1]), int(self.settings[10][1])) # change x axis limits to specified settings
        plt.ylabel('a.u.')
        plt.xlabel('Wavelength (nm)')
        # acquire data for the given # of loops plot, and prompt user to
        # select plots they wish to save with a popup window
        if self.ser.is_open:
            for x in range(0,max_autorange): 
                self.settings[1][1] = int(pulses)
                # write settings array to csv 
                self.settings_func.settings_write(self.settings)
                data = self.acquire_avg(pulses)
                if max(data) < autorange_thresh:  
                    if x < max_autorange-1:
                        pulses = pulses+1
                        plt.plot(self.wavelength,data, label = "Pulses: "+ str(self.settings[1][1]))
                        plt.subplots_adjust(bottom=0.14, right=0.86)
                        plt.legend(loc = "center right", prop={'size': 7}, bbox_to_anchor=(1.18, 0.5))
                        self.fig.canvas.draw()
                    else: 
                        messagebox.showinfo("Pulses", "Max # of Pulses reached")
                else:
                    self.settings[1][1] = int(pulses-1)
                    messagebox.showinfo("Pulses", str(self.settings[1][1]) + "  Pulses to reach threshold")
                    break
            self.settings_func.settings_write(self.settings)
            
    def OpenFile(self):
        scan_message = None    
        save_file = askopenfilename(initialdir="/home/pi/Desktop/Spectrometer",
                                    filetypes =(("csv file", "*.csv"),("All Files","*.*")),
                                    title = "Choose a file.")
        #try:
        if save_file: # check if file was selected if not dont change experiment file
            self.save_file = save_file 
            self.reference_number = 1
            self.scan_number = 1
            
            # try to scan through reference and scan number to set to correct value for further saving
            self.df = pd.read_csv(self.save_file, header = 0)
            headers = list(self.df.columns.values)
    
        #find the scan number from the opened file
        # only works for files with the specified headers
            while True:
                result = [i for i in headers if i.startswith('Scan_ID %d' %self.scan_number)]
                if result == []:
                    break
                self.scan_number = self.scan_number+1 # increment scan number until we reach correct value
            while True:
                result = [i for i in headers if i.startswith('Reference %d' %self.reference_number)]
                if result == []:
                        break
                self.reference_number = self.reference_number+1
                self.ref = pd.DataFrame(self.df['Reference %d' %(self.reference_number-1)]).to_numpy()
            self.ref = self.ref.reshape((288))
            

            #reset indexing attrubtues for later use in
            #add remove functions 
            self.add_remove_top.data_headers_idx = None
            self.add_remove_top.data_headers = None
            self.add_remove_top.ref_ratio = None
            self.add_remove_top.ref_ratio_idx = None
            scan_message = "Scan #: " + str(self.scan_number-1)
        return scan_message
    
    def SPI_send(self, data):
        to_send = []
        
        ## convert the data to two bytes
        for x in range(len(data)):
            high = (int(data[x]) >> 8) & 0xff
            low = int(data[x]) & 0xff
            to_send += [high]
            to_send += [low]
       
        self.spi.xfer(to_send)
        
    def analyze_spectra(self, data):
        ## add algorithm for analyzing spectr
        # placeholder use a simple max value filter
        score = max(data)
        
        return score
    
    ############## Module 1 Functions ################
    def new_scan(self):
        global path
        self.battery_check_flag = True
        self.home() # home the device before taking a measurement
        self.battery_check_flag = False
        keyboard = key_pad(self.parent)
        self.df_scan = None
        try:
            (scan_file, save_folder) = keyboard.create_keypad()
            self.scan_file = save_folder + '/' + scan_file + "_scan.csv"
        
            self.exp_folder = str(save_folder)
            if not os.path.exists(self.exp_folder):
                os.makedirs(self.exp_folder)
        
            open(self.scan_file, 'w+')
            
            #create data frame for saving data to csv files
            self.df_scan = pd.DataFrame(self.wavelength)
            self.df_scan.columns = ['Wavelength (nm)']
            save_csv = self.df_scan.to_csv(self.scan_file, mode = 'a', index=False)
            
        except NameError:
           messagebox.showerror("Error", "No Filename Found! Please input again to create Experiment")
        except FileExistsError:
           messagebox.showerror("Error", "Filename Already Exists. Try New Filename")
   
   # create a window to display the
   # image formed after scanning
    def scan_image_window(self):
        self.scan_image = Toplevel(self.parent)
        self.scan_image.focus_force()
        self.scan_image.geometry('450x450')
        self.scan_image.attributes('-fullscreen', True)
        self.scan_image.configure(bg = "sky blue")
        self.scan_fig = plt.figure()
        self.scan_image.bind("<Escape>", lambda x: self.scan_image.destroy)
        
        grid_size = int(self.settings[14][1])
        plt.xlabel('X Location')
        plt.ylabel('Y Location')
        plt.title('ESS Scan Image')
        
        #configure buttons
        self.save_image_btn = Button(self.scan_image, fg = "black", bg = "white", text = "Save Image",
                                     width = 8, height = 2, command = self.save_scan_image)
        self.save_image_btn.pack(padx = 3, pady = 3)
        
        self.quit_image = Button(self.scan_image, tex = "quit", command = self.scan_image.destroy)
        self.quit_image.pack()
        self.canvas = FigureCanvasTkAgg(self.scan_fig, master=self.scan_image)  # A tk.DrawingArea.
        self.df_scan = self.df_scan.to_numpy()
        self.canvas.get_tk_widget().pack(padx = 3, pady = 3, fill = BOTH)
        #initalize array for the location at each pixel
        location = np.zeros((grid_size, grid_size))
        pixel_interest = 58
        start = time.time()
        for x in range(grid_size):
            for y in range(grid_size):
                if x % 2 ==0:
                    idx = (x*grid_size) + y + 2
                    location[x,y] = self.analyze_spectra(self.df_scan[:,idx])
                    
                    #print(self.df_scan.iloc[:,2])
                else:
                    idx = (1+grid_size-y)+ (x*grid_size)
                    location[x,y] = self.analyze_spectra(self.df_scan[:,idx])

                    #((1+x)+((y)*grid_size))
        end = time.time()
        print(end-start)
        self.pcolor_handle = plt.pcolor(location)
        ax = self.pcolor_handle.axes
        ax.invert_xaxis()
        
        #cbar = self.scan_fig.colorbar(location)
        #cbar.set_ylabel('Max Value')
        self.scan_fig.canvas.draw()
        
    def save_scan_image(self):
        file_loc = self.exp_folder + str("/ESS_Scan.jpeg")
        plt.savefig(file_loc)
        
        
    def scan(self):
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        grid_size = int(self.settings[14][1])
        # check if spectrometer is connected
        if self.ser.is_open:
            self.ser.write(b"step_size %d\n" %int(self.settings[13][1]))        
            
            self.plot_labels_axis() # set axis and labels
            # if we dont have a scan file then create one for saving data
            if self.scan_file == None:
                messagebox.showerror('Error', 'No Scan File. Create scan file to save data')
            elif self.scan_file is not None:
                if self.scan_ref is not None:
                    for x in range(0,int(grid_size/2)):
                        self.ser.write(b"x 1\n")
                    time.sleep(1)
                    for y in range(0,int(grid_size/2)):
                        self.ser.write(b"y 1\n")
                    grid_size = int(self.settings[14][1])
                    scan_resolution = int(self.settings[13][1])
                    start = time.time()
                            
                    def scan_move():
                        self.ser.write(b"step_size %d\n" %scan_resolution)
                        
                        for x in range(0,grid_size):
                            for y in range(0,grid_size):
                                idx = (x*grid_size) + y
                                            
                                data = self.acquire_avg(int(self.settings[1][1]))
                                df_data_array = pd.DataFrame(data)
                                if y == grid_size-1:
                                    if (x % 2) == 0:
                                        idx = (x*grid_size) + y
                                        self.df_scan['X: %d Y: %d' % (x, y)] = df_data_array
                                    else:
                                        idx = (x*grid_size) + grid_size - y -1
                                        self.df_scan['X: %d Y: %d' % (x, grid_size-y-1)] = df_data_array
               
                                else: 
                                    if (x % 2) == 0:
                                        idx = (x*grid_size) + y
                                        self.ser.write(b"y 0\n") # move in y after one scan
                                        self.df_scan['X: %d Y: %d' % (x, y)] = df_data_array

                                    else:
                                        idx = (x*grid_size) + grid_size - y -1
                                        self.ser.write(b"y 1\n")
                                        self.df_scan['X: %d Y: %d' % (x, grid_size-y-1)] = df_data_array
                                
                                self.button[idx].configure(bg = 'Green')
                                self.parent.update_idletasks()
                                self.progress_popup.update_idletasks()


                            self.ser.write(b"x 0\n")
                        
                        self.battery_check_flag = True
                        self.ser.write(b"home\n")
                        self.battery_check_flag = False
                        self.progress_popup.destroy()
                        plt.plot(self.wavelength, self.df_scan)
                        self.fig.canvas.draw()
                        self.df_scan.to_csv(self.scan_file, mode = 'w', index = False)
                        self.scan_file = None
                        end = time.time()
                        #print(end-start)
                        
                        # form the image from the acquired data
                        self.scan_image_window()
                        
                    self.progress_popup = Toplevel(self.parent, bg = 'sky blue')
                    self.progress_popup.focus_force()
                    self.progress_popup.geometry('450x450')
                    self.button = list(range(0,grid_size**2 +1))
                    
                    for x_button in range(0,grid_size):
                        for y_button in range(0, grid_size):
                            idx = (x_button*grid_size) + y_button
                            self.button[idx] = Button(self.progress_popup, bg = 'red', width = 1, height = 1)
                            self.button[idx].grid(row = 1+y_button, column = x_button, sticky = 'nsew')

                    start_button = Button(self.progress_popup, fg = 'black', command = scan_move,
                                          width = 5, height = 3, text = 'Scan')
                    start_button.grid(row = 0, column = 0, columnspan = grid_size)
                    
    
                    #self.progress_popup.rowconfigure(0, weight = 2)
                    self.progress_popup.columnconfigure(0, weight =1)
                    for i in range(1,grid_size+1):
                        self.progress_popup.rowconfigure(i, weight = 1)
                        self.progress_popup.columnconfigure(i-1, weight =1) 
                else:
                    messagebox.showerror('Error', 'No reference Saved, Save Reference before Scanning')
        else:
            messagebox.showerror('Error','Spectrometer Not Connected, Connect and Restart')
                
               
########### Module 2 Functions ########################
    def pump_prime(self):
        self.prime_pump_handler = not self.prime_pump_handler
        self.ser.write(b"prime_pump %d\n" %int(self.prime_pump_handler))
        
    def water_acquire(self, save):
        scan_message = None
        (self.settings, self.wavelength) = self.settings_func.settings_read()
        self.ser.write(b"pump_read\n")
        time.sleep(1)  #maybe some delay after the water spray
        data = self.acquire_avg(int(self.settings[1][1]))
        if data is not None:
            if save: 
                if self.save_file == None:
                    messagebox.showerror('Error', 'No Experiment File Found, create or open File to save Data')
                else:
                    # save data array to save_file
                    df_data_array = pd.DataFrame(data)
                    self.df['Scan_ID %d' %self.scan_number] = df_data_array
                    self.df.to_csv(self.save_file, mode = 'w', index = False)
                    data = self.df[['Scan_ID %d' %self.scan_number]]
                    self.scan_number = 1 + self.scan_number
                    scan_message = "Scan #: " + str(self.scan_number-1)    
            else: # temporary save
                np.savetxt(self.acquire_file, data, fmt="%d", delimiter=",")
                data = pd.read_csv(self.acquire_file, header = None)
                
            plt.clf()
            self.plotting(data, "Scan: " +str(self.scan_number-1))
        return scan_message
    
    def water_sequence(self, save):
        seq_message = None
        plt.clf()
        if self.ser.is_open:
            if save and self.save_file == None:
                messagebox.showerror('Error', 'No Experiment File Found, create or open File to save Data')
            (self.settings, self.wavelength) = self.settings_func.settings_read()       
            number_avg = int(self.settings[11][1])
            integ_time = int(self.settings[3][1])
            smoothing_used = int(self.settings[12][1])
            smoothing_width = int(self.settings[8][1])
            dark_subtract = int(self.settings[4][1])
            burst_number = int(self.settings[22][1])
            burst_delay = float(self.settings[21][1])
            
            plt.xlim(int(self.settings[9][1]), int(self.settings[10][1]))
            self.plot_labels_axis() # configure axis
            start = time.time()
            for burst in range(0,burst_number):
                number_measurements_burst = int(self.settings[23+burst][1])
                self.ser.write(b"pump_read\n")
                for i in range(0,number_measurements_burst):
                    graph_label = 'Burst ' + str(burst+1) + ' measurement ' + str(i+1)
                    pulses = int(self.settings[33+burst][1])
                    data = []
                    data = self.acquire_avg(pulses).reshape((288))
                    data = pd.DataFrame(data)
                    if self.ratio_view_handler:
                        data = (data/self.ref)*100
                    data = pd.DataFrame(data).to_numpy()
                    plt.plot(self.wavelength, data, label = graph_label)
                    plt.subplots_adjust(bottom = 0.14, right = 0.95)
                    plt.legend(loc = "center right", prop = {'size': 6})
                    
                    if save:
                        seq_message = "Scan: " + str(self.scan_number)
                        df_data_array = pd.DataFrame(data)
                        self.df['Scan_ID %d' % (self.scan_number)] = df_data_array
                        self.scan_number = self.scan_number +1
                    else:
                        seq_message = "Scan: Temp"
                time.sleep(burst_delay)
            end = time.time()
            print("seq Time: " + str(end-start))
           # after sequence complete save and plot
            if save:
                self.df.to_csv(self.save_file, mode = 'w', index = False)
            # after all data is taken save to sequence csv
            self.fig.canvas.draw()
        return seq_message