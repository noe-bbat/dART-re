import asyncio
from bleak import BleakClient
import struct
import numpy as np

DEVICE_ADDRESS = "00:13:43:25:04:0D"  # Replace with your actual device address
SERVICE_UUID = "0783b03e-8535-b5a0-7140-a304d2495cb7"  # Replace with your actual service UUID
CHARACTERISTIC_UUID = "0783b03e-8535-b5a0-7140-a304d2495cb8"  # Replace with your actual characteristic UUID

HEADER = bytes.fromhex("2a2a2a")  # Fixed header to look for

class GridEYEReader:
    def __init__(self):
        self.buffer = bytearray()
        self.temperatures = np.zeros((8, 8), dtype=np.float32)

    def process_data(self, data):
        self.buffer.extend(data)
        # print(f"Received packet of {len(data)} bytes: {data.hex()}")  # Debugging output

        while True:
            header_index = self.buffer.find(HEADER)
            if header_index == -1:
                break

            # Start reading the temperature data after the header (2a2a2aXXXX)
            frame_start = header_index + len(HEADER) + 2  # Skip 2 bytes after header
            if len(self.buffer) - frame_start < 128:  # Not enough data for a full frame
                break

            frame_data = self.buffer[frame_start:frame_start + 128]  # Read 128 bytes for temperatures
            
            # Check for end marker (0d 0a)
            end_marker = self.buffer[frame_start + 128:frame_start + 130]
            if end_marker == bytes.fromhex("0d0a"):
                self.parse_frame(frame_data)

            # Remove processed data from the buffer
            self.buffer = self.buffer[frame_start + 128 + 2:]  # Move past the frame and end marker

    def parse_frame(self, frame_data):
        """
        Parses a frame of 128 bytes into 64 temperature readings and updates the temperature grid.
        """
        for i in range(8):
            for j in range(8):
                # Each temperature is 2 bytes, little-endian format
                index = (i * 8 + j) * 2
                # Get the two bytes for temperature reading
                raw_temp = frame_data[index:index + 2]

                # Convert to signed integer
                temp = struct.unpack('<h', raw_temp)[0]

                # Convert to Celsius (assuming raw value needs to be multiplied by 0.25)
                celsius_temp = temp * 0.25
                
                # Debugging output to verify raw and converted values
                # print(f"Raw temp (hex): {raw_temp.hex()}, Raw temp (dec): {temp}, Converted (°C): {celsius_temp}")  # Debugging output

                # Update the temperatures array
                self.temperatures[i][j] = celsius_temp

        # Display the temperatures in the grid
        self.display_temperatures()

    def display_temperatures(self):
        print("\nTemperatures (°C):")
        for i, row in enumerate(self.temperatures):
            print(f"Row {i}: " + " ".join(f"{temp:6.2f}" for temp in row))
        print("\nCorner temperatures:")
        print(f"Top-left: {self.temperatures[0, 0]:6.2f}  Top-right: {self.temperatures[0, 7]:6.2f}")
        print(f"Bottom-left: {self.temperatures[7, 0]:6.2f}  Bottom-right: {self.temperatures[7, 7]:6.2f}")
        print("\n")

async def run_ble_client():
    reader = GridEYEReader()
    
    def notification_handler(sender, data):
        reader.process_data(data)

    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"Connected to {DEVICE_ADDRESS}")

        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        print("Listening for notifications. Press Ctrl+C to stop.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

        await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    asyncio.run(run_ble_client())
