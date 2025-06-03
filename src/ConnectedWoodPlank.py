"""
Connected Wood Plank Module
==========================

This module provides a comprehensive interface for managing and recording data from a Connected Wood Plank device.
The device incorporates multiple sensor types:
    - 16 capacitive sensors
    - 4 strain gauge sensors
    - 4 piezoelectric sensors

The module handles Bluetooth Low Energy (BLE) communication, real-time data collection,
and persistent storage of sensor readings in CSV format.
"""

import asyncio
import struct
from bleak import BleakScanner, BleakClient
from datetime import datetime
import logging
from pathlib import Path
import threading 
import pandas as pd 

Main_Path = Path(__file__).parent.resolve()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

class ConnectedWoodPlankError(Exception):
    """
    Custom exception for Connected Wood Plank operations.
    Raised when device initialization, data collection, or storage operations fail.
    """
    pass

class ConnectedWoodPlank:
    """
    A comprehensive manager for Connected Wood Plank devices.

    This class handles:
        - BLE device discovery and connection
        - Real-time data collection from multiple sensor types
        - Data parsing and temporary storage
        - CSV file export
        - Multi-instance support for multiple devices

    Attributes:
        NUM_CAPACITIVE (int): Number of capacitive sensors (16)
        NUM_STRAIN (int): Number of strain gauge sensors (4)
        NUM_PIEZO (int): Number of piezoelectric sensors (4)
        instance_id: Unique identifier for multi-device setups
        wifi_transmitter: Object handling WiFi communication
        recording (bool): Current recording status
    """

    def __init__(self, instance_id, wifi_transmitter):
        """
        Initialize a Connected Wood Plank manager.

        Args:
            instance_id: Unique identifier for multi-device configurations
            wifi_transmitter: Object for WiFi data transmission

        Raises:
            ConnectedWoodPlankError: If initialization fails
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config
            
            self.NUM_CAPACITIVE = 16
            self.NUM_STRAIN = 4
            self.NUM_PIEZO = 4
            
            self.wifi_transmitter = wifi_transmitter
            self.instance_id = instance_id
            
            self.capacitive_data = {f"capacitive_{i}": [] for i in range(self.NUM_CAPACITIVE)}
            self.strain_data = {f"strain_{i}": [] for i in range(self.NUM_STRAIN)}
            self.piezo_data = {f"piezo_{i}": [] for i in range(self.NUM_PIEZO)}
            
            self.DIRECTORY = Main_Path / self.config['directories']['csv']
            
            self.get_connected_wood_plank_uuid()
            
            self.recording = False
            self.recording_thread = None
            self.stop_event = threading.Event()
            
        except Exception as e:
            logging.error(f"Error initializing ConnectedWoodPlank: {str(e)}")
            raise ConnectedWoodPlankError("CWP initialization error")

    def get_connected_wood_plank_uuid(self):
        """
        Retrieve device UUIDs from configuration.
        
        Gets BLE service and characteristic UUIDs based on device configuration.
        Handles multi-device setups by appending instance_id to device name.

        Raises:
            ValueError: If device configuration is not found
        """
        try:
            sensor_amount = self.ConfigClass.get_sensor_amount("Connected_Wood_Plank")
            
            target_device = "Connected_Wood_Plank"
            if sensor_amount > 1:
                target_device = f"Connected_Wood_Plank_{self.instance_id}"

            for device in self.config['uuid_services']:
                if device['device'].lower() == target_device.lower():
                    self.SERVICE_UUID = device['SERVICE_UUID']
                    self.CAPACITIVE_UUID = device['CAPACITIVE_UUID']
                    self.STRAIN_GAUGE_UUID = device['STRAIN_GAUGE_UUID']
                    self.PIEZO_UUID = device['PIEZO_UUID']
                    return

            raise ValueError(f"Device '{target_device}' not found in the configuration")
        except Exception as e:
            logging.error(f"Error getting Connected Wood Plank UUIDs: {str(e)}")

    def parse_capacitive(self, sender, data):
        """
        Parse capacitive sensor data from BLE notification.

        Processes raw data from capacitive sensors, expecting:
            - Start marker: '<'
            - 16 unsigned short values (2 bytes each)
            - End marker: '>'

        Args:
            sender: BLE notification sender
            data: Raw byte array containing sensor readings
        """
        try:
            if data[0] != ord('<') or data[-1] != ord('>'):
                logging.error("Invalid start/end symbols for capacitive data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_CAPACITIVE):
                value = struct.unpack_from('<H', data, offset=1+i*2)[0]
                self.capacitive_data[f"capacitive_{i}"].append((timestamp, value))
            logging.info("Capacitive data received")
        except Exception as e:
            logging.error(f"Error parsing capacitive data: {str(e)}")

    def parse_strain_gauge(self, sender, data):
        """
        Parse strain gauge sensor data from BLE notification.

        Processes raw data from strain sensors, expecting:
            - Start marker: '('
            - 4 single-byte values
            - End marker: ')'

        Args:
            sender: BLE notification sender
            data: Raw byte array containing sensor readings
        """
        try:
            if data[0] != ord('(') or data[-1] != ord(')'):
                logging.error("Invalid start/end symbols for strain gauge data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_STRAIN):
                value = data[i+1]
                self.strain_data[f"strain_{i}"].append((timestamp, value))
            logging.info("Strain gauge data received")
        except Exception as e:
            logging.error(f"Error parsing strain gauge data: {str(e)}")

    def parse_piezo(self, sender, data):
        """
        Parse piezoelectric sensor data from BLE notification.

        Processes raw data from piezo sensors, expecting:
            - Start markers: '->'
            - 4 unsigned short values (2 bytes each, big endian)
            - End markers: '<-'

        Args:
            sender: BLE notification sender
            data: Raw byte array containing sensor readings
        """
        try:
            if data[0] != ord('-') or data[1] != ord('>') or data[-2] != ord('<') or data[-1] != ord('-'):
                logging.error("Invalid start/end symbols for piezoelectric data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_PIEZO):
                value = struct.unpack_from('>H', data, offset=2+i*2)[0]
                self.piezo_data[f"piezo_{i}"].append((timestamp, value))
            logging.info("Piezoelectric data received")
        except Exception as e:
            logging.error(f"Error parsing piezoelectric data: {str(e)}")

    async def run(self):
        """
        Main asynchronous operation loop.

        Handles:
            1. BLE device discovery using service UUID
            2. Device connection establishment
            3. Notification setup for all sensor types
            4. Continuous data collection until stop_event
            5. Clean disconnection and notification cleanup

        Raises:
            ConnectedWoodPlankError: If data collection process fails
        """
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: self.SERVICE_UUID.lower() in ad.service_uuids
            )

            if not device:
                logging.error(f"No device found with service UUID {self.SERVICE_UUID}")
                return

            logging.info(f"Device found: {device.name}")

            async with BleakClient(device) as client:
                logging.info(f"Connected to: {device.name}")

                await client.start_notify(self.CAPACITIVE_UUID, self.parse_capacitive)
                await client.start_notify(self.STRAIN_GAUGE_UUID, self.parse_strain_gauge)
                await client.start_notify(self.PIEZO_UUID, self.parse_piezo)

                logging.info("Notifications enabled, waiting for data...")
                
                while not self.stop_event.is_set():
                    await asyncio.sleep(1)

                await client.stop_notify(self.CAPACITIVE_UUID)
                await client.stop_notify(self.STRAIN_GAUGE_UUID)
                await client.stop_notify(self.PIEZO_UUID)
        except Exception as e:
            logging.error(f"Error in CWP data collection: {str(e)}")
            raise ConnectedWoodPlankError("CWP data collection error")

    def start_recording(self):
        """
        Begin data recording session.
        
        Initializes and starts a new thread for the asyncio event loop
        if no recording is currently in progress.
        """
        try:
            if not self.recording:
                self.recording = True
                self.stop_event.clear()
                self.recording_thread = threading.Thread(target=self._run_asyncio_loop)
                self.recording_thread.start()
                logging.info("Recording started")
            else:
                logging.warning("Recording is already in progress")
        except Exception as e:
            logging.error(f"Error starting recording: {str(e)}")

    def stop_recording(self):
        """
        Stop data recording session.
        
        Handles:
            1. Setting stop flag
            2. Thread cleanup
            3. Data export to CSV
        """
        try:
            if self.recording:
                self.recording = False
                self.stop_event.set()
                self.recording_thread.join()
                self.recording_thread = None
                logging.info("Recording stopped")
                self.send_data_to_csv()
            else:
                logging.warning("No recording in progress")
        except Exception as e:
            logging.error(f"Error stopping recording: {str(e)}")
            
    def send_data_to_csv(self):
        """
        Export collected data to CSV files.

        Creates separate CSV files for each sensor type:
            - CWP_Capa_data[_instance_id].csv: Capacitive sensor data
            - CWP_Piezos_data[_instance_id].csv: Piezoelectric sensor data
            - CWP_SG_data[_instance_id].csv: Strain gauge data

        Each file includes timestamps and all sensor channels.
        Instance_id is appended for multi-device setups.

        Raises:
            ConnectedWoodPlankError: If CSV writing fails
        """
        try:
            sensor_amount = self.ConfigClass.get_sensor_amount("Connected_Wood_Plank")

            for data, base_filename in [
                (self.capacitive_data, "CWP_Capa_data"),
                (self.piezo_data, "CWP_Piezos_data"),
                (self.strain_data, "CWP_SG_data")
            ]:
                if data:
                    # Convert the dictionary to a DataFrame
                    df = pd.DataFrame({key: [value for _, value in values] for key, values in data.items()})
                    df['timestamp'] = [timestamp for timestamp, _ in list(data.values())[0]]

                    if sensor_amount > 1:
                        new_filename = f"{base_filename}_{self.instance_id}.csv"
                    else:
                        new_filename = f"{base_filename}.csv"

                    new_path = self.DIRECTORY / new_filename
                    df.to_csv(new_path, mode="w", header=True, index=False)
                    logging.info(f"Data {base_filename} saved in {new_filename}")
                    data.clear()

            if not any([self.capacitive_data, self.piezo_data, self.strain_data]):
                logging.info("No CWP data to save.")
        except Exception as e:
            logging.error(f"Error writing CWP data to CSV: {str(e)}")
            raise ConnectedWoodPlankError("CWP CSV writing error")

    def _run_asyncio_loop(self):
        """
        Internal method to run asyncio event loop.
        
        Executes the main run() method in an asyncio context.
        Used by the recording thread for asynchronous operation.
        """
        asyncio.run(self.run())