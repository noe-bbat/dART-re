"""
GridEYE Kit Interface
====================

Serial interface for GridEYE thermal sensor. Handles data acquisition, 
processing and storage operations.
"""

import sys
from webbrowser import Error
import serial
from serial import Serial, SerialException
import struct
import numpy as np
import threading
from queue import Queue
import glob
import time 
from datetime import datetime
import pandas as pd
import config.configuration as Conf
import os
import logging
from pathlib import Path
import threading

sys.path.append(str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

class GridEYEError(Exception):
    """Base exception for GridEYE operations."""
    pass

class ConnectionError(GridEYEError):
    """Connection-related errors."""
    pass

class DataReadError(GridEYEError):
    """Data reading operation errors."""
    pass

class GridEYEKit:
    """
    Main interface for GridEYE sensor operations.
    Manages serial connection and data handling.
    """

    def __init__(self, port, wifi_transmitter):
        """
        Initialize GridEYEKit instance.

        Args:
            port: Serial port identifier
            wifi_transmitter: WiFi transmission object
        
        Raises:
            GridEYEError: On initialization failure
        """
        try:
            self.port = port
            self.wifi_transmitter = wifi_transmitter
            
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            self.csv_directory = Main_path / self.config["directories"]["csv"]
            self.csv_filename = self.config["filenames"]["Grideye"]
            self.csv_path = self.csv_directory / self.csv_filename

            self.ser = None
            self.data_records = []
            self.multiplier_tarr = 0.25
            self.multiplier_th = 0.0125
            
            self.instance_id = 1
            
            self.is_connected = False
            self.connection_error = False
            self.last_successful_read = time.time()

            self.data_thread = None
            self.stop_thread = threading.Event()
        except Exception as e: 
            logging.error(f"Error initializing GridEYEKit: {e}")
            raise GridEYEError("Failed to initialize GridEYEKit")

    def connect(self):
        """
        Establish serial connection.

        Returns:
            bool: Connection success status
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=0.5,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            logging.info(f"Connected to port {self.port}")
            self.is_connected = True
            return True
        except serial.SerialException as e:
            logging.error(f"Error connecting to port {self.port}: {e}")
            self.connection_error = True
            return False

    def disconnect(self):
        """
        Close serial connection and save data.

        Returns:
            bool: Disconnection success status
        """
        try:
            if self.is_connected:
                self.send_data_to_csv()
                if self.ser and self.ser.is_open:
                    self.ser.flush()
                    self.ser.close()
                    self.is_connected = False
                logging.info("Disconnected from serial port")
                return True
            else :
                logging.info("Already disconnected")
                self.connection_error = True
                return False
        except (serial.SerialException, Exception) as e:
            self.connection_error = True
            logging.error(f"Error disconnecting from port {self.port}: {e}") if SerialException else logging.error(f"Error disconnecting: {e}")
            return False

    def check_connection(self):
        """
        Verify connection status.

        Returns:
            bool: True if connection is active
        """
        try:
            if not self.ser or not self.ser.is_open:
                self.connection_error = True
                logging.error("Serial port is not open")
                return False  
            
            if time.time() - self.last_successful_read > 5:
                self.connection_error = True
                logging.error("No data received for 5 seconds")
                return False  
        except serial.SerialException as e:
            self.connection_error = True
            logging.error(f"Serial port error: {e}")
            return False
        
        return True

    def get_data(self):
        """
        Read sensor data.

        Returns:
            dict: Processed data or None on error
        """
        if not self.check_connection():
            return None
        
        try:
            data = self.serial_readline()
            if len(data) >= 135:
                self.last_successful_read = time.time()
                self.connection_error = False
                thermistor, tarr = self._process_data(data)
                return {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'thermistor': thermistor,
                    'temperatures': tarr.flatten().tolist()
                }
            else:
                logging.warning(f"Incomplete data received: {len(data)} bytes")
                return None
        except serial.SerialException as e:
            self.connection_error = True
            logging.error(f"Serial read error: {e}")
            return None
        except struct.error as e:
            logging.error(f"Data decoding error: {e}")
            return None
    
    def get_latest_data(self):
        """
        Retrieve most recent data record.

        Returns:
            dict: Latest data or None if empty
        """
        try:
            if self.data_records:
                logging.info(f"Latest data: {self.data_records[-1]}")
                return self.data_records[-1]
            return None 
        except Exception as e:
            logging.error(f"Error getting latest data: {e}")

    def _process_data(self, data):
        """
        Process raw sensor data.

        Args:
            data: Raw sensor data

        Returns:
            tuple: (thermistor_value, temperature_array)
        """
        tarr = np.zeros((8, 8))
        try : 
            if data[1] & 0b00001000 != 0:
                data[1] &= 0b00000111
                thermistor = -struct.unpack('<h', data[0:2])[0] * self.multiplier_th
            else:
                thermistor = struct.unpack('<h', data[0:2])[0] * self.multiplier_th

            for i in range(2, 130, 2):
                raw_temp = data[i:i+2]
                temp_value = struct.unpack('<h', raw_temp)[0]
                temperature = temp_value * self.multiplier_tarr

                row = (i - 2) // 16
                col = ((i - 2) // 2) % 8
                tarr[row, col] = temperature

            return thermistor, tarr
        except Exception as e:
            logging.error(f"Error processing data: {e}")
            return None, None

    def serial_readline(self, eol='***', bytes_timeout=300):
        """
        Read serial data until EOL marker.

        Args:
            eol: End of line marker
            bytes_timeout: Maximum bytes to read

        Returns:
            bytearray: Read data
        """
        length = len(eol)
        line = bytearray()
        try:
            while True:
                c = self.ser.read(1)
                if c:
                    line += c
                    if line[-length:] == eol.encode():
                        break
                    if len(line) > bytes_timeout:
                        return line
                else:
                    break

            return line
        except serial.SerialException as e:
            logging.error(f"Serial read error: {e}")
            return line
    
    def start_recording(self):
        """
        Begin data recording session.

        Raises:
            ConnectionError: If device not connected
        """
        try:
            if not self.is_connected:
                self.connection_error = True
                raise ConnectionError("Device is not connected")
            
            self.is_recording = True
            self.stop_thread.clear()
            self.data_thread = threading.Thread(target=self.update_data)
            self.data_thread.start()
            logging.info("Started recording GridEYE data")
        except ConnectionError as e:
            logging.error(f"Error starting recording: {e}")
            raise ConnectionError("Failed to start recording")
        
    def stop_recording(self):
        """Stop recording and disconnect device."""
        self.is_recording = False
        if self.data_thread:
            self.stop_thread.set()
            self.data_thread.join()
        if self.is_connected:
            self.disconnect()
        logging.info("Stopped recording GridEYE data")

    def update_data(self):
        """Continuous data collection thread."""
        while not self.stop_thread.is_set() and self.is_recording:
            if not self.check_connection():
                time.sleep(1)  
                continue

            try:
                data = self.get_data()
                if data:
                    self.data_records.append(data)
                    if self.wifi_transmitter:
                        self.wifi_transmitter.update(self.get_latest_data())
                time.sleep(0.1)  
            except Exception as e:
                logging.error(f"Error collecting data: {e}")
                self.connection_error = True
                time.sleep(1)  
            
    def send_data_to_csv(self):
        """Save collected data to CSV file."""
        if not self.data_records:
            logging.warning("No data to save")
            return

        records = []
        for record in self.data_records:
            row = {'timestamp': record['timestamp'], 'thermistor': record['thermistor']}
            for i, temp in enumerate(record['temperatures']):
                row[f'temp-{i+1}'] = temp
            records.append(row)

        df = pd.DataFrame(records)
        try:
            base_filename = self.csv_filename[:-4]
            sensor_amount = self.configClass.get_sensor_amount("Grideye")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.csv_filename
                
            new_filepath = self.csv_directory / new_filename
            df.to_csv(new_filepath, index=False)
            print(f"Data saved to {new_filename}")
            self.data_records.clear()
        except IOError as e:
            print(f"Error writing data to CSV file: {e}")
            print(self.csv_directory, new_filepath)
            
    def run_session(self):
        """
        Execute complete recording session.

        Raises:
            ConnectionError: On connection failure
        """
        if not self.connect():
            raise ConnectionError("Failed to connect to the device")

        try:
            self.start_recording()
            self.record_data()
        except KeyboardInterrupt:
            logging.info("Recording interrupted by user")
        finally:
            self.stop_recording()
            self.send_data_to_csv()
            self.disconnect()