"""
@file random_database.py
@brief A Streamlit application for visualizing random 3D data.

This module provides a user interface for generating and visualizing
random 3D data using Streamlit and Plotly.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import os
import config.configuration as conf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RandomDatabaseError(Exception):
    """Exception for RandomDatabase"""
    pass

class RandomDatabase:
    """
    @class RandomDatabase
    @brief A class for generating and visualizing random 3D data.

    This class provides methods for generating random 3D data and
    creating a Streamlit interface to visualize it.
    """

    def __init__(self):
        """
        @brief Initialize the RandomDatabase object.

        Sets up the configuration and directory paths.
        """
        try:
            self.Config = conf.Config()
            self.config = self.Config.config
            self.directory = self.config['directories']['database']
        except Exception as e:
            raise RandomDatabaseError(f"Error initializing RandomDatabase: {str(e)}")

    def list_py_files(self, directory):
        """
        @brief List all Python files in a given directory.
        @param directory The directory to search for Python files.
        @return A list of Python file names in the directory.
        """
        try:
            return [f for f in os.listdir(directory) if f.endswith('.py')]
        except Exception as e:
            logging.error(f"Error listing Python files: {str(e)}")

    def generate_random_3d_data(self, x_size=10, y_size=10, z_size=10):
        """
        @brief Generate random 3D data.
        @param x_size The size of the x dimension.
        @param y_size The size of the y dimension.
        @param z_size The size of the z dimension.
        @return A 3D numpy array of random values.
        """
        try:
            return np.random.rand(x_size, y_size, z_size)
        except Exception as e:
            logging.error(f"Error generating random 3D data: {str(e)}")

    def run(self):
        """
        @brief Run the Streamlit application.

        This method sets up the Streamlit interface, generates the 3D data,
        and creates the interactive visualization.
        """
        st.write("""
        # Random Database
        This is the Random database page. You can visualize the **evolution of data** during a session.
        """)

        try:
            st.sidebar.write("3D Data Visualization")
            x_size = st.sidebar.slider("X Size", 5, 20, 10)
            y_size = st.sidebar.slider("Y Size", 5, 20, 10)
            z_size = st.sidebar.slider("Z Size", 5, 20, 10)
        except Exception as e:
            logging.error(f"Error setting up sidebar: {str(e)})")
            st.write(f"Error setting up sidebar: {str(e)}")

        st.markdown(
            """
            This application visualizes random 3D data.
            Use the sliders in the sidebar to adjust the dimensions of the data.
            """
        )

        try:
            data = self.generate_random_3d_data(x_size, y_size, z_size)
            x, y, z = np.meshgrid(np.arange(x_size), np.arange(y_size), np.arange(z_size))
            values = data.flatten()

            fig = go.Figure(data=go.Volume(
                x=x.flatten(),
                y=y.flatten(),
                z=z.flatten(),
                value=values,
                isomin=0.1,
                isomax=0.8,
                opacity=0.1,
                surface_count=17,
            ))

            fig.update_layout(scene_aspectmode='data')
            st.plotly_chart(fig, use_container_width=True)

            if st.button("Generate New Random Data"):
                st.experimental_rerun()

            if st.checkbox("Show raw data"):
                st.write(data)
        except Exception as e:
            logging.error(f"Error running application: {str(e)}")
            st.write(f"Error running 3d model: {str(e)}")

def main():
    """
    @brief The main function to run the RandomDatabase application.

    This function initializes and runs the RandomDatabase application.
    """
    try:
        app = RandomDatabase()
        app.run()
    except RandomDatabaseError as e:
        logging.error(f"Error running RandomDatabase: {str(e)}")
        st.error(f"Error running RandomDatabase: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occured while running the application: {str(e)}")
        st.error(f"An unexpected error occured while running the application: {str(e)}")

if __name__ == "__main__":
    main()
