import asyncio
from bleak import BleakClient
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import signal
import sys

DEVICE_ADDRESS = "00:13:43:25:04:0D"
CHARACTERISTIC_UUID = "0783b03e-8535-b5a0-7140-a304d2495cb8"

HEADER = bytes.fromhex("2a2a2a")

class GridEYEReader:
    def __init__(self):
        self.buffer = bytearray()
        self.temperatures = np.zeros((8, 8), dtype=np.float32)

        # Set up the plot
        self.fig, self.ax = plt.subplots()
        self.cax = self.ax.imshow(self.temperatures, cmap='hot_r', vmin=0, vmax=40)
        self.ax.set_title('Temperature Readings (°C)')
        self.ax.set_xlabel('Sensor Column')
        self.ax.set_ylabel('Sensor Row')
        plt.colorbar(self.cax)

        self.running = True  # Control variable to manage running state

    def process_data(self, data):
        self.buffer.extend(data)

        while True:
            header_index = self.buffer.find(HEADER)
            if header_index == -1:
                break

            if len(self.buffer) < header_index + len(HEADER) + 128 + 2:  # 2 for end marker
                break
            
            # Read 128 bytes of temperature data
            frame_start = header_index + len(HEADER) + 2  # Skip header and two additional bytes
            frame_data = self.buffer[frame_start:frame_start + 128]
            
            # Process the frame
            self.parse_frame(frame_data)
            
            # Remove processed data from buffer
            self.buffer = self.buffer[frame_start + 128 + 2:]  # Skip end marker

    def parse_frame(self, frame_data):
        for i in range(8):
            for j in range(8):
                index = (i * 8 + j) * 2
                temp = struct.unpack('<h', frame_data[index:index + 2])[0] * 0.25
                self.temperatures[i][j] = temp

    def update_plot(self):
        self.cax.set_array(self.temperatures)
        plt.draw()  # Draw the updated plot

async def run_ble_client(reader):
    def notification_handler(sender, data):
        reader.process_data(data)
        reader.update_plot()  # Update the plot with new data

    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"Connected to {DEVICE_ADDRESS}")

        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        print("Listening for notifications. Press Ctrl+C to stop.")
        
        try:
            while reader.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

        await client.stop_notify(CHARACTERISTIC_UUID)

def start_ble_thread(reader):
    asyncio.run(run_ble_client(reader))

# Signal handler to gracefully exit
def signal_handler(sig, frame):
    print('Exiting...')
    plt.close()  # Close the matplotlib window
    reader.running = False  # Set the running state to false to exit loop
    # Ensure BLE thread can finish properly
    if ble_thread.is_alive():
        ble_thread.join()

if __name__ == "__main__":
    # Create the GridEYEReader instance
    reader = GridEYEReader()

    # Register signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)

    # Start the BLE client in a separate thread
    ble_thread = threading.Thread(target=start_ble_thread, args=(reader,))
    ble_thread.start()

    # Start the Matplotlib event loop
    plt.show()

    # Wait for the BLE thread to finish before exiting
    ble_thread.join()

