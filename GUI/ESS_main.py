import serial
from time import sleep
from ESS_GUI_module_0 import *
from ESS_GUI_module_1 import *
from ESS_GUI_module_2 import *
from ESS_GUI_module_3 import *
from ESS_GUI_module_4 import *
from ESS_GUI_module_5 import *
from ESS_GUI_module_6 import *
from ESS_GUI_module_7 import *

import matplotlib.pyplot as plt
from tkinter import *
from tkinter import messagebox
import tkinter.font as tkfont

from debug_utils import (
    SerialDebugWrapper,
    configure_logging,
    get_logger,
    log_call,
    summarize_bytes,
)


configure_logging()
logger = get_logger(__name__)

# error popup box
def spectrometer_disconnect():
    logger.warning("Spectrometer disconnect handler triggered")
    root = Tk()
    root.geometry('800x480')
    root.title("ESS System Interface")
    root.configure(bg = 'sky blue')
    message = Label(root, text = 'Spectrometer Not connected, Connect and try again', bg = 'sky blue', anchor = "center").pack()
    quit_button = Button(root, text = 'QUIT', command = root.destroy, fg = 'red').pack()

@log_call(logger_name=__name__)
def run_program():
    sleep(2.5) # wait for a little to initialize serial connection

    payload = b"module\n"
    logger.debug("Requesting module identifier over serial: %s", summarize_bytes(payload))
    ser.write(payload)
    logger.debug("Serial write complete, awaiting module response")
#     module = int(ser.readline().decode()) # read in the module number
    module = 0
    logger.debug("Module identifier resolved to %s", module)
    root = Tk()
    

    if module == 0:
        logger.info("Launching Module_0 GUI")
        app = Module_0(root)
        
    elif module == 1:
        logger.info("Launching Module_1 GUI")
        app = Module_1(root)

    elif module == 2:
        logger.info("Launching Module_2 GUI")
        app = Module_2(root)
        
    elif module == 3:
        logger.info("Launching Module_3 GUI")
        app = Module_3(root)
        
    elif module == 4:
        logger.info("Launching Module_4 GUI")
        app = Module_4(root)
        
    elif module == 5:
        logger.info("Launching Module_5 GUI")
        app = Module_5(root)
        
    elif module == 6:
        logger.info("Launching Module_6 GUI")
        app = Module_6(root)
        
    elif module == 7:
        logger.info("Launching Module_7 GUI")
        app = Module_7(root)
    else:
        logger.error("Unknown module identifier %s", module)
        raise ValueError(f"Unsupported module {module}")
    
    logger.debug("Entering Tk mainloop")
    root.mainloop()
    logger.debug("Tk mainloop exited")
    
# open up a serial to allow for reading in of module attachment
port_candidates = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
ser = None

for candidate in port_candidates:
    try:
        logger.info("Attempting to open serial port %s", candidate)
        raw_serial = serial.Serial(candidate, baudrate=115200, timeout=3)
        ser = SerialDebugWrapper(raw_serial, logger=logger, name="ESS_main.ser")
        logger.info("Serial port opened successfully on %s", candidate)
        break
    except serial.serialutil.SerialException as exc:
        logger.warning("Serial port %s unavailable: %s", candidate, exc)
    except Exception as exc:
        logger.exception("Unexpected error opening serial port %s", candidate)

if ser is None:
    logger.error("Unable to initialize serial connection after trying %s", port_candidates)
    spectrometer_disconnect()
else:
    try:
        run_program()
    except Exception:
        logger.exception("run_program raised an exception")
        raise

 
