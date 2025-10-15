from tkinter import *
import tkinter.font as tkFont
import os

from debug_utils import (
    configure_logging,
    get_logger,
    log_class_methods,
    safe_repr,
)
class help_window_pop:
    def __init__(self, parent):
        configure_logging()
        self.logger = get_logger(f"{__name__}.help_window_pop")
        self.logger.debug("Initializing help window with parent=%s", safe_repr(parent))
        label_font = tkFont.Font(family = "Lucida Grande", size = 24)
        label_new = tkFont.Font(family = "Lucida Grande", size = 14)
        self.parent = parent
        self.version_file = "/home/pho512/Desktop/BMO_Lab/Gen-4_ESS/GUI/version.txt"
        self.logger.debug("Using version file at %s", self.version_file)
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
        self.logger.debug("Reading version information")
        try:
            with open(self.version_file) as file:
                version = str(file.readlines())
            # take away first and last characters for formating
            self.lines = "Version: " + str(version)
            self.logger.debug("Version content loaded: %s", safe_repr(self.lines, maxlen=120))
        except Exception:
            self.logger.exception("Failed to read version information from %s", self.version_file)
            self.lines = "Version: unavailable"
    
    def update(self):
        
        #os.system("cd ~")
        #try:
        #    os.system("cd /home/pho512/Desktop/BMO_Lab/Gen-4_ESS/GUI")
        #except:
        #    pass
        
        script = "/home/pho512/Desktop/BMO_Lab/Gen-4_ESS/GUI/version_detect_script.sh"
        self.logger.info("Running version update script: %s", script)
        os.system(f"sudo chmod u+x {script}")
        result = os.system(f"bash {script}")
        self.logger.debug("Version update script exited with code %s", result)


log_class_methods(
    help_window_pop,
    exclude={"__init__"},
    logger_name=f"{__name__}.help_window_pop",
    log_result=False,
)
        
