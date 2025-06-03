"""
@file CWP_database.py
@brief A Streamlit application for visualizing Connected Wood Plank (CWP) sensor data.

This module provides a user interface for loading, visualizing, and analyzing
CWP sensor data using Streamlit and Plotly.

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
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Main_path = Path(__file__).parents[1]

class CWPDatabaseError(Exception):
    """Custom exception for CWPDatabase"""
    pass

class CWPDatabase:
    """
    @class CWPDatabase
    @brief A class for managing and visualizing Connected Wood Plank (CWP) sensor data.

    This class provides methods for loading CWP sensor data from CSV files
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the CWPDatabase object.

        Sets up the configuration and file paths for the CWP data.
        """
        try:
            self.config = conf.Config().config
            self.csv_directory = Main_path / self.config['directories']['csv']
            self.cwp_files = ['CWP_SG', 'CWP_Capa', 'CWP_Piezos']
        except Exception as e:
            logging.error(f"Error initializing CWPDatabase: {str(e)}")
            raise CWPDatabaseError(f"Error initializing CWPDatabase: {str(e)}")

    def get_csv_files(self, file_prefix):
        """
        @brief Get a list of all CSV files matching the pattern for a specific CWP file type.
        @param file_prefix The prefix of the CWP file type (e.g., 'CWP_SG', 'CWP_Capa', 'CWP_Piezos').
        @return A list of CSV file paths.
        """
        try:
            pattern = f"{file_prefix}_data*.csv"
            return list(self.csv_directory.glob(pattern))
        except Exception as e:
            logging.error(f"Error getting CSV files for {file_prefix}: {str(e)}")
            return []

    def get_instances(self):
        """
        @brief Get the number of instances based on the CSV files present.
        @return A list of instance numbers.
        """
        all_files = []
        for prefix in self.cwp_files:
            all_files.extend(self.get_csv_files(prefix))
        
        instances = set()
        for file in all_files:
            match = re.search(r'_data(?:_(\d+))?\.csv$', file.name)
            if match:
                instance = int(match.group(1) or 0)  # If no number, use 0
                instances.add(instance)
        
        return sorted(instances)

    @staticmethod
    @st.cache_data
    def load_data(csv_path):
        """
        @brief Load and preprocess the CWP data from a CSV file.
        @param csv_path The path to the CSV file containing the CWP data.
        @return A pandas DataFrame containing the processed CWP data.
        """
        try:
            df = pd.read_csv(csv_path)

            if 'time' not in df.columns:
                st.warning(f"No 'time' column found in {csv_path.name}. Using row numbers as index.")
                df['time'] = range(len(df))
            else:
                try:
                    df['time'] = pd.to_datetime(df['time'])
                except ValueError:
                    st.warning(f"Unable to parse 'time' column as datetime in {csv_path.name}. Using it as is.")
        except Exception as e:
            logging.error(f"Error loading data from {csv_path}: {str(e)}")
            df = pd.DataFrame()

        return df

    def display_data(self, df, title):
        """
        @brief Display the data and create visualizations.
        @param df The DataFrame containing the CWP data.
        @param title The title for the data visualization.
        """
        st.subheader(f"Raw data - {title}")
        st.write(df)

        st.subheader(f"Data Visualization - {title}")
        columns_to_plot = st.multiselect(f"Select columns to plot for {title}",
                                         [col for col in df.columns if col != 'time'],
                                         key=f"multiselect_{title}")

        if columns_to_plot:
            fig = px.line(df, x='time', y=columns_to_plot, title=f'{title} Data Over Time')
            st.plotly_chart(fig)

        st.subheader(f"Statistics - {title}")
        st.write(df.describe())

        st.subheader(f"Download Data - {title}")
        csv = df.to_csv(index=False)
        st.download_button(
            label=f"Download {title} data as CSV",
            data=csv,
            file_name=f"{title}_data.csv",
            mime="text/csv",
            key=f"download_{title}"
        )

    def run(self):
        """
        @brief Run the Streamlit application for CWP data visualization.

        This method sets up the Streamlit interface, loads the data,
        and creates interactive visualizations for the CWP sensor data.
        """
        st.write("""
        # Connected Wood Plank (CWP) Database

        This is the CWP database page. You can visualize the **evolution of data** for different CWP sensors and instances.
        """)

        try:
            instances = self.get_instances()
            
            # Main tab for all CWP types
            main_tab, *instance_tabs = st.tabs(["All CWP Types"] + [f"Instance {i}" for i in instances])
            
            with main_tab:
                for cwp_type in self.cwp_files:
                    files = self.get_csv_files(cwp_type)
                    if files:
                        df = self.load_data(files[0])  # Load the first file of each type
                        self.display_data(df, cwp_type)
                    else:
                        st.warning(f"No data files found for {cwp_type}")
            
            # Instance tabs
            for instance, tab in zip(instances, instance_tabs):
                with tab:
                    for cwp_type in self.cwp_files:
                        files = [f for f in self.get_csv_files(cwp_type) if f.name.endswith(f"_{instance}.csv")]
                        if not files and instance == 0:
                            files = [f for f in self.get_csv_files(cwp_type) if not re.search(r'_\d+\.csv$', f.name)]
                        if files:
                            df = self.load_data(files[0])
                            self.display_data(df, f"{cwp_type} - Instance {instance}")
                        else:
                            st.warning(f"No data files found for {cwp_type} - Instance {instance}")

        except Exception as e:
            st.error(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

def main():
    """
    @brief The main function to run the CWPDatabase application.

    This function initializes and runs the CWPDatabase application.
    """
    try:
        app = CWPDatabase()
        app.run()
    except CWPDatabaseError as e:
        logging.error(f"Error running CWPDatabase: {str(e)}")
        st.error(f"Error running CWPDatabase: {str(e)}")

if __name__ == "__main__":
    main()