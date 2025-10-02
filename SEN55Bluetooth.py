"""
SEN55 Bluetooth Sensor Interface
==============================

This module provides a comprehensive interface for SEN55 environmental sensors via Bluetooth Low Energy.
It handles device discovery, data collection, and storage for environmental parameters including:
    - Particulate Matter (PM1.0, PM2.5, PM10)
    - Temperature
    - Humidity
    - VOC (Volatile Organic Compounds)

The module supports multi-device configurations and real-time data monitoring.
"""

from bleak import BleakScanner
import asyncio
import struct
import time
import pandas as pd
import config.configuration as Conf
import os
import logging
from pathlib import Path
import threading
import signal
import sys
import json
from socket import *

s = socket(AF_INET,SOCK_DGRAM)
host ="..."
port = 5022
buf =1024
addr = (host,port)

Main_path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEN55BluetoothError(Exception):
    """
    Custom exception for SEN55 Bluetooth operations.
    Raised for initialization, connection, and data handling errors.
    """
    pass

class SEN55Bluetooth:
    """
    Manages SEN55 environmental sensor communication and data collection.
    
    Features:
        - Asynchronous BLE device discovery
        - Real-time data collection
        - CSV data storage
        - Multi-device support
        - WiFi data transmission support
    
    Attributes:
        instance_id: Device identifier for multi-sensor setups
        running (Event): Controls the data collection thread
        SEN55_data (list): Collected sensor readings
        wifi_transmitter: Optional WiFi transmission interface
    """

    def __init__(self, wifi_transmitter):
        """
        Initialize SEN55 Bluetooth interface.

        Args:
            wifi_transmitter: Object for WiFi data transmission
            
        Raises:
            SEN55BluetoothError: If initialization fails
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config
            self.wifi_transmitter = wifi_transmitter

            self.instance_id = 1
            self.stop_flag = False
            self.running = threading.Event()
            self.thread = None 
            self.latest_successful_read = time.time()
            
            self.SEN55_ports = self.ConfigClass.get_device_ports("SEN55")
            self.SEN55_mac_adress = None
            
            self.current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.DIRECTORY = self.config['directories']['csv']
            self.SEN55_filename = self.config['filenames']['SEN55']
            self.SEN55_path = Main_path / self.DIRECTORY / self.SEN55_filename
            self.SEN55_data = []

        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation: {str(e)}")
            raise SEN55BluetoothError("Erreur d'initialisation")
        
    def get_latest_data(self):
        """
        Retrieve most recent sensor reading.

        Returns:
            dict: Latest sensor data or None if no data available
        """
        latest_data = self.SEN55_data[-1] if self.SEN55_data else None
        return latest_data
    
    def get_SEN55_mac_adresses(self):
        """
        Configure MAC addresses for available SEN55 devices.

        Matches device MAC addresses to instance IDs for multi-device setups.

        Raises:
            SEN55BluetoothError: If MAC address retrieval fails or instance ID is invalid
        """
        try:
            if self.instance_id == 0:
                raise SEN55BluetoothError("Invalid instance ID: 0")
            self.SEN55_mac_adress = self.SEN55_ports[self.instance_id - 1]
        except Exception as e:
            logging.error(f"Error while getting MAC addresses: {str(e)}")
            raise SEN55BluetoothError("Error getting MAC addresses")
        
    def start_recording(self):
        """
        Start sensor data recording.

        Initializes a new thread for BLE scanning and data collection.
        Only starts if not already recording.
        """
        try:
            if not self.running.is_set():
                self.running.set()
                self.thread = threading.Thread(target=self.run_listen_for_sen55)
                self.thread.start()
                logging.info("Started listening for devices.")
        except Exception as e : 
            logging.error(f"Error while starting to listen for devices: {str(e)}")
            
    def stop_recording(self):
        """
        Stop sensor data recording.

        Performs:
            1. Data export to CSV
            2. Thread cleanup
            3. Resource release
        """
        try:
            if self.running.is_set():
                time.sleep(3)
                self.sen55_data_to_csv()
                logging.info("Data saved to CSV.")
                self.SEN55_data.clear()
                self.running.clear()
                if self.thread:
                    self.thread.join(timeout=5)
                    logging.info("Stopped listening for devices.")
        except Exception as e : 
            logging.error(f"Error while stopping to listen for devices: {str(e)}")
        
    async def listen_for_sen55(self):
        """
        Asynchronous BLE device discovery and data collection.

        Features:
            - Continuous BLE scanning
            - Device filtering by name
            - Manufacturer data parsing
            - Real-time data processing
            - Watchdog timer for connection monitoring

        Raises:
            SEN55BluetoothError: On device communication errors
        """
        if time.time() - self.latest_successful_read > 7:
            logging.info("No data received for 7 seconds. Stopping...")
            self.stop_recording()
            
        while self.running.is_set():
            try:
                available_devices = {device['device']: device for device in self.config['devices']}
                logging.info("Starting to listen...")

                async def detection_callback(device, advertising_data):
                    if device.name in available_devices:
                        if self.ConfigClass.get_status(device.name):
                            manufacturer_data = advertising_data.manufacturer_data
                            if manufacturer_data:
                                for company_id, data in manufacturer_data.items():
                                    logging.info(f"Raw data received: {[hex(x) for x in data]}")
                                    data_size = self.ConfigClass.get_values(device.name)
                                    if len(data) >= data_size:
                                        values = struct.unpack(self.ConfigClass.get_values_string(device.name), data[:data_size])
                                        logging.debug(', '.join(str(value) for value in values))
                                        #s.sendto(bytes(values),addr)
                                        
                                        if device.name == "SEN55":
                                            self.latest_successful_read = time.time()
                                            self.SEN55_data_to_array(values)
                                            #self.sen55_data_to_csv()
                                            #s.sendto(bytes(values),addr)
                                            #print("Ici ça passe")
                                            #print(host)
         
                                            #s.sendto(bytes(data_dict,"utf-8"),addr)
                                            
                                        if self.wifi_transmitter:
                                            latest_data = self.get_latest_data()
                                            self.wifi_transmitter.update(latest_data)
                                            print("On est la")
                                            host = self.config["Wifi_settings"]["Local_adress"]
                                            addr = (host,port)
                                            s.sendto(bytes(str(json.dumps(latest_data)),"utf-8"),addr)
                                            #self.sen55_data_to_csv()

                scanner = BleakScanner(detection_callback=detection_callback)
                await scanner.start()
                await asyncio.sleep(20)  # Run for 20 seconds
                await scanner.stop()
               # self.sen55_data_to_csv()

            except Exception as e:
                logging.error(f"Error while listening for devices: {str(e)}")
                raise SEN55BluetoothError("Error listening for devices")

    def run_listen_for_sen55(self):
        """
        Execute asynchronous BLE scanning.

        Wraps the async listen_for_sen55 method in a synchronous interface
        for thread execution.
        """
        asyncio.run(self.listen_for_sen55())
    
    def SEN55_data_to_array(self, values):
        """
        Process raw sensor data with proper byte reconstruction.
        """
        try:
            # Reconstruct decimal values from byte pairs
            pm1p0 = values[0] + values[1]/100.0
            pm2p5 = values[2] + values[3]/100.0
            pm10 = values[6] + values[7]/100.0
            temperature = values[10] + values[11]/100.0  # This matches Arduino's byte packing
            humidity = values[8] + values[9]/100.0
            voc = values[12] + values[13]/100.0
            nox = values[14] + values[15]/100
            #host=self.config["Wifi_settings"]["Local_adress"]
            #addr=(host,port)
            self.SEN55_data.append({
                "time": self.current_time,
                "Pm1p0": pm1p0,
                "Pm2p5": pm2p5,
                "Pm10": pm10,
                "Temperature": temperature,
                "Humidity": humidity,
                "VOC": voc,
                "NOx": nox
            })

        
            logging.debug(f"Reconstructed values - Temp: {temperature}°C, Humidity: {humidity}%")
        
        except IndexError as e:
            logging.error(f"Error processing SEN55 data: {str(e)}")
            raise SEN55BluetoothError("Invalid SEN55 data format")

    def sen55_data_to_csv(self):
        """
        Export collected data to CSV.

        Features:
            - Multiple device support with unique filenames
            - Append mode for continuous recording
            - Automatic header management
            - Data buffer clearing after export

        Raises:
            SEN55BluetoothError: If CSV write operation fails
        """
        try:
            df = pd.DataFrame(self.SEN55_data)
            base_filename = self.SEN55_filename[:-4]
            sensor_amount = self.ConfigClass.get_sensor_amount("SEN55")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.SEN55_filename

            new_filepath = Main_path / self.DIRECTORY / new_filename
            file_exists = os.path.isfile(new_filepath)

            df.to_csv(new_filepath, mode="a", header=not file_exists, index=False)
            logging.info(f"Données SEN55 enregistrées dans {new_filename}")
            self.SEN55_data.clear()
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données SEN55 dans le CSV: {str(e)}")
            raise SEN55BluetoothError("Erreur d'écriture CSV SEN55")
        
    def __del__(self):
        """
        Clean up resources on object destruction.
        Ensures recording is stopped before cleanup.
        """
        self.stop_recording()

if __name__ == "__main__":
   device = SEN55Bluetooth(None)
