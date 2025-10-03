#include "myoclient.h"
#include "serial.h"
#include <fstream>
#include <array>
#include <iomanip>
#include <ctime>
#include <chrono>
#include <thread>
#include <csignal>
#include <filesystem>
#include <cstdlib>
#include <stdexcept>
#include <sstream>

using namespace myolinux;
namespace fs = std::filesystem;

std::chrono::seconds connection_timeout = std::chrono::seconds(30);


// Variable that will stop the loop getting data from the Myo. It will go to 1 after receiving a SIGInt in the fucntion just below
volatile sig_atomic_t stop = 0;

void signal_handler(int signal) {
    stop = 1;
}


// Created by Claude, it was suppossed to prevent the code from being stuck infinitely in the loop 
// gathering data but I've never seen it activated
class ConnectionWatchdog {
public:
    ConnectionWatchdog(std::chrono::seconds timeout) : timeout(timeout), last_activity(std::chrono::steady_clock::now()) {}

    void update() {
        last_activity = std::chrono::steady_clock::now();
    }

    bool is_timeout() {
        auto now = std::chrono::steady_clock::now();
        return std::chrono::duration_cast<std::chrono::seconds>(now - last_activity) > timeout;
    }

private:
    std::chrono::seconds timeout;
    std::chrono::steady_clock::time_point last_activity;
};

// Function to have better message in the command shell
void log_message(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto now_c = std::chrono::system_clock::to_time_t(now);
    std::cout << std::put_time(std::localtime(&now_c), "%Y-%m-%d %H:%M:%S") << " - " << message << std::endl;
}


// Function that will take the MAC Address from the command argument and shape it into a suitable MAC Address 
// for the connect() method of the myoclient.cpp
std::array<unsigned char, 6> parse_mac_address(const std::string& mac_str) {
    std::array<unsigned char, 6> address;
    std::istringstream ss(mac_str);
    std::string octet;
    
    for (int i = 0; i < 6; ++i) {
        if (!std::getline(ss, octet, ':')) {
            throw std::runtime_error("Invalid MAC address format");
        }
        address[i] = static_cast<unsigned char>(std::stoi(octet, nullptr, 16));
    }
    
    return address;
}

// Function to reconnect the Armband
void reconnect(myo::Client& client, const std::array<unsigned char, 6>& address) {
    const int MAX_RECONNECT_ATTEMPTS = 5;
    const int RECONNECT_DELAY_MS = 10000;
    int reconnect_attempts = 0;

    while (reconnect_attempts < MAX_RECONNECT_ATTEMPTS) {
        try {
            // Check if the connection is really established
            
            if (client.connected()) {
                log_message("Trying to reconnect even though we're connected ...");
                client.connect(address, connection_timeout);

                // Reset the bracelet parameters
                client.setSleepMode(myo::SleepMode::NeverSleep);
                client.setMode(myo::EmgMode::SendEmg, myo::ImuMode::SendData, myo::ClassifierMode::Disabled);
                log_message("Reconnection successful!");
                return;
            }
            
            log_message("Attempting to reconnect...");
            // Printing the state of client.connected()
            log_message(std::to_string(client.connected()));
            client.disconnect();  // Make sure the previous connection is closed
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));  // Wait a bit before reconnecting
            client.connect(address, connection_timeout);
            
        } catch (const std::exception& e) {
            log_message("Reconnection error: " + std::string(e.what()));
        }
        
        reconnect_attempts++;
        log_message("Reconnection failed. Trying again in " + std::to_string(RECONNECT_DELAY_MS/1000) + " seconds...");
        std::this_thread::sleep_for(std::chrono::milliseconds(RECONNECT_DELAY_MS));
    }
    
    throw std::runtime_error("Unable to reconnect after " + std::to_string(MAX_RECONNECT_ATTEMPTS) + " attempts.");
}

