import streamlit as st
import pandas as pd
import plotly.express as px
import logging
from pathlib import Path
import config.configuration as conf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Main_path = Path(__file__).parents[1]

class SEN55DatabaseError(Exception):
    """Custom exception for SEN55Database"""
    pass

class SEN55Database:
    """
    @class SEN55Database
    @brief A class for managing and visualizing SEN55 sensor data.

    This class provides methods for loading SEN55 sensor data from a CSV file
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the SEN55Database object.

        Sets up the configuration and file paths for the SEN55 data.
        """
        try:
            self.config = conf.Config().config
            self.csv_directory = Main_path / self.config['directories']['csv']
            self.csv_pattern = f"{self.config['filenames']['SEN55'].split('.')[0]}*.csv"
            self.csv_files = self.get_csv_files()
        except Exception as e:
            logging.error(f"Error initializing SEN55Database: {str(e)}")
            raise SEN55DatabaseError(f"Error initializing SEN55Database: {str(e)}")
        
    def get_csv_files(self):
        """
        @brief Get a list of all CSV files matching the pattern.
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
        @brief Load and preprocess the SEN55 data from a CSV file.
        @param csv_path The path to the CSV file containing the SEN55 data.
        @return A pandas DataFrame containing the processed SEN55 data.
        """
        try:
            # Définir les noms de colonnes
            column_names = ['time', 'Pm1p0', 'Pm2p5', 'Pm10', 'Temperature', 'Humidity', 'Temp', 'VOC']
            
            # Lire le CSV avec les noms de colonnes spécifiés
            df = pd.read_csv(csv_path, names=column_names, parse_dates=['time'])
            
            return df
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            return pd.DataFrame()

    def run(self):
        """
        @brief Run the Streamlit application for SEN55 data visualization.

        This method sets up the Streamlit interface, loads the data,
        and creates interactive visualizations for the SEN55 sensor data.
        """
        st.write("""
        # SEN55 Database

        This is the SEN55 database page. You can visualize the **evolution of data** during a session.
        """)
        try:
            csv_files = [f.name for f in self.get_csv_files()]
            tabs = st.tabs(csv_files)
            
            for tab, csv_file in zip(tabs, csv_files):
                with tab:
                    df = self.load_data(self.csv_directory / csv_file)
                    self.display_data(df)

        except Exception as e:
            st.error(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

    def display_data(self, df):
        """
        @brief Display the data and create visualizations.
        @param df The DataFrame containing the SEN55 data.
        """
        st.subheader("Raw data")
        st.write(df)

        st.subheader("Data Visualization")
        columns_to_plot = st.multiselect("Select columns to plot",
                                         [col for col in df.columns if col != 'time'])

        if columns_to_plot:
            fig = px.line(df, x='time', y=columns_to_plot, title='SEN55 Data Over Time')
            st.plotly_chart(fig)

        st.subheader("Statistics")
        st.write(df.describe())

        st.subheader("Download Data")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="SEN55_data.csv",
            mime="text/csv",
        )

def main():
    """
    @brief The main function to run the SEN55Database application.

    This function initializes and runs the SEN55Database application.
    """
    try:
        app = SEN55Database()
        app.run()
    except SEN55DatabaseError as e:
        logging.error(f"Error running SEN55Database: {str(e)}")
        st.error(f"Error running SEN55Database: {str(e)}")

if __name__ == "__main__":
    main()