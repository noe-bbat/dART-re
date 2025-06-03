"""
Configuration Management Module
===========================

Provides centralized configuration management for the dARt Toolkit application.
Handles JSON-based configuration including:
    - Device settings and ports
    - Network configurations
    - Sensor parameters
    - Preset management
    - Status tracking

Features:
    - Dynamic configuration loading
    - Configuration validation
    - Multi-device support
    - Preset management
    - Real-time configuration updates
"""

import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
directory = Path(__file__).parent.resolve()

class Config:
    """
    Application configuration manager.
    
    Provides methods for reading, validating, and modifying application configuration.
    Manages device settings, network parameters, and system presets through a JSON file.

    Attributes:
        config_path: Path to configuration JSON file
        config: Loaded configuration dictionary
    """

    def __init__(self):
        """
        Initialize configuration manager.
        
        Loads configuration file and establishes base configuration state.
        Configuration file must be named 'config.json' in the same directory.
        """
        self.config_path = os.path.join(directory, 'config.json')
        self.config = self.load_config()
        
    def correct_config(self):
        """
        Validate and correct configuration settings.
        
        Performs configuration corrections:
            1. Ensures single instance for Grideye and Myo sensors
            2. Resets negative sensor counts
            3. Saves corrected configuration
        """
        self.set_grideye_myo_amount_to_one()
        self.reset_sensor_amount()
        self.save_config()
    
    def set_grideye_myo_amount_to_one(self):
        """
        Limit Grideye and Myo sensors to single instances.

        Returns:
            bool: True if changes were made, False otherwise

        Notes:
            Required for sensors that don't support multiple instances
        """
        try:
            changed = False
            for device in self.config['devices']:
                if device['device'].lower() == "Myo_Sensor" or "Grideye":
                    if device['amount'] > 1:
                        device['amount'] = 1
                        changed = True
            if changed:
                self.save_config()
            return changed
        except Exception as e:
            logging.error(f"Error while setting the amount of grideye and myo sensors to one: {e}")
            return False
        
    def reset_sensor_amount(self):
        """
        Reset negative sensor counts to zero.

        Returns:
            bool: True if any counts were reset, False otherwise

        Notes:
            Ensures valid sensor counts across all devices
        """
        try:
            reset_occurred = False
            for device in self.config['devices']:
                if device['amount'] < 0:
                    device['amount'] = 0
                    reset_occurred = True
            
            if reset_occurred:
                self.save_config()
            
            return reset_occurred
        except Exception as e:
            logging.error(f"Error while resetting the amount of sensors: {e}")
            return False
                
    def get_devices(self):
        """
        Retrieve configured devices list.

        Returns:
            list: List of device names from configuration

        Notes:
            Returns only device names, not full device configurations
        """
        devices = []
        for device in self.config['devices']:
            devices.append(device['device'])
            return devices
            
    def load_config(self):
        """
        Load configuration from JSON file.

        Returns:
            dict: Complete configuration dictionary

        Notes:
            Configuration file must be valid JSON format
        """
        with open(self.config_path, 'r') as config_file:
            return json.load(config_file)

    def get_device_port(self, device_name):
        """
        Get port for specific device.

        Args:
            device_name: Target device identifier

        Returns:
            str: Port identifier or None if not found

        Notes:
            Case-insensitive device name matching
        """
        for device in self.config['ports']:
            if device['device'].lower() == device_name.lower():
                return device['port']
        return None
    
    def get_device_ports(self, device_name):
        """
        Get all ports for a device type.

        Args:
            device_name: Device type identifier

        Returns:
            list: List of port identifiers

        Notes:
            Supports devices with multiple ports
        """
        ports = []
        for device in self.config['ports']:
            if device['device'].lower().startswith(device_name.lower()):
                ports.append(device['port'])
                return ports

    def get_available_devices(self):
        """
        Get list of active devices.

        Returns:
            list: Names of currently active devices

        Notes:
            Only returns devices marked as active in config
        """
        devices = []
        for device in self.config['devices']:
            if device['active']:
                devices.append(device['device'])
        return devices

    def get_values(self, device_name):
        """
        Get number of values for device.

        Args:
            device_name: Target device identifier

        Returns:
            int: Number of values or 0 if not found

        Notes:
            Used for data parsing configuration
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values']
        return 0

    def get_values_string(self, device_name):
        """
        Get value format string for device.

        Args:
            device_name: Target device identifier

        Returns:
            str: Format string or "0" if not found

        Notes:
            Used for data formatting and parsing
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values_string']
        return "0"

    def get_sensor_amount(self, device_name):
        """
        Get number of sensors for device type.

        Args:
            device_name: Device type identifier

        Returns:
            int: Number of sensors or 0 if not found

        Notes:
            Supports multi-sensor configurations
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['amount']
        return 0
    
    def set_sensor_amount(self, device_name, amount):
        """
        Set number of sensors for device type.

        Args:
            device_name: Device type identifier
            amount: New sensor count

        Returns:
            bool: True if update successful

        Notes:
            Automatically saves configuration after update
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['ammount'] = amount
                self.save_config()
                return True
        return False

    def get_status(self, device_name):
        """
        Get device activation status.

        Args:
            device_name: Target device identifier

        Returns:
            bool: True if active, False if inactive, None if not found

        Notes:
            Case-insensitive device name matching
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['active']
        return None

    def set_status(self, device_name, status):
        """
        Set device activation status.

        Args:
            device_name: Target device identifier
            status: New activation status

        Returns:
            bool: True if update successful

        Notes:
            Automatically saves configuration after update
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['active'] = status
                self.save_config()
                return True
        return False

    def get_active_preset(self):
        """
        Get currently active preset.

        Returns:
            str: Active preset identifier

        Notes:
            Returns preset name from configuration
        """
        return self.config['active_preset']['value']

    def set_active_preset(self, preset_name):
        """
        Set active configuration preset.

        Args:
            preset_name: Target preset identifier

        Raises:
            ValueError: If preset doesn't exist

        Notes:
            Validates preset existence before setting
        """
        preset_names = [preset['name'] for preset in self.config['presets']]

        if preset_name not in preset_names:
            raise ValueError(f"Preset '{preset_name}' does not exist. Available: {', '.join(preset_names)}")

        self.config['active_preset']['value'] = preset_name
        self.save_config()
        print(f"Active preset set to '{preset_name}'")

    def check_live_devices(self):
        """
        Check for devices in live mode.

        Returns:
            tuple: (list of live devices, boolean indicating live devices present)

        Notes:
            Used for real-time monitoring configuration
        """
        live_devices = []
        try:
            for device in self.config['devices']:
                if device['live'] == "true":
                    live_devices.append(device['device'])
            if live_devices:
                return live_devices, True
            else:
                return None, False
        except Exception as e:
            logging.error(f"Error while checking live devices: {e}")
            return None, False
    
    def get_wifi_configuration(self):
        """
        Get WiFi configuration settings.

        Returns:
            dict: WiFi configuration parameters or None if error

        Notes:
            Includes broadcast IP, port, and intervals
        """
        try:
            wifi_conf = {
                "Broadcast_IP": self.config["Wifi_settings"]["Broadcast_IP"],
                "Port": self.config["Wifi_settings"]["Port"],
                "Min_interval": self.config["Wifi_settings"]["Min_interval"],
                "Max_interval": self.config["Wifi_settings"]["Max_interval"],
            }
            return wifi_conf
        except Exception as e:
            logging.error(f"Error while retrieving the wifi configuration: {e}")
            return None
        
    def get_grideye_uuid(self, device_name):
        """
        Get GridEYE device UUID configuration.

        Args:
            device_name: Target device identifier

        Returns:
            dict: UUID configuration or None if not found

        Notes:
            Includes device address and service/characteristic UUIDs
        """
        for device in self.config['uuid_services']:
            if device['device'].lower() == device_name.lower():
                uuid_config = {
                    "DEVICE_ADDRESS": device['DEVICE_ADDRESS'],
                    "SERVICE_UUID": device['SERVICE_UUID'],
                    "CHARACTERISTIC_UUID": device['CHARACTERISTIC_UUID']
                }
                return uuid_config
            
    def save_config(self):
        """
        Save current configuration to file.

        Returns:
            bool: True if save successful

        Notes:
            Saves with formatting for readability
        """
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file, indent=4)
        return True