# 🎨 dARt Application

## 🌟 Overview

The **dARt application** is designed to interface with multiple types of sensors, including:

- 🌡️ **Grideye**
- 🌪️ **SEN55**
- 💪 **Myo**
- 🪵 **Wood Plank** sensors

It allows for configuring the number of sensors and enabling real-time data transfer over Wi-Fi. The system can be adjusted via the `config.json` file and operated through the application's UI.

## 📑 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
  - [Example 1: Grideye Only](#example-1-grideye-only)
  - [Example 2: Multiple Sensors](#example-2-multiple-sensors)
- [Usage](#usage)
- [Limitations](#limitations)

## 📥 Installation

1. Clone the repository to your local machine:

```bash
git clone https://github.com/AzTaiiyoo/dARt.git
```

2. Create a python environment:

> ℹ️ A python environment containing all dependencies is already provided with the repository. However, it
> might happen depending on your OS that the environment will not be working properly. If that happens,
> follow these instruction to create a custom python environment:

```bash
python -m venv dependencies/name_of_your_environment
```

Then activate it:

```bash
# On linux/MacOS
source dependencies/name_of_your_environment/bin/activate

# On Windows
source dependencies/name_of_your_environment/Scripts/activate
```

3. Install dependencies:

> To install the dependencies, you can either install them all at once using the requirement file such as:

```bash
pip install --no-cache-dir -r requirements.txt
```

Or do it manually using the _pip install_ command for each package in the requirements.txt file.

⚠️ **Warning**:
Due to some compatibility issues from the factory Grid-EYE code, you might encounter an error a `serial`error when running the app. If that happens, you have to run the following commands:

```bash
pip install serial        # install serial library
pip install pyserial     # install pyserial library
pip uninstall serial     # uninstall serial library
pip uninstall pyserial   # uninstall pyserial
pip install pyserial     # install pyserial library again
```

This should solve the problem.

## ⚙️ Configuration

Before running the application, you will need to modify the `config.json` file to set up the sensors you intend to use. This file serves as the central configuration hub for all sensors and system settings.

> 💡 **Configuration Overview**: The `config.json` file contains several key sections:
>
> - `devices`: Define sensor parameters and quantities
> - `ports`: Specify connection details for each sensor
> - `directories`: Set data storage locations
> - `filenames`: Configure output file naming
> - `Wifi_settings`: Setup for real-time data transfer (partially implemented)
> - `uuid_services`: Manage Bluetooth connections (particularly important for Grideye)

### 📝 Convention rules

The way of declaring sensors in the `config.json` file changes depending on if you wish to use one or multiple sensors of the same type. You must respect this convention for the **dARt** to work as intended.

#### 🔍 Example 1: Amount set to 1 for a sensor

In this case, use the simple sensor name without any number:

```json
"ports": [
    {
      "device": "SEN55",    // Simple name for single sensor
      "port": "53:89:D1:03:96:F7"  // MAC address for Bluetooth connection
    },
    {
      "device": "Grideye",         // Another single sensor example
      "port": "COM5"             // COM port for direct connection
    },
] ...
```

#### 🔍 Example 2: Amount set to > 1 for a sensor

When using multiple sensors of the same type, append numbers to the device names:

```json
"ports":[
  {
    "device": "Grideye_1",      // First Grideye sensor
    "port": "COM1"              // Unique port required for each sensor
  },
  {
    "device": "Grideye_2",      // Second Grideye sensor
    "port": "COM2"
  },
  {
    "device": "SEN55_1",        // First SEN55 sensor
    "port": "53:09:C1:F3:54:F2"  // Bluetooth address example
  },
  {
    "device": "SEN55_2",        // Second SEN55 sensor
    "port": "54:F2:11:43:54:F2"
  },
]...
```

### 🌡️ Example 1: Grideye Only

To use only Grideye sensors:

1. Open the `config.json` file and navigate to the `devices` section.
2. Locate the section labeled `device: "Grideye"`.
3. Set the `amount` variable to the number of Grideye sensors you want to use (e.g., 4).
   > ⚠️ **Note**: While the configuration supports multiple Grideye sensors, the current implementation in `src/GrideyeBluetooth.py` is optimized for a single sensor. For multiple sensors, code modifications will be needed.
4. Set the `live` variable to `true` if you want to enable real-time data transfer via Wi-Fi.
   > 💡 **Important**: The WiFi data transfer feature is partially implemented. The configuration structure exists but full functionality is not yet available.
5. Update ports section following the convention at the beginning of the config.json file or as shown below.

Example:

```json
{
  "device": "Grideye",
  "amount": 4,          // Number of sensors to configure
  "active": true,       // Enable this sensor type
  "live": true         // Enable real-time data transfer (partial implementation)
}

"ports":[
  {
    "device": "Grideye_1",   // First sensor identifier
    "port": "COM1"           // Connection port
  },
  {
    "device": "Grideye_2",   // Second sensor identifier
    "port": "COM2"           // Must use unique ports
  },
] ...
```

6. Save your changes and proceed to the application UI. Select the Grideye option, click start, and the system will initialize your Grideye sensors.

### 🔄 Example 2: Multiple Sensors

To use multiple sensors (e.g., 2 Grideye, 1 Myo, and 5 SEN55):

1. Open the `config.json` file and edit each sensor's section in the `devices` block.
2. Set the `amount` variable for each sensor:
   - 🌡️ `amount: 2` for Grideye
   - 💪 `amount: 1` for Myo
   - 🌪️ `amount: 5` for SEN55
3. If real-time data transfer is required for any of the sensors, set the `live` variable to `true` for those sensors.
4. Update ports section following the convention at the beginning of the config.json file or as shown below.

Example:

```json
{
  "device": "Grideye",
  "amount": 2, // amount set to greater than 1
  "active": true,
  "live": true
},
{
  "device": "Myo",
  "amount": 1,
  "active": true,
  "live": false
},
{
  "device": "SEN55",
  "amount": 5, // this amount is greater than 1 aswell
  "active": true,
  "live": true
}

"ports":[
  {
    "device": "Grideye_1",
    "port": "COM1" // If Grideye is set to serial connection, use COM port for example
  },
  {
    "device": "Grideye_2",
    "port": "COM2" // All sensors from same type are linked, so using one as serial implies you must use the other with serial
  },
   {
    "device": "SEN55_1",     // Now you use "_1" because amount is set to 5
    "port": "00:01:AB:EC:D5" // Random Mac address for a SEN55
  },
  {
    "device": "SEN55_2",    // Repeat it 3 times so you reach 5 SEN55
    "port": "00:01:AB:EC:D6"
  },
] ...
```

## 🚀 Usage

1. After configuring the `config.json` file, launch the application through the command using:

```bash
streamlit run src/main.py
```

2. In the UI:
   - ✅ Select the sensors you want to activate
   - ▶️ Click Start to initialize the sensors and begin data collection
   - ⏹️ To stop the session, click Stop Session
3. Data will be collected and transferred as per the configured settings.

In case you don't know what the Network link to the app is, you can type the following command in the terminal:

```bash
journalctl -u dart-app.service -f
```

This will show you the link to the app, which you can copy and paste in your browser.

## ⚠️ Limitations

Currently, the dARt application is designed to support a maximum of 1 Grideye and 1 Myo sensor at a time due to hardware limitations during development. However, the code is capable of handling multiple instances of these sensors. If you have more than one available, you can modify the following files to remove this limitation:

- 📄 `Configuration.py`
- 📄 `dart_GUI`

By adjusting these files, you can increase the number of supported **Grideye** and **Myo sensors**.

> 💡 The **Myo sensor** library was built to work on Linux and MacOS. This means on Windows, the application will work for every other sensors except for the Myo. Further development using **Docker** might solve that issue.

### 🔧 Rebuild MyoLinux Library

While this toolkit comes with a functional image for Raspberry Pi 3, you might encounter an "exec format error" when trying to use the Myo Armband on Linux or Mac. In such cases, rebuilding the library might resolve the issue.

#### Rebuilding Steps

1. Navigate to the MyoSensor folder, and clone the MyoArmband git:

```bash
git clone https://github.com/brokenpylons/MyoLinux.git
```

2. By precaution, remove .git file:

```bash
cd MyoLinux
rm -rf .git
```

3. In the src folder of MyoLinux, replace myoclient.cpp & myoclient.h files from the following git:

```bash
cd src
https://github.com/Iregnis/Dart_Toolkit_Florian/blob/main/Documentation.pdf
```

4. While in the src folder, compile the library:

```bash
cmake ..
make
make install
```

5. Replace the main.cpp file by the one provided in the git in given in task 3.

6. compile the c++ file:

```bash
g++ main.cpp -o executable_name -lmyolinux
```

Be sure to replace executable_name by the one you want to use (base is MyoApp).

7. Add libmyolinux.so to system path:

```bash
# Option 1
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:path_to_MyoLinux_src_folder/libmyolinux.so

# Option 2
export LD_LIBRARY_PATH=path_to_MyoLinux_src_folder/libmyolinux.so:$LD_LIBRARY_PATH
```

Now you can use the MyoSensor within the application or you can head back to the root of the app and type:

```bash
src/MyoSensor/MyoLinux/src/executable_name src/csv_files/data MAC_ADDRESS_OF_DEVICE
```

💡 The Mac address of the device provided in the toolkit is `53:89:D1:03:96:F7`

## 🔌 Connection on Raspberry Pi

### 🚨 Existing Problem

The optimal way to use the application is through SSH connection. However, to establish an SSH connection, the Raspberry Pi must be connected to the same network as your external computer.
🛠️ Initial Setup

Connect a screen and keyboard to the Raspberry Pi
Use the following commands to manage network connection:

```bash
# Display available networks
nmcli connection show

# Connect to a network
sudo nmcli device wifi connect "your_network_SSID" password "your_network_password"
```

Once done, you should be able to connect to the Raspberry Pi using ssh with the command :

```bash
ssh raspberry@raspberry_ip
```

### 💾 External Storage

Scripts on the Raspberry Pi are designed to automatically mount and unmount external storage devices. If you ever encounter an issue mentioning the storage device is already mounted, you can check the scripts using the following command:

```bash
# Enter automount script
sudo nano /home/raspberry/automount-usb.sh

# Enter auto unmount script
sudo nano /home/raspberry/unmount-usb.sh
```

A service has been created to automatically check the external drives every 5 seconds. You can edit that service using the following command:

```bash
sudo nano /etc/systemd/system/usb-monitor.service
```

Or you can use cron to execute the script every minute:

```bash
# Enter crontab
crontab -e
# uncomment lines starting with #* * * * * * and @reboot
```

## 🔌 Grideye Connection Mode

By default, the Grideye sensor operates via Bluetooth connection. However, you can modify this configuration to use a different connection mode. To change the connection mode:

1. Navigate to the `src/Instance_manager.py` file
2. Locate line 62 which contains:
   ```python
   return self.initialize_bluetooth_grideye(sensor_id, i)
   ```
3. Replace it with:
   ```python
   return self.initialize_grideye(sensor_id, port, i)
   ```

This modification will switch the Grideye sensor from Bluetooth to serial connection mode.

## 🔵 SEN55 Bluetooth Implementation Details

The SEN55 sensor uses Bluetooth connectivity for data transmission. The current implementation in `src/SEN55Bluetooth.py` is designed to read data from devices specifically named "SEN55" (as defined in line 186 with `if device.name == "SEN55"`).

### 🔄 Multiple SEN55 Sensors Implementation

For users planning to implement multiple SEN55 sensors in the future, the code will need to be modified to handle multiple devices. Here are several potential implementation approaches:

#### 1. ID-Based Approach

- Modify the device naming convention to use IDs (e.g., "SEN55_1", "SEN55_2")
- Change the code from `if device.name == "SEN55"` to `if device.name == f"SEN55_{i}"`
- Requires modification of the SEN55 source code in the `SEN55_source_code` folder
- Simplest approach but requires device name changes

#### 2. UUID Service Approach

- Implement UUID service identification in the `config.json` file
- More complex implementation
- Requires more extensive code modifications
- Provides more robust device identification

#### 3. MAC Address Implementation (Recommended)

- Utilize the existing `get_SEN55_mac_addresses(self)` function in `src/SEN55Bluetooth.py`
- Creates an array of MAC addresses for all SEN55 devices
- Maps MAC addresses to SEN55 instance IDs
- Requires modifying the SEN55 source code to use MAC addresses instead of device names
- Most flexible and maintainable solution

> 💡 **Recommendation**: The MAC address approach is the preferred method as it provides the most reliable device identification and scalability. However, it requires modifying the SEN55 source code to implement MAC address-based identification instead of name-based identification.
