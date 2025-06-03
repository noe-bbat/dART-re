"""
@file grideye_database.py
@brief A Streamlit application for visualizing Grid-EYE sensor data.

This module provides a user interface for loading, filtering, and visualizing
Grid-EYE sensor data using Streamlit and Plotly.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import config.configuration as conf
import logging
from pathlib import Path
import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Main_path = Path(__file__).parents[1]

class GridEyeDatabaseError(Exception):
    """Exception personnalisée pour GridEyeDatabase"""
    pass

class GridEyeDatabase:
    """
    @class GridEyeDatabase
    @brief A class for managing and visualizing Grid-EYE sensor data.

    This class provides methods for loading Grid-EYE sensor data from a CSV file
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the GridEyeDatabase object.

        Sets up the configuration and file paths for the Grid-EYE data.
        """
        try:
            self.ConfigClass = conf.Config()
            self.config = self.ConfigClass.config
            self.directory = self.config['directories']['database']
            self.csv_directory = os.path.join(Main_path, self.config['directories']['csv'])
            self.csv_pattern = os.path.join(self.csv_directory, f"{self.config['filenames']['Grideye'].split('.')[0]}*.csv")
            self.csv_files = self.get_csv_files()
        except Exception as e:
            logging.error(f"Error initializing GridEyeDatabase: {str(e)}")
            raise GridEyeDatabaseError(f"Error initializing GridEyeDatabase: {str(e)}")

    def get_csv_files(self):
        """
        @brief Get a list of all CSV files matching the pattern.
        @return A list of CSV file paths.
        """
        return glob.glob(self.csv_pattern)

    @staticmethod
    @st.cache_data
    def load_data(csv_path):
        """
        @brief Load and preprocess the Grid-EYE data from a CSV file.
        @param csv_path The path to the CSV file containing the Grid-EYE data.
        @return A pandas DataFrame containing the processed Grid-EYE data.
        """
        try:
            df = pd.read_csv(csv_path, parse_dates=['timestamp'])
            df['avg_temp'] = df.iloc[:, 2:].mean(axis=1)  # Calculate average temperature
            return df
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            return None

    def display_csv_data(self, csv_path):
        """
        @brief Display data for a single CSV file.
        @param csv_path The path to the CSV file to display.
        """
        df = self.load_data(csv_path)

        if df is not None:
            start_date = st.date_input("Start date", df['timestamp'].min().date(), key=f"start_date_{csv_path}")
            end_date = st.date_input("End date", df['timestamp'].max().date(), key=f"end_date_{csv_path}")

            filtered_df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]

            st.subheader("Temperature Evolution Over Time")
            fig = px.line(filtered_df, x='timestamp', y=['thermistor', 'avg_temp'],
                          labels={'value': 'Temperature', 'variable': 'Sensor'},
                          title='Thermistor and Average Cell Temperature Over Time')
            st.plotly_chart(fig, use_container_width=True)

            if st.checkbox("Show raw data", key=f"show_raw_{csv_path}"):
                st.subheader("Raw data")
                st.write(filtered_df)

            if st.button("Download filtered data as CSV", key=f"download_{csv_path}"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"filtered_{os.path.basename(csv_path)}",
                    mime="text/csv",
                    key=f"download_button_{csv_path}"
                )
        else:
            st.error(f"Unable to load the CSV file: {csv_path}. Please check the file and try again.")

    def run(self):
        st.write("""
        # Grid-EYE Database

        This is the Grid-EYE database page. You can visualize the **evolution of data** during a session.
        Select a tab to view data from different CSV files.
        """)

        try:
            # Create tabs for each CSV file
            csv_files = [os.path.basename(f) for f in self.csv_files]
            tabs = st.tabs(csv_files)

            # Display data for each CSV file in its corresponding tab
            for tab, csv_file in zip(tabs, self.csv_files):
                with tab:
                    self.display_csv_data(csv_file)

        except Exception as e:
            st.write(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

def main():
    try:
        app = GridEyeDatabase()
        app.run()
    except GridEyeDatabaseError as e:
        logging.error(f"Error running GridEyeDatabase: {str(e)}")
        st.error(f"Error running GridEyeDatabase: {str(e)}")

if __name__ == "__main__":
    main()