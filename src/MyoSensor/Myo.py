"""
Myo Sensor Interface Module
=========================

This module manages the interface with Myo sensor devices. It handles:
    - Process management for the Myo executable
    - CSV data storage configuration
    - Device communication setup
    - Graceful process termination

The module ensures proper cleanup of resources and handles multi-instance configurations.
"""

from pathlib import Path
import logging
import psutil
import signal
import subprocess
import time 
import streamlit as st
import os
import sys

Main_path = Path(__file__).parent
Parent_path = Main_path.parent  # Points to 'src' directory
sys.path.append(str(Parent_path))

import config.configuration as Conf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MyoSensorException(Exception):
    """
    Custom exception for Myo sensor operations.
    Handles errors in initialization, execution, and termination.
    """
    pass

class MyoSensor:
    """
    Interface for Myo sensor device management.
    
    Handles:
        - Executable process management
        - Data storage configuration
        - Device communication
        - Resource cleanup

    Attributes:
        port: Communication port for the Myo device
        instance_id: Identifier for multi-sensor setups
        myo_process: Reference to the running Myo executable process
        csv_path: Path for data storage
    """

    def __init__(self, port):
        """
        Initialize Myo sensor interface.

        Args:
            port: Communication port identifier

        Raises:
            MyoSensorException: If initialization fails
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config
            
            self.port = port
            self.csv_dir = self.ConfigClass.config['directories']['csv']
            self.csv_path = Parent_path / self.csv_dir
            
            self.myo_process = None
            self.instance_id = 1
            
        except Exception as e:
            logging.error(f"Error in MyoSensor __init__ {e}")
            st.error(f"Error in MyoSensor __init__ {e}")
            raise MyoSensorException(f"Error in MyoSensor __init__ {e}")
        
    def launch_myo_executable(self):
        """
        Launch the Myo sensor executable process.

        Process:
            1. Verify directory permissions
            2. Configure data storage paths
            3. Start Myo executable
            4. Update sensor status

        Raises:
            MyoSensorException: If executable launch fails
        """
        try:
            os.makedirs(self.csv_path, exist_ok=True)
            
            executable_path = os.path.join(Main_path, "MyoLinux/src/MyoApp")
            logging.info(f"Mac address : {self.port}")
            
            # Verify executable permissions
            print(f"executable_path: {executable_path}")
            print(f"Executable rights: {os.access(executable_path, os.X_OK)}")
            print(f"Writing rights: {os.access(os.path.dirname(self.csv_path),os.W_OK)}")
            
            # Launch executable with CSV path and port
            self.myo_process = subprocess.Popen(
                [executable_path, self.csv_path, self.port], 
                preexec_fn=os.setsid
            )
            logging.info(f"Myo executable launched with PID: {self.myo_process.pid}")
            
            self.ConfigClass.set_status('MYO_Sensor', True)
           
        except Exception as e:
            st.error(f"Error while launching Myo executable file: {str(e)}")
            logging.error(f"Error while launching Myo executable file: {str(e)}")
            raise MyoSensorException(f"Error while launching Myo executable file: {str(e)}")
            
    def stop_myo_executable(self):
        """
        Stop the Myo sensor executable process.

        Process:
            1. Locate MyoApp process
            2. Send SIGINT signal for graceful shutdown
            3. Wait for process termination
            4. Force kill if necessary with SIGKILL
            
        The method ensures clean process termination to prevent resource leaks.
        """
        myo_process_exists = False
        for process in psutil.process_iter(['pid', 'name']):
                if "MyoApp" in process.info['name']:
                    myo_process_exists = True
                    pid = process.info['pid']
                    break

        if myo_process_exists:
            print(f"Stopping process")
            os.kill(pid, signal.SIGINT)
            print(f"Process stopped")
            
            # Wait up to 5 seconds for graceful termination
            for _ in range(5):
                if not psutil.pid_exists(pid):
                    break
                time.sleep(1)
            
            # Force kill if still running
            if psutil.pid_exists(pid):
                os.kill(pid, signal.SIGKILL)
            self.myo_process = None
            
if __name__ == "__main__":
    print(Parent_path)