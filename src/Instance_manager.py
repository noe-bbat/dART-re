"""
Sensor Instance Management System
===============================

Handles initialization and management of multiple sensor types.
Supports GridEye, SEN55, Myo Sensor, and Connected Wood Plank devices.
"""

from pathlib import Path
import logging

Main_path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf
import GridEyeKit as gek
import MyoSensor.Myo as Myo
import SEN55Bluetooth as cbd
import GrideyeBluetooth as geb
import streamlit as st
import ConnectedWoodPlank as cwp

class InstanceManager:
    """
    Manages multiple sensor instances and their lifecycle.
    Handles device initialization, monitoring, and cleanup.
    """

    def __init__(self, wifi_transmitter):
        """
        Initialize InstanceManager.

        Args:
            wifi_transmitter: Object for WiFi communication
        """
        self.configClass = Conf.Config()
        self.config = self.configClass.config
        
        self.wifi_transmitter = wifi_transmitter
        
        if 'sensor_instances' not in st.session_state:
            st.session_state.sensor_instances = {}
        self.sensor_instances = st.session_state.sensor_instances

    def initialize_devices(self, sensor, is_active, i, wifi_transmitter):
        """
        Initialize specified sensor device.

        Args:
            sensor: Sensor type identifier
            is_active: Activation status
            i: Instance number
            wifi_transmitter: WiFi transmission object

        Returns:
            tuple: (success_status, sensor_id)
        """
        sensor_id = f"{sensor}_{i}" if i > 1 else sensor
        port = self.configClass.get_device_port(sensor_id)

        if sensor == "Grideye":
            return self.initialize_bluetooth_grideye(sensor_id, i)
        elif sensor == "SEN55":
            return self.initialize_sen55(sensor_id, i)
        elif sensor == "Myo_Sensor":
            return self.initialize_myo_sensor(sensor_id, port, i)
        elif sensor == "Connected_Wood_Plank":
            return self.initialize_connected_wood_plank(sensor_id, i)
        else:
            st.error(f"Unknown sensor: {sensor}")
            return False, None

    def initialize_grideye(self, sensor_id, port, i):
        """
        Initialize GridEye sensor.

        Args:
            sensor_id: Unique sensor identifier
            port: Connection port
            i: Instance number

        Returns:
            tuple: (success_status, sensor_id)
        """
        try:
            grideye = gek.GridEYEKit(port, self.wifi_transmitter)
            if grideye.connect():
                self.sensor_instances[sensor_id] = grideye
                grideye.start_recording()
                grideye.instance_id = i
                self.configClass.set_status("Grideye", "true")
                st.success(f"{sensor_id} initialized & connected ✅")
                return True, sensor_id
            else:
                raise Exception(f"Error while initializing {sensor_id}. Please verify the connection.")
        except (gek.GridEYEError, Exception) as e:
            st.error(f"Error while initializing {sensor_id}: {str(e)}")
            return False, None

    def initialize_bluetooth_grideye(self, sensor_id, i):
        """
        Initialize Bluetooth GridEye sensor.

        Args:
            sensor_id: Unique sensor identifier
            i: Instance number

        Returns:
            tuple: (success_status, sensor_id)
        """
        try:
            grideye = geb.GridEYEReader(i)
            self.sensor_instances[sensor_id] = grideye
            grideye.start_recording()
            self.configClass.set_status("Grideye", "true")
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def initialize_sen55(self, sensor_id, i):
        """
        Initialize SEN55 sensor.

        Args:
            sensor_id: Unique sensor identifier
            i: Instance number

        Returns:
            tuple: (success_status, sensor_id)
        """
        try:
            sen55 = cbd.SEN55Bluetooth(self.wifi_transmitter)
            self.sensor_instances[sensor_id] = sen55
            self.configClass.set_status("SEN55", "true")
            sen55.instance_id = i
            sen55.start_recording()
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def initialize_myo_sensor(self, sensor_id, port, i):
        """
        Initialize Myo sensor.

        Args:
            sensor_id: Unique sensor identifier
            port: Connection port
            i: Instance number

        Returns:
            tuple: (success_status, sensor_id)
        """
        try:
            MyoSensor = Myo.MyoSensor(port)
            MyoSensor.launch_myo_executable()
            MyoSensor.instance_id = i
            self.sensor_instances[sensor_id] = MyoSensor
            self.configClass.set_status("Myo_Sensor", "true")
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Error while initializing {sensor_id}: {str(e)}")
            logging.error(f"Error while initializing {sensor_id}: {str(e)}")
            return False, None

    def initialize_connected_wood_plank(self, sensor_id, i):
        """
        Initialize Connected Wood Plank sensor.

        Args:
            sensor_id: Unique sensor identifier
            i: Instance number

        Returns:
            tuple: (success_status, sensor_id)
        """
        try:
            connected_wood_plank = cwp.ConnectedWoodPlank(i,self.wifi_transmitter)
            self.sensor_instances[sensor_id] = connected_wood_plank
            self.configClass.set_status("Connected_Wood_Plank", "true")
            connected_wood_plank.start_recording()
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def cleanup_on_error(self, activated_sensors):
        """
        Clean up sensors after error.

        Args:
            activated_sensors: List of activated sensor IDs
        """
        for sensor_id in activated_sensors:
            try:
                sensor_instance = self.sensor_instances.pop(sensor_id, None)
                if isinstance(sensor_instance, gek.GridEYEKit):
                    sensor_instance.stop_recording()
                    self.configClass.set_status(sensor_id, "false")
                if isinstance(sensor_instance, cbd.SEN55Bluetooth):
                    sensor_instance.stop_recording()
                    self.configClass.set_status(sensor_id, "false")
                if isinstance(sensor_instance, cwp.ConnectedWoodPlank):
                    sensor_instance.stop_recording()
                    self.configClass.set_status(sensor_id, "false")
                elif isinstance(sensor_instance, Myo.MyoSensor):
                    sensor_instance.stop_myo_executable()
                self.configClass.set_status(sensor_id.split('_')[0], "false")
            except Exception as deactivation_error:
                logging.error(f"Error deactivating {sensor_id}: {str(deactivation_error)}")

    def stop_grideye_sensor(self, sensor_id, sensor_instance):
        """
        Stop GridEye sensor.

        Args:
            sensor_id: Sensor identifier
            sensor_instance: GridEye sensor instance

        Returns:
            bool: Stop operation success status
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, gek.GridEYEError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def stop_grideye_bluetooth_sensor(self, sensor_id, sensor_instance):
        """
        Stop Bluetooth GridEye sensor.

        Args:
            sensor_id: Sensor identifier
            sensor_instance: Bluetooth GridEye instance

        Returns:
            bool: Stop operation success status
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, gek.GridEYEError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False

    def stop_bluetooth_sensor(self, sensor_id, sensor_instance):
        """
        Stop generic Bluetooth sensor.

        Args:
            sensor_id: Sensor identifier
            sensor_instance: Bluetooth sensor instance

        Returns:
            bool: Stop operation success status
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, cbd.SEN55BluetoothError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def stop_connected_wood_plank_sensor(self, sensor_id, sensor_instance):
        """
        Stop Connected Wood Plank sensor.

        Args:
            sensor_id: Sensor identifier
            sensor_instance: Wood Plank sensor instance

        Returns:
            bool: Stop operation success status
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, cwp.ConnectedWoodPlankError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def stop_myo_sensor(self, sensor_id, sensor_instance):
        """
        Stop Myo sensor.

        Args:
            sensor_id: Sensor identifier
            sensor_instance: Myo sensor instance

        Returns:
            bool: Stop operation success status
        """
        try:
            sensor_instance.stop_myo_executable()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, Myo.MyoSensorException) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def clean_up_session_instances(self):
        """Clear all sensor instances from current session."""
        self.sensor_instances.clear()