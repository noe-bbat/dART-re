"""
GridEYE Bluetooth Interface Module
================================

This module provides Bluetooth Low Energy (BLE) communication capabilities for the GridEYE thermal sensor.
It handles device connection, data acquisition, processing, and storage of thermal data.

The module implements a robust connection mechanism with automatic reconnection and data validation.
Temperature data is processed in real-time and can be saved to CSV files for further analysis.

Features:
    - Asynchronous BLE communication
    - Automatic reconnection on connection loss
    - Real-time temperature data processing
    - CSV data storage with multi-sensor support
    - Configurable device settings through external configuration
"""

import asyncio
from bleak import BleakClient
import struct
import numpy as np
from pathlib import Path
import logging
import threading
import pandas as pd
import time

Main_Path = Path(__file__).parent.resolve()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

HEADER = bytes.fromhex("2a2a2a")  # Fixed header to look for

class GridEYEConfigError(Exception):
    """
    Exception raised for configuration-related errors in GridEYE setup.
    
    This exception is raised when there are issues with loading or parsing
    configuration settings for the GridEYE sensor.
    """
    pass

class GridEYEConnectionError(Exception):
    """
    Exception raised for BLE connection-related errors.
    
    This exception is raised when there are issues establishing or maintaining
    the Bluetooth connection with the GridEYE sensor.
    """
    pass

class GridEYEDataProcessingError(Exception):
    """
    Exception raised for errors during data processing.
    
    This exception is raised when there are issues processing or parsing
    the data received from the GridEYE sensor.
    """
    pass

class GridEYEDataSavingError(Exception):
    """
    Exception raised for errors during data saving operations.
    
    This exception is raised when there are issues saving the collected
    data to CSV files or other storage operations.
    """
    pass

class GridEYEReader:
    """
    A class for reading and processing data from a GridEYE sensor via Bluetooth Low Energy.
    
    This class manages the BLE connection to a GridEYE sensor, handles data reception,
    processes temperature data, and provides storage capabilities. It supports multiple
    sensor configurations and implements automatic reconnection mechanisms.

    Attributes:
        instance_id: Identifier for multi-sensor setups
        config: Configuration dictionary loaded from external config
        csv_directory (Path): Directory for storing CSV files
        running (Event): Threading event for controlling the recording state
        temperatures (ndarray): 8x8 array of current temperature readings
        data_records (list): List of collected temperature records
    """

    def __init__(self, instance_id):
        """
        Initialize a new GridEYEReader instance.

        Args:
            instance_id: Unique identifier for the sensor instance in multi-sensor setups
        """
        self.ConfigClass = Conf.Config()
        self.config = self.ConfigClass.config
        
        self.instance_id = instance_id 
        self.init_bluetooth_config()
        
        self.csv_directory = Main_Path / self.config["directories"]["csv"]
        self.csv_filename = self.config["filenames"]["Grideye"]
        self.csv_path = self.csv_directory / self.csv_filename
        
        self.running = threading.Event()
        self.stop_event = asyncio.Event()
        self.thread = None
        
        self.buffer = bytearray() 
        self.temperatures = np.zeros((8, 8), dtype=np.float32)
        self.latest_successful_read = time.time()
        self.data_records = []
       
        self.client = None

    def init_bluetooth_config(self):
        """
        Initialize Bluetooth configuration for the GridEYE sensor.
        
        Loads and sets up Bluetooth-specific configuration parameters including
        device address and UUID values from the configuration file.

        Raises:
            GridEYEConfigError: If there's an error loading or parsing Bluetooth configuration
        """
        try:
            device = self.grideye_uuid_name()
            bluetooth_config = self.ConfigClass.get_grideye_uuid(device)
            if bluetooth_config:
                self.DEVICE_ADDRESS = bluetooth_config['DEVICE_ADDRESS']
                self.SERVICE_UUID = bluetooth_config['SERVICE_UUID']
                self.CHARACTERISTIC_UUID = bluetooth_config['CHARACTERISTIC_UUID']
            else:
                raise GridEYEConfigError("Bluetooth configuration for GridEYE not found")
        except Exception as e:
            raise GridEYEConfigError(f"Error in Bluetooth configuration: {str(e)}")
            
    def grideye_uuid_name(self):
        """
        Generate the device name for UUID configuration.

        Returns:
            str: Device name formatted according to multi-sensor configuration
        """
        return "Grideye_{self.instance_id}" if self.ConfigClass.get_sensor_amount("Grideye") > 1 else "Grideye"
    
    def start_recording(self):
        """
        Start recording data from the GridEYE sensor.
        
        Initializes and starts a new thread for BLE communication if not already running.
        The thread will handle connection establishment and data reception.

        Raises:
            GridEYEConnectionError: If there's an error starting the recording process
        """
        try:
            if not self.running.is_set():
                self.running.set()
                self.stop_event.clear()
                self.thread = threading.Thread(target=self.run_ble_client_thread)
                self.thread.start()
                logging.info("Started GridEYE recording.")
        except Exception as e:
            raise GridEYEConnectionError(f"Error in starting GridEYE recording: {str(e)}")

    def stop_recording(self):
        """
        Stop recording data from the GridEYE sensor.
        
        Stops the BLE communication thread and ensures all collected data is saved to CSV.
        Performs cleanup of connections and threads.

        Raises:
            GridEYEConnectionError: If there's an error stopping the recording process
        """
        try:
            if self.running.is_set():
                self.send_data_to_csv()
                self.running.clear()
                self.stop_event.set()
                
                if self.thread:
                    self.thread.join(timeout=10)
                
                logging.info("Stopped GridEYE recording.")
                
        except Exception as e:
            raise GridEYEConnectionError(f"Error in stopping GridEYE recording: {str(e)}")

    async def run_ble_client(self):
        """
        Asynchronous method to run the BLE client and handle data reception.
        
        Manages the BLE connection lifecycle including connection establishment,
        data notification setup, and automatic reconnection on connection loss.
        Implements a watchdog timer to detect connection issues.
        """
        def notification_handler(sender, data):
            self.process_data(data)
            self.latest_successful_read = time.time()

        while self.running.is_set() and not self.stop_event.is_set():
            try:
                async with BleakClient(self.DEVICE_ADDRESS, timeout=4) as client:
                    self.client = client
                    logging.info(f"Connected to {self.DEVICE_ADDRESS}")
                    await client.start_notify(self.CHARACTERISTIC_UUID, notification_handler)

                    while self.running.is_set() and not self.stop_event.is_set():
                        await asyncio.sleep(1)
                        if time.time() - self.latest_successful_read > 7:
                            logging.info("No data received for 7 seconds. Reconnecting...")
                            break

                    try:
                        await client.stop_notify(self.CHARACTERISTIC_UUID)
                    except Exception as e:
                        logging.error(f"Error stopping notifications: {e}")

            except asyncio.CancelledError:
                logging.info("BLE client task cancelled.")
                break
            except Exception as e:
                logging.error(f"Error in BLE connection: {e}")
                if not self.running.is_set() or self.stop_event.is_set():
                    break
                await asyncio.sleep(5)

        self.client = None
        logging.info("BLE client loop ended.")

    def run_ble_client_thread(self):
        """
        Run the BLE client in a separate thread.
        
        Creates a new event loop for the BLE client to run asynchronously.
        Handles the lifecycle of the asyncio event loop.
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_ble_client())
        except Exception as e:
            logging.error(f"Error in BLE client thread: {e}")
        finally:
            try:
                loop.close()
            except Exception as e:
                logging.error(f"Error closing event loop: {e}")
                
    def process_data(self, data):
        """
        Process the received data from the GridEYE sensor.
        
        Parses the received data buffer and extracts valid temperature frames.
        Handles data validation and frame extraction.

        Args:
            data: Raw data received from the GridEYE sensor

        Raises:
            GridEYEDataProcessingError: If there's an error processing the data
        """
        try:
            self.buffer.extend(data)
            while True:
                header_index = self.buffer.find(HEADER)
                if header_index == -1:
                    break

                frame_start = header_index + len(HEADER) + 2
                if len(self.buffer) - frame_start < 128:
                    break

                frame_data = self.buffer[frame_start:frame_start + 128]
                
                end_marker = self.buffer[frame_start + 128:frame_start + 130]
                if end_marker == bytes.fromhex("0d0a"):
                    self.parse_frame(frame_data)
                    self.add_data_record()

                self.buffer = self.buffer[frame_start + 128 + 2:]
        except Exception as e:
            raise GridEYEDataProcessingError(f"Error in processing GridEYE data: {str(e)}")

    def parse_frame(self, frame_data):
        """
        Parse a single frame of temperature data.
        
        Converts raw frame data into a temperature matrix using the
        specified conversion factor (0.25°C per unit).

        Args:
            frame_data: Raw frame data containing temperature values
        """
        for i in range(8):
            for j in range(8):
                index = (i * 8 + j) * 2
                raw_temp = frame_data[index:index + 2]
                temp = struct.unpack('<h', raw_temp)[0]
                celsius_temp = round(temp * 0.25,3)
                self.temperatures[i][j] = celsius_temp
        self.display_temperatures()

    def display_temperatures(self):
        """
        Display the current temperature matrix for debugging purposes.
        
        Logs the complete temperature matrix and corner temperatures
        for monitoring and debugging.
        """
        logging.debug("\nTemperatures (°C):")
        for i, row in enumerate(self.temperatures):
            logging.debug(f"Row {i}: " + " ".join(f"{temp:6.2f}" for temp in row))
        logging.debug("\nCorner temperatures:")
        logging.debug(f"Top-left: {self.temperatures[0, 0]:6.2f}  Top-right: {self.temperatures[0, 7]:6.2f}")
        logging.debug(f"Bottom-left: {self.temperatures[7, 0]:6.2f}  Bottom-right: {self.temperatures[7, 7]:6.2f}")

    def add_data_record(self):
        """
        Add a new data record to the collection.
        
        Creates a record containing the current timestamp and temperature
        matrix for later storage.
        """
        record = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'temperatures': self.temperatures.flatten().tolist()
        }
        self.data_records.append(record)

    def send_data_to_csv(self):
        """
        Save collected data records to a CSV file.
        
        Handles file naming for multi-sensor configurations and saves
        all collected records to a CSV file.

        Raises:
            GridEYEDataSavingError: If there's an error saving the data to CSV
        """
        if not self.data_records:
            logging.warning("No data to save")
            return

        try:
            df = pd.DataFrame(self.data_records)
            base_filename = self.csv_filename[:-4]
            sensor_amount = self.ConfigClass.get_sensor_amount("Grideye")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.csv_filename
                
            new_filepath = self.csv_directory / new_filename
            df.to_csv(new_filepath, index=False)
            logging.info(f"Data saved to {new_filename}")
            self.data_records.clear()
        except Exception as e:
            raise GridEYEDataSavingError(f"Error in saving GridEYE data to CSV: {str(e)}")