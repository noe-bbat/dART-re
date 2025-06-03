"""
External Storage Management Module
================================

This module provides a comprehensive solution for managing external storage devices,
including detection, monitoring, and CSV file backup operations.

Features:
---------
    - External storage detection and validation
    - Continuous monitoring of storage connection
    - Automated backup of CSV files
    - Thread-safe operation handling
    - Comprehensive logging

Dependencies:
------------
    - os: System operations
    - shutil: Advanced file operations
    - psutil: System and process information
    - logging: Event logging
    - pathlib: Path manipulation
    - threading: Thread management
    - time: Time operations
"""

import os
import shutil
import psutil
import logging
from pathlib import Path
import threading
import time 
import sys

Main_path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

class ExternalStorageError(Exception):
    """
    Custom exception for external storage operations.
    
    This exception is raised when errors occur during storage detection,
    monitoring, or backup operations.
    """
    pass

class ExternalStorageManager:
    """
    External storage manager for detection, monitoring, and automatic backup.
    
    This class provides a comprehensive interface for managing external storage operations
    including device detection, connection monitoring, and file backup functionality.
    
    Attributes
    ----------
    ConfigClass : Config
        Configuration class instance
    config : dict
        Configuration settings dictionary
    csv_directory : Path
        Directory path for CSV files
    monitor_thread : Thread
        Thread for storage monitoring
    _stop_monitoring : Event
        Threading event to control monitoring
    _storage_disconnected : Event
        Threading event for disconnection status
    _is_monitoring : bool
        Current monitoring status
    on_storage_disconnected : callable
        Callback for storage disconnection events
    initial_storage_path : str
        Path to initially detected storage
    
    Methods
    -------
    detect_external_storage()
        Detect and validate external storage devices
    start_monitoring(on_disconnected_callback)
        Begin storage connection monitoring
    stop_monitoring()
        Stop the storage monitoring process
    backup_and_clear_csv_files(external_path)
        Backup CSV files and clear originals
    verify_storage_ready()
        Check if storage is available and writable
    """
    
    def __init__(self):
        """
        Initialize the ExternalStorageManager with necessary configurations.
        
        Sets up logging, configuration, and initializes monitoring variables.
        """
        self.ConfigClass = Conf.Config()
        self.config = self.ConfigClass.config
        
        self.csv_directory = Main_path / self.config['directories']['csv']
        self._setup_logging()
        
        self.monitor_thread = None
        self._stop_monitoring = threading.Event()
        self._storage_disconnected = threading.Event()
        self._is_monitoring = False
        
        self.on_storage_disconnected = None
        self.initial_storage_path = None
        
        self._destroyed = False
        
    def _setup_logging(self):
        """
        Configure logging settings for the storage manager.
        
        Sets up logging with appropriate format and level for tracking
        storage operations and events.
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("ExternalStorageManager")

    def detect_external_storage(self):
        """
        Detect and validate available external storage devices.
        
        Returns
        -------
        tuple
            (bool, str or None) - Status and path of detected storage
            First element is True if valid storage found, False otherwise
            Second element is the mountpoint path if found, None otherwise
        
        Raises
        ------
        ExternalStorageError
            If there's an error during storage detection process
        """
        try:
            partitions = psutil.disk_partitions(all=True)
            
            valid_external_drives = []
            for partition in partitions:
                if self._is_external_drive(partition):
                    if os.access(partition.mountpoint, os.W_OK):
                        valid_external_drives.append(partition)
                        self.logger.debug(f"Found valid external drive at {partition.mountpoint}")
                    else :
                        self.logger.warning(f"External drive not writable: {partition.mountpoint}")
                        return False, None
            
            if valid_external_drives:
                valid_external_drives.sort(key=lambda x: x.mountpoint)
                chosen_drive = valid_external_drives[0]
                if self._is_monitoring:
                    self.logger.info(f"Using external storage at: {chosen_drive.mountpoint}")
                return True, chosen_drive.mountpoint
                
            self.logger.warning("No external storage device found")
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error detecting storage: {str(e)}")
            raise ExternalStorageError(f"Storage detection failed: {str(e)}")

    def _is_external_drive(self, partition):
        """
        Determine if a given partition is an external drive.
        
        Parameters
        ----------
        partition : psutil._pslinux.sdiskpart
            Partition object to check
        
        Returns
        -------
        bool
            True if partition is external drive, False otherwise
        """
        try:
            system_mounts = ['/boot', '/boot/firmware', '/','/System/Volumes']
            if partition.mountpoint in system_mounts:
                return False

            if 'removable' in partition.opts.lower():
                return True
                
            if partition.mountpoint.startswith(('/media/', '/mnt/')):
                if not any(mount in partition.mountpoint for mount in system_mounts):
                    return True
                
            if partition.device.startswith(('E:', 'F:', 'G:', 'H:')):
                return True
                
            # if '/dev/sd' in partition.device and not partition.device.startswith('/dev/sda'):
            if '/dev/sd' in partition.device:
                if any(fs in partition.fstype.lower() for fs in ['vfat', 'fat', 'exfat', 'ntfs']):
                    return True
            
            if sys.platform == 'darwin':
                 # Check if mounted in /Volumes and not a system volume
                if partition.mountpoint.startswith('/Volumes/'):
                    # Skip macOS specific system volumes
                    if partition.mountpoint not in ['/Volumes/Macintosh HD', '/Volumes/Recovery', '/Volumes/VM']:
                        # Additional check for mounted disk images (DMG files)
                        if 'disk image' not in partition.opts.lower():
                            return True
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking drive type: {str(e)}")
            return False
    
    def start_monitoring(self, on_disconnected_callback):
        """
        Start monitoring external storage for disconnection.
        
        Parameters
        ----------
        on_disconnected_callback : callable
            Function to call when storage disconnection is detected
        
        Raises
        ------
        ExternalStorageError
            If no external storage is available to monitor
        """
        try:
            if self._is_monitoring:
                self.logger.warning("Storage monitoring already active")
                return

            storage_found, storage_path = self.detect_external_storage()
            if not storage_found:
                raise ExternalStorageError("No external storage to monitor")
            
            self.initial_storage_path = storage_path
            self.on_storage_disconnected = on_disconnected_callback
            self._stop_monitoring.clear()
            self._storage_disconnected.clear()
            self._is_monitoring = True
            
            self.monitor_thread = threading.Thread(target=self._monitor_storage)
            self.monitor_thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
            self.monitor_thread.start()
            self.logger.info(f"Storage monitoring started for: {storage_path}")
        except Exception as e:
            self._is_monitoring = False
            self.logger.error(f"Error starting monitoring: {e}")
            raise
        
    def stop_monitoring(self):
        """
        Stop the external storage monitoring process.
        
        Gracefully stops the monitoring thread and cleans up resources.
        """
        try:
            if not self._is_monitoring:
                return

            self.logger.info("Stopping storage monitoring...")
            self._stop_monitoring.set()
            self._is_monitoring = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                try:
                    self.monitor_thread.join(timeout=2)
                except Exception:
                    pass  # Ignorer les erreurs de join qui peuvent survenir pendant le rechargement
                
                if self.monitor_thread.is_alive():
                    self.logger.warning("Monitor thread did not stop gracefully")
                
            self.monitor_thread = None
            self.initial_storage_path = None
            
            if not self._destroyed:  # Ne logger que si l'objet n'est pas en cours de destruction
                self.logger.info("Storage monitoring stopped successfully")
                
        except Exception as e:
            if not self._destroyed:
                self.logger.error(f"Error stopping monitoring: {e}")
        
    def _monitor_storage(self):
        """
        Internal method for continuous storage monitoring.
        
        Runs in a separate thread and continuously checks storage connection status.
        Triggers callback on disconnection detection.
        """
        while not self._stop_monitoring.is_set() and not self._storage_disconnected.is_set():
            try:
                if self._destroyed:  # Vérifier si l'objet est en cours de destruction
                    break
                    
                storage_found, current_path = self.detect_external_storage()
                
                if not storage_found or current_path != self.initial_storage_path:
                    if not self._destroyed:
                        self.logger.warning("External storage disconnected!")
                    self._storage_disconnected.set()
                    if self.on_storage_disconnected:
                        try:
                            self.on_storage_disconnected()
                        except Exception as e:
                            if not self._destroyed:
                                self.logger.error(f"Disconnection callback error: {e}")
                    break
                
                time.sleep(5)  # Utiliser un simple sleep
                
            except Exception as e:
                if not self._destroyed:
                    self.logger.error(f"Monitoring error: {e}")
                time.sleep(5)

        self._is_monitoring = False
        if not self._destroyed:
            self.logger.info("Storage monitoring thread ended")
            
    def backup_and_clear_csv_files(self, external_path):
        """
        Backup CSV files to external storage and clear originals.
        
        Parameters
        ----------
        external_path : str or Path
            Path to external storage for backup
        
        Returns
        -------
        bool
            True if backup completed successfully
        
        Raises
        ------
        ExternalStorageError
            If backup operation fails or source directory not found
        """
        try:
            backup_dir = Path(external_path) / f"dart_data_backup_{self._get_timestamp()}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            if not self.csv_directory.exists():
                raise ExternalStorageError(f"Source directory not found: {self.csv_directory}")
            
            csv_files = list(self.csv_directory.glob("*.csv"))
            if not csv_files:
                self.logger.info("No CSV files to backup")
                return True
                
            for csv_file in csv_files:
                safe_filename = csv_file.name.replace(':', '_')
                dest_path = backup_dir / safe_filename
                
                shutil.copy2(csv_file, dest_path)
                self.logger.debug(f"Backed up: {safe_filename}")
                
                if dest_path.exists():
                    csv_file.unlink()
                    self.logger.debug(f"Deleted: {csv_file.name}")
                else:
                    raise ExternalStorageError(f"Backup failed for: {csv_file.name}")
                    
            self.logger.info("Backup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup error: {str(e)}")
            raise ExternalStorageError(f"Backup failed: {str(e)}")

    def _get_timestamp(self):
        """
        Get current timestamp string.
        
        Returns
        -------
        str
            Formatted timestamp in YYYYMMDD_HHMMSS format
        """
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def verify_storage_ready(self):
        """
        Verify external storage is available and writable.
        
        Returns
        -------
        tuple
            (bool, str or None) - Status and path of storage
            First element is True if storage is ready, False otherwise
            Second element is the storage path if ready, None otherwise
        """
        try:
            storage_found, storage_path = self.detect_external_storage()
            if not storage_found:
                self.logger.warning("No external storage detected")
                return False, None
                
            if not os.access(storage_path, os.W_OK):
                self.logger.error(f"Storage not writable: {storage_path}")
                return False, None
                
            return True, storage_path
            
        except Exception as e:
            self.logger.error(f"Storage verification failed: {str(e)}")
            return False, None
        
    def __del__(self):
        """
        Destructor for the ExternalStorageManager.
        
        Ensures monitoring is stopped when the object is deleted.
        """
        if not self._destroyed:
            self._destroyed = True
            try:
                if self._is_monitoring:
                    self.stop_monitoring()
                logging.info("ExternalStorageManager cleaned up")
            except Exception as e:
                logging.error(f"Error during ExternalStorageManager cleanup: {e}")
