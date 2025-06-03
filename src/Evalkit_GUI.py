#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GridEYE Viewer Application
=========================

This module implements a graphical interface to visualize GridEYE sensor data.
It provides real-time temperature visualization using a color-coded 8x8 grid.

The application allows users to:
    - Start/Stop real-time temperature monitoring
    - Set maximum and minimum temperature thresholds
    - View temperature values in a color-coded grid
    - Automatically scale colors based on temperature range
"""

import tkinter as tk
from tkinter import messagebox
import colorsys
import sys
from pathlib import Path
import logging
import threading
import queue
import config.configuration as conf
import time 

sys.path.append(str(Path(__file__).parent))
from GridEyeKit import GridEYEKit, GridEYEError, ConnectionError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_Path = Path(__file__).parents[0]

class GridEYE_Viewer:
    """
    A class that implements the graphical interface for visualizing GridEYE thermal data.

    This class creates a window with an 8x8 grid of colored labels representing
    temperature values from the GridEYE sensor. It includes controls for starting/stopping
    the data acquisition and setting temperature range limits.

    Attributes:
        ConfigClass (Config): Configuration object for device settings
        config (dict): Configuration dictionary
        HUEstart (float): Starting value for color HUE mapping (0.5 = cyan)
        HUEend (float): Ending value for color HUE mapping (1.0 = red)
        HUEspan (float): Range of HUE values used for temperature mapping
        MULTIPLIER (float): Scaling factor for temperature values
        START (bool): Flag indicating if temperature monitoring is active
        connection_error (bool): Flag indicating connection status
    """

    def __init__(self, root):
        """
        Initialize the GridEYE viewer interface.

        Args:
            root (tk.Tk): Root window instance for the application

        Raises:
            GridEYEError: If initialization of the GridEYE kit fails
        """
        self.ConfigClass = conf.Config()
        self.config = self.ConfigClass.config
        
        self.tkroot = root
        self.tkroot.protocol('WM_DELETE_WINDOW', self.exitwindow)

        self.HUEstart = 0.5
        self.HUEend = 1
        self.HUEspan = self.HUEend - self.HUEstart
        
        self.MULTIPLIER = 0.25
        
        self.START = False
        self.connection_error = False
         
        
        self.setup_ui()
        
        try:
            self.kit = GridEYEKit(self.ConfigClass.get_device_port("Grideye"))
        except GridEYEError as e:
            messagebox.showerror("Initialization Error", str(e))
            self.tkroot.destroy()
            return

    def setup_ui(self):
        """
        Set up the user interface components.

        Creates:
            - 8x8 grid of temperature display labels
            - Start/Stop buttons
            - Temperature range control sliders
        """
        self.frameTarr = tk.Frame(master=self.tkroot, bg='white')
        self.frameTarr.place(x=5, y=5, width=400, height=400)
        
        self.tarrpixels = []
        for i in range(8):
            for j in range(8):
                pix = tk.Label(master=self.frameTarr, bg='gray', text='11')
                spacerx = spacery = 1
                pixwidth = pixheight = 40
                pix.place(x=spacerx+j*(spacerx+pixwidth), y=spacery+i*(pixheight+spacery), width=pixwidth, height=pixheight)
                self.tarrpixels.append(pix)
    
        self.frameElements = tk.Frame(master=self.tkroot, bg='white')
        self.frameElements.place(x=410, y=5, width=100, height=400)
        
        self.buttonStart = tk.Button(master=self.frameElements, text='start', bg='white', command=self.start_update)
        self.buttonStart.pack()
        self.buttonStop = tk.Button(master=self.frameElements, text='stop', bg='white', command=self.stop_update)
        self.buttonStop.pack()
        
        self.lableTEMPMAX = tk.Label(master=self.frameElements, text='Max Temp (red)')
        self.lableTEMPMAX.pack()
        self.MAXTEMP = tk.Scale(self.frameElements, from_=-20, to=120, resolution=0.25)
        self.MAXTEMP.set(31)
        self.MAXTEMP.pack()
        self.lableMINTEMP = tk.Label(master=self.frameElements, text='Min Temp (blue)')
        self.lableMINTEMP.pack()
        self.MINTEMP = tk.Scale(self.frameElements, from_=-20, to=120, resolution=0.25)
        self.MINTEMP.set(27)
        self.MINTEMP.pack()

    def exitwindow(self):
        """
        Handle application exit.

        Stops data updates and disconnects from the GridEYE device before
        destroying the main window.
        """
        try:
            self.stop_update()
            if self.kit and self.kit.is_connected:
                self.kit.disconnect()
        except Exception as e:
            logging.error(f"Error during exit: {e}")
        finally:
            self.tkroot.destroy()
        
    def stop_update(self):
        """
        Stop the real-time temperature updates.

        Sets the START flag to False, which will stop the update loop
        in update_tarrpixels().
        """
        self.START = False
        logging.info("Stopped updating")

    def start_update(self):
        """
        Start real-time temperature updates.

        Attempts to connect to the GridEYE device and starts the update loop
        if successful.

        Raises:
            ConnectionError: If connection to the GridEYE device fails
        """
        try:
            if not self.kit.connect():
                raise ConnectionError("Could not connect to Grid-EYE Eval Kit")
            
            self.START = True
            self.connection_error = False
            self.update_tarrpixels()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            logging.error(f"Error starting update: {e}")
    
    def update_tarrpixels(self):
        """
        Update the temperature display pixels.

        Fetches new temperature data from the GridEYE device and updates
        the display if monitoring is active. Runs every 100ms while START
        is True.
        """
        if self.START and not self.connection_error:
            try:
                data = self.kit.get_data()
                if data:
                    self.update_pixels(data['temperatures'])
                    self.kit.data_records.append(data)
            except Exception as e:
                logging.error(f"Error in update_tarrpixels: {e}")
                self.connection_error = True
            finally:
                if self.START:
                    self.frameTarr.after(100, self.update_tarrpixels)
    
    def update_pixels(self, tarr):
        """
        Update individual pixel displays with new temperature values.

        Args:
            tarr (list): List of 64 temperature values corresponding to the 8x8 grid
        """
        if len(tarr) == len(self.tarrpixels):
            for i, (tarrpix, temp) in enumerate(zip(self.tarrpixels, tarr)):
                tarrpix.config(text=f"{temp:.2f}")
                normtemp = self.normalize_temperature(temp)
                color = self.get_color_for_temperature(normtemp)
                tarrpix.config(bg=color)
        else:
            logging.error("Error - temperature array length wrong")

    def normalize_temperature(self, temp):
        """
        Normalize a temperature value to a 0-1 range based on min/max settings.

        Args:
            temp (float): Temperature value to normalize

        Returns:
            float: Normalized temperature value between 0 and 1
        """
        if temp < self.MINTEMP.get():
            return 0
        elif temp > self.MAXTEMP.get():
            return 1
        else:
            temp_span = max(self.MAXTEMP.get() - self.MINTEMP.get(), 1)
            return (float(temp) - self.MINTEMP.get()) / temp_span

    def get_color_for_temperature(self, normtemp):
        """
        Convert a normalized temperature value to an RGB color.

        Args:
            normtemp (float): Normalized temperature value (0-1)

        Returns:
            str: Color in hexadecimal format (#RRGGBB)
        """
        h = max(0, min(1, normtemp * self.HUEspan + self.HUEstart))
        rgb = colorsys.hsv_to_rgb(h, 1, 1)
        bgrgb = tuple(int(255 * j) for j in rgb)
        return '#%02x%02x%02x' % bgrgb

if __name__ == "__main__":
    root = tk.Tk()
    root.title('Grid-Eye Viewer')
    root.geometry('500x450')
    try:
        Window = GridEYE_Viewer(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"Error in main: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")