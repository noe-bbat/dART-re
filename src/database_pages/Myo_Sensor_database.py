"""
@file Myo_Sensor_database.py
@brief A Streamlit application for visualizing Myo sensor data.

This module provides a user interface for loading, visualizing, and analyzing
Myo sensor data using Streamlit and Plotly.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import logging
from pathlib import Path
import config.configuration as conf
import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Main_path = Path(__file__).parents[1]

class MyoSensorDatabaseError(Exception):
    """Custom exception for MyoSensorDatabase"""
    pass

class MyoSensorDatabase:
    """
    @class MyoSensorDatabase
    @brief A class for managing and visualizing Myo sensor data.

    This class provides methods for loading Myo sensor data from CSV files
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the MyoSensorDatabase object.

        Sets up the configuration and file paths for the Myo data.
        """
        try:
            self.config = conf.Config().config
            self.csv_directory = Main_path / self.config['directories']['csv']
            self.csv_pattern = "myo_data*.csv"
        except Exception as e:
            logging.error(f"Error initializing MyoSensorDatabase: {str(e)}")
            raise MyoSensorDatabaseError(f"Error initializing MyoSensorDatabase: {str(e)}")

    def get_csv_files(self):
        """
        @brief Get a list of all CSV files matching the Myo data pattern.
        @return A list of CSV file paths.
        """
        try:
            return list(self.csv_directory.glob(self.csv_pattern))
        except Exception as e:
            logging.error(f"Error getting CSV files: {str(e)}")
            return []

    @staticmethod
    @st.cache_data
    def load_data(csv_path):
        """
        @brief Load and preprocess the Myo data from a CSV file.
        @param csv_path The path to the CSV file containing the Myo data.
        @return A pandas DataFrame containing the processed Myo data.
        """
        try:
            df = pd.read_csv(csv_path)
            if 'Timestamp' not in df.columns:
                st.warning(f"No 'Timestamp' column found in {csv_path.name}. Using row numbers as index.")
                df['Timestamp'] = range(len(df))
            else:
                try:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                except ValueError:
                    st.warning(f"Unable to parse 'Timestamp' column as datetime in {csv_path.name}. Using it as is.")
        except Exception as e:
            logging.error(f"Error loading data from {csv_path}: {str(e)}")
            df = pd.DataFrame()

        return df

    def display_data(self, df, file_name):
        """
        @brief Display the data and create visualizations.
        @param df The DataFrame containing the Myo data.
        @param file_name The name of the CSV file being displayed.
        """
        st.subheader(f"Raw data - {file_name}")
        st.write(df)

        st.subheader(f"Data Visualization - {file_name}")
        columns_to_plot = st.multiselect(f"Select columns to plot for {file_name}",
                                         [col for col in df.columns if col != 'Timestamp'],
                                         key=f"multiselect_{file_name}")

        if columns_to_plot:
            fig = px.line(df, x='Timestamp', y=columns_to_plot, title=f'Myo Data Over Time - {file_name}')
            st.plotly_chart(fig)

        st.subheader(f"Statistics - {file_name}")
        st.write(df.describe())

        st.subheader(f"Download Data - {file_name}")
        csv = df.to_csv(index=False)
        st.download_button(
            label=f"Download {file_name} data as CSV",
            data=csv,
            file_name=file_name,
            mime="text/csv",
            key=f"download_{file_name}"
        )

    def run(self):
        """
        @brief Run the Streamlit application for Myo data visualization.

        This method sets up the Streamlit interface, loads the data,
        and creates interactive visualizations for the Myo sensor data.
        """
        st.write("""
        # Myo Sensor Database

        This is the Myo sensor database page. You can visualize the **evolution of data** for different Myo sensor recordings.
        """)

        try:
            csv_files = self.get_csv_files()
            
            if not csv_files:
                st.warning("No Myo sensor data files found.")
                return

            # Create tabs for each CSV file
            tabs = st.tabs([file.name for file in csv_files])
            
            for tab, csv_file in zip(tabs, csv_files):
                with tab:
                    df = self.load_data(csv_file)
                    self.display_data(df, csv_file.name)

        except Exception as e:
            st.error(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

def main():
    """
    @brief The main function to run the MyoSensorDatabase application.

    This function initializes and runs the MyoSensorDatabase application.
    """
    try:
        app = MyoSensorDatabase()
        app.run()
    except MyoSensorDatabaseError as e:
        logging.error(f"Error running MyoSensorDatabase: {str(e)}")
        st.error(f"Error running MyoSensorDatabase: {str(e)}")

if __name__ == "__main__":
    main()