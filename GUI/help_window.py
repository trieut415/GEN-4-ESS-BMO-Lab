from tkinter import *
import tkinter.font as tkFont
import os
class help_window_pop:
    def __init__(self, parent):
        label_font = tkFont.Font(family = "Lucida Grande", size = 24)
        label_new = tkFont.Font(family = "Lucida Grande", size = 14)
        self.parent = parent
        self.version_file = "/home/pi/Desktop/BMO_Lab/Gen-4_ESS/GUI/version.txt"
        self.help_window_popup = Toplevel(self.parent, bg = "sky blue")
        #self.help_window_popup.attributes('-fullscreen', True)
        self.read_version()
        lbl = Label(self.help_window_popup, text = self.lines,
                    bg = "sky blue", font = label_font)
        lbl.pack()
        
        #lbl_version = "(Hardware).(PCB).(GUI).(Arduino).(Date)"
        #lbl_new = Label(self.help_window_popup, text = lbl_version,
        #            bg = "sky blue", font = label_new)
        #lbl_new.pack()
        
        btn = Button(self.help_window_popup, text = "UPDATE",
                     font = label_new)
        btn.pack()
        
    def read_version(self):
        with open(self.version_file) as file:
            version = str(file.readlines())
        # take away first and last characters for formating
        self.lines = "Version: " + str(version)
    
    def update(self):
        
        #os.system("cd ~")
        #try:
        #    os.system("cd /home/pi/Desktop/BMO_Lab/Gen-4_ESS/GUI")
        #except:
        #    pass
        
        os.system("sudo chmod u+x /home/pi/Desktop/BMO_Lab/Gen-4_ESS/GUI/version_detect_script.sh")
        
        os.system("bash /home/pi/Desktop/BMO_Lab/Gen-4_ESS/GUI/version_detect_script.sh")
        