int main(int argc, char* argv[])
{
    std::string output_directory;
    std::string mac_address_str;
    log_message("Starting Myo data collection application");

    // Check for command line arguments
    if (argc < 3) {
        log_message("Error: Insufficient arguments. Usage: " + std::string(argv[0]) + " <output_directory> <MAC_address>");
        return 1;
    }

    output_directory = argv[1];
    mac_address_str = argv[2];

    // Parse MAC address
    std::array<unsigned char, 6> address;
    try {
        address = parse_mac_address(mac_address_str);
    } catch (const std::exception& e) {
        log_message("Error parsing MAC address: " + std::string(e.what()));
        return 1;
    }

    // Create output directory if it doesn't exist
    if (!fs::exists(output_directory)) {
        if (!fs::create_directories(output_directory)) {
            log_message("Error: Failed to create output directory: " + output_directory);
            return 1;
        }
    }

    // Set up signal handler for graceful shutdown
    std::signal(SIGINT, signal_handler);

    myo::Client client(Serial{"/dev/ttyACM0", 115200});
    ConnectionWatchdog watchdog(std::chrono::seconds(60));  // 1 minute timeout
    
    const int MAX_RECONNECT_ATTEMPTS = 5;
    const int RECONNECT_DELAY_MS = 5000;  // 5 seconds

    while (!stop) {
        try {
            if (!client.connected()) {
                log_message("Attempting to connect to Myo...");
                client.connect(address, connection_timeout);
            }

            if (!client.connected()) {
                log_message("Connection failed. Retrying in 5 seconds...");
                std::this_thread::sleep_for(std::chrono::seconds(5));
                continue;
            }

            log_message("Successfully connected to Myo!");

            // Generate a unique filename with timestamp
            auto t = std::time(nullptr);
            auto tm = *std::localtime(&t);
            std::ostringstream oss;
            oss << "myo_data_" << mac_address_str.substr(mac_address_str.length()-5) << "_" << std::put_time(&tm, "%Y%m%d_%H%M%S") << ".csv";
            std::string filename = (fs::path(output_directory) / oss.str()).string();

            // Open the CSV file
            std::ofstream csv_file(filename, std::ios::app);
            if (!csv_file.is_open()) {
                log_message("Error: Unable to open CSV file: " + filename);
                return 1;
            }
            
            // Write CSV header
            csv_file << "Timestamp,EMG1,EMG2,EMG3,EMG4,EMG5,EMG6,EMG7,EMG8,";
            csv_file << "OrientationW,OrientationX,OrientationY,OrientationZ,";
            csv_file << "AccX,AccY,AccZ,";
            csv_file << "GyroX,GyroY,GyroZ" << std::endl;

            // Configure sleep mode
            client.setSleepMode(myo::SleepMode::NeverSleep);

            // Read EMG and IMU
            client.setMode(myo::EmgMode::SendEmg, myo::ImuMode::SendData, myo::ClassifierMode::Disabled);

            std::array<int, 8> emg_data;
            myo::OrientationSample ori_data;
            myo::AccelerometerSample acc_data;
            myo::GyroscopeSample gyr_data;

            client.onEmg([&emg_data](myo::EmgSample sample)
            {
                for (std::size_t i = 0; i < 8; i++) {
                    emg_data[i] = static_cast<int>(sample[i]);
                }
            });

            client.onImu([&ori_data, &acc_data, &gyr_data](myo::OrientationSample ori, myo::AccelerometerSample acc, myo::GyroscopeSample gyr)
            {
                ori_data = ori;
                acc_data = acc;
                gyr_data = gyr;
            });

            auto last_write_time = std::chrono::steady_clock::now();

            log_message("Starting data collection loop");
            while (client.connected() && !stop) {
                client.listen();
                watchdog.update();

                auto current_time = std::chrono::steady_clock::now();
                if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - last_write_time).count() >= 10) {
                    // Get current timestamp
                    auto now = std::chrono::system_clock::now();
                    auto now_ms = std::chrono::time_point_cast<std::chrono::milliseconds>(now);
                    auto value = now_ms.time_since_epoch();
                    long long timestamp = value.count();

                    // Write data to CSV
                    csv_file << timestamp << ",";
                    for (int j = 0; j < 8; j++) {
                        csv_file << emg_data[j] << ",";
                    }
                    csv_file << ori_data[0] << "," << ori_data[1] << "," << ori_data[2] << "," << ori_data[3] << ",";
                    csv_file << acc_data[0] << "," << acc_data[1] << "," << acc_data[2] << ",";
                    csv_file << gyr_data[0] << "," << gyr_data[1] << "," << gyr_data[2] << std::endl;

                    last_write_time = current_time;
                }

                if (watchdog.is_timeout()) {
                    throw std::runtime_error("Watchdog timeout");
                }

                // Small delay to avoid CPU overload
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }

            csv_file.close();
            
            if (!client.connected()) {
                log_message("Disconnection detected. Attempting to reconnect...");
            }
        } catch (const std::exception& e) {
            log_message("Error: " + std::string(e.what()));
            log_message("Attempting to reconnect in 30 seconds...");
            std::this_thread::sleep_for(std::chrono::seconds(30));
            
            try {
                reconnect(client, address);
            } catch (const std::exception& e) {
                log_message("Reconnection failed: " + std::string(e.what()));
            }
        }
    }

    log_message("Disconnecting...");
    try {
        client.disconnect();
    } catch (const std::exception& e) {
        log_message("Program ended abnormally.");
    }
    // If this delay of 5 seconds is activated, I don't know why but the application doesn't end well
    // with the interface
    //std::this_thread::sleep_for(std::chrono::seconds(5));
    log_message("Program ended normally.");
    return 0;
}
