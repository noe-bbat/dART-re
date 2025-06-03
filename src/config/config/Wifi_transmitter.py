"""
WiFi Data Transmission Module
==========================

This module implements UDP broadcast transmission for sensor data over WiFi networks.
It provides a robust interface for real-time data broadcasting with configurable
transmission intervals and automatic resource management.

Features:
    - UDP broadcast transmission
    - Configurable transmission intervals
    - Threaded operation
    - Automatic socket management
    - Data change detection
"""

import socket 
from pathlib import Path
import json
import time
import threading
import logging

Main_Path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

class Wifi_transmitter:
    """
    WiFi data transmission manager using UDP broadcast.
    
    Manages data transmission over WiFi networks using UDP broadcast protocol.
    Implements data change detection and configurable transmission intervals
    to optimize network usage.

    Attributes:
        Broadcast_IP (str): UDP broadcast address
        Port (int): UDP port number
        Min_interval (float): Minimum time between transmissions
        Max_interval (float): Maximum time between transmissions
        running (Event): Thread control flag
        sock: UDP socket instance
    """

    def __init__(self):
        """
        Initialize WiFi transmitter.

        Sets up:
            - Configuration parameters
            - Socket settings
            - Thread control
            - Data buffers

        Raises:
            Exception: If initialization fails
        """
        try:
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            self.init_wifi_config()
            self.sock = None
            
            self.latest_data = None
            self.previous_data = None
            
            self.running = threading.Event()
            self.thread = None
        except Exception as e:
            logging.error(f"Error initializing Wifi_transmitter: {e}")
        
    def init_wifi_config(self):
        """
        Load WiFi configuration settings.

        Retrieves and sets:
            - Broadcast IP address
            - Port number
            - Transmission intervals

        Raises:
            Exception: If configuration loading fails
        """
        try:
            wifi_config = self.configClass.get_wifi_configuration()
            if wifi_config:
                self.Broadcast_IP = wifi_config['Broadcast_IP']
                self.Port = wifi_config['Port']
                self.Min_interval = wifi_config['Min_interval']
                self.Max_interval = wifi_config['Max_interval']
            else:
                logging.error("Failed to get WiFi configuration")
        except Exception as e:
            logging.error(f"Error in init_wifi_config: {e}")
        
    def init_socket(self):
        """
        Initialize UDP broadcast socket.

        Creates and configures UDP socket for broadcast transmission.
        Sets SO_BROADCAST option for network broadcasting.

        Raises:
            Exception: If socket initialization fails
        """
        try:
            if self.sock is None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e:
            logging.error(f"Error initializing socket: {e}")
        
    def send_data(self, data):
        """
        Transmit data over UDP.

        Args:
            data: Data to broadcast (will be JSON-encoded)

        Process:
            1. JSON encode data
            2. Convert to UTF-8 bytes
            3. Broadcast via UDP socket

        Raises:
            Exception: If data transmission fails
        """
        try:
            if self.sock:
                message = json.dumps(data).encode('utf-8')
                self.sock.sendto(message, (self.Broadcast_IP, self.Port))
            else:
                logging.error("Socket not initialized, unable to send data")
        except Exception as e:
            logging.error(f"Error sending data: {e}")
        
    def start(self):
        """
        Start transmission thread.

        Initializes socket and starts transmission thread
        if not already running.

        Raises:
            Exception: If start-up fails
        """
        try:
            if not self.running.is_set():
                self.init_socket()
                self.running.set()
                self.thread = threading.Thread(target=self.run)
                self.thread.start()
                logging.info("Wifi transmitter started.")
        except Exception as e:
            logging.error(f"Error starting Wifi transmitter: {e}")
    
    def stop(self):
        """
        Stop transmission thread.

        Process:
            1. Clear running flag
            2. Wait for thread completion
            3. Close socket
            4. Clean up resources

        Raises:
            Exception: If shutdown fails
        """
        try:
            if self.running.is_set():
                self.running.clear()
                if self.thread:
                    self.thread.join(timeout=3)  # 3-second timeout
                if self.sock:
                    self.sock.close()
                    self.sock = None
                logging.info("Wifi transmitter stopped.")
        except Exception as e:
            logging.error(f"Error stopping Wifi transmitter: {e}")
 
    def update(self, data):
        """
        Update transmission data.

        Args:
            data: New data to be transmitted

        Updates latest_data buffer for next transmission cycle.

        Raises:
            Exception: If update fails
        """
        try:
            self.latest_data = data
        except Exception as e:
            logging.error(f"Error updating data: {e}")
        
    def __del__(self):
        """
        Cleanup resources on destruction.

        Ensures socket is closed and thread is stopped
        when object is destroyed.

        Raises:
            Exception: If cleanup fails
        """
        try:
            self.stop()
        except Exception as e:
            logging.error(f"Error in __del__ method: {e}")
        
    def run(self):
        """
        Main transmission loop.

        Continuously:
            1. Check for new data
            2. Transmit if data changed
            3. Sleep for minimum interval
            4. Handle any errors

        Runs in separate thread until stopped.

        Raises:
            Exception: If transmission loop fails
        """
        while self.running.is_set():
            try:
                if self.latest_data != self.previous_data:
                    self.send_data(self.latest_data)
                    self.previous_data = self.latest_data
                time.sleep(self.Min_interval)
            except Exception as e:
                logging.error(f"Error in Wifi transmitter thread: {e}")