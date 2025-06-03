"""
dARt Toolkit Main Application
===========================

Entry point for the dARt Toolkit Streamlit application. This module initializes 
and launches the main application components, handling configuration loading
and error management.

Features:
    - Application initialization
    - Configuration management
    - Error handling and reporting
    - WiFi communication setup (when enabled)

Dependencies:
    - streamlit: Web application framework
    - dart_GUI: Main application interface
    - config.configuration: Configuration management
    - config.Wifi_transmitter: WiFi communication
"""

import streamlit as st
from dart_GUI import dARtToolkit, dARtToolkitError
import config.configuration as Conf
import config.Wifi_transmitter as Wifi

def main():
    """
    Initialize and run the dARt Toolkit application.

    Process Flow:
        1. Load system configuration
        2. Check for live device connections
        3. Initialize WiFi communication if needed
        4. Launch main application interface
        5. Handle any critical errors

    Raises:
        dARtToolkitError: For application-specific errors
        Exception: For unexpected critical errors

    Notes:
        Displays error messages in the Streamlit interface
        if any initialization steps fail.
    """
    try:
        config = Conf.Config()
        devices, live = config.check_live_devices()
        
        # WiFi initialization commented out but preserved for future use
        # if live or devices():
        #     wifi_socket = Wifi.Wifi_transmitter()
        #     wifi_socket.start()
            
        app = dARtToolkit()
        app.run()
    except dARtToolkitError as e:
        st.error(f"Critical error: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected critical error occurred: {str(e)}")
        
if __name__ == "__main__":
    main()