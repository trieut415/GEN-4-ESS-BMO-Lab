from settings import Settings as _Settings
import csv
from tkinter import *
import tkinter.font as tkfont

from debug_utils import (
    configure_logging,
    get_logger,
    log_class_methods,
    safe_repr,
)
########## Global Variables ##################
global settings_file

settings_file = '/home/pho512/Desktop/Spectrometer/settings/settings.csv'



class Num_Pad:
    def __init__(self, parent, button_number):
        global number_save
        global settings_file
        configure_logging()
        self.logger = get_logger(f"{__name__}.Num_Pad")
        self.logger.debug("Initializing Num_Pad with parent=%s button_number=%s", safe_repr(parent), button_number)
        self.settings_file = settings_file
        self.numpad = parent
        #number pad attributes
        num = StringVar()  # variable for extracting entry number
        
        self.numpad.title('Input pad')
        numpad_size = '330x450'
        self.numpad.geometry(numpad_size)

        number_entry = Entry(self.numpad, textvariable = num, justify = CENTER).grid(row = 0, column = 0, columnspan = 3, sticky = 'ew')
        self.numpad.grid_columnconfigure((0,1,2), weight = 1)
        self.numpad.grid_rowconfigure((0,1,2,3,4), weight = 1)
       
        def button_click(number):
            self.logger.debug("Button clicked: %s", number)
            global current
            current = num.get() # save current entry value
            num.set('') # erase entry
            current = str(current) + str(number)
            num.set(current) # rewrite entry with additional values 
    
        def num_pad_delete():
            self.logger.debug("Clearing current entry")
            num.set('') # erase current entry

        def backspace():
            global current
            current = current[:-1] # Remove last digit
            num.set(current)
            self.logger.debug("Backspace applied; current=%s", num.get())

        def num_pad_save(button_number):
            global number_save
            try:
                self.logger.debug("Saving value for button %s", button_number)
                settings_open = open(self.settings_file, 'r')
                csv_reader = csv.reader(settings_open, delimiter=',')
                settings = list(csv_reader)
                
                # read in settings to particular button ID on settings page
                # arbitrary number depending on location in CSV file
                if button_number<15 or button_number>21:
                    if button_number == 1 and int(num.get()) == 0:
                        settings[3][1] = 40
                    elif button_number == 1 and int(num.get()) != 0:
                        #calculate integ time 
                        settings[3][1] = 40 + (int(settings[1][1]) - 1)*(1000000/int(settings[2][1]))
                        
                    settings[button_number][1]  = int(num.get())
                else:
                    settings[button_number][1]  = float(num.get())
                #write settings to csv file
                settings_open = open(self.settings_file, 'w')
                with settings_open:
                    csv_writer = csv.writer(settings_open, delimiter = ',')
                    csv_writer.writerows(settings)

                self.numpad.destroy()
                self.logger.debug("Number pad value saved and window closed")



            # if value or type of returned value isnt an int or float then raise error
            except ValueError or TypeError:
                self.logger.exception("Invalid numeric input provided")
                error_top = Toplevel(self.numpad)
                message = Label(error_top, text = "Input must be a valid integer or float", font = tkfont.Font(family = "Helvetica", weight = "bold", size = 15), wraplength = 300)
                message.grid(row = 0, column = 0, padx = 10)
                quit_button = Button(error_top, text = "OK", fg = 'red', command = self.numpad.destroy, font = tkfont.Font(size = 15))
                quit_button.grid(row = 1, column = 0, padx = 4, pady = 4)
                
                error_top.after(5000, self.numpad.destroy)
                #messagebox.showerror("Error", "Input must be a valid integer or float", parent =self.numpad)
                #self.numpad.destroy()

        btn_list = [
        '7', '8', '9',
        '4', '5', '6',
        '1', '2', '3',
        '0', 'Del', 'OK']

        r = 1
        c = 0
        n = 0

        btn = list(range(len(btn_list)+2))
        for label in btn_list:
            btn[n] = Button(self.numpad, text = label, height = 3, width = 3)
            btn[n].grid(row = r, column = c, sticky = 'nsew')
            n+= 1
            c+= 1
            if c>2:
                c = 0
                r+= 1
        if button_number>14:
            if button_number<22:
                # for buttons that require decimal places
                btn[12] = Button(self.numpad, text = '.', height = 3, width = 3)
                btn[12].grid(row = 6, column = 0, sticky = 'nsew')
                btn[13] = Button(self.numpad, text = 'Backspace', height = 3, width = 3)
                btn[13].grid(row = 6, column = 1, columnspan = 2, sticky = 'nsew')
                btn[12].configure(command = lambda: button_click('.'))
                btn[13].configure(command = backspace)
        else:
            pass
        # atttach a number or func to each button
        btn[0].configure(command = lambda: button_click(7))
        btn[1].configure(command = lambda: button_click(8))
        btn[2].configure(command = lambda: button_click(9))
        btn[3].configure(command = lambda: button_click(4))
        btn[4].configure(command = lambda: button_click(5))
        btn[5].configure(command = lambda: button_click(6))
        btn[6].configure(command = lambda: button_click(1))
        btn[7].configure(command = lambda: button_click(2))
        btn[8].configure(command = lambda: button_click(3))
        btn[9].configure(command = lambda: button_click(0))
        btn[10].configure(command = num_pad_delete)
        btn[11].configure(command = lambda: num_pad_save(button_number))


log_class_methods(
    Num_Pad,
    exclude={"__init__"},
    logger_name=f"{__name__}.Num_Pad",
    log_result=False,
)

        
        
