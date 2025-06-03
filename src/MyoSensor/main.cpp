#include "myoclient.h"
#include "serial.h"
#include <fstream>
#include <iomanip>
#include <ctime>
#include <chrono>
#include <thread>
#include <csignal>
#include <filesystem>
#include <cstdlib>
#include <stdexcept>

using namespace myolinux;
namespace fs = std::filesystem;

volatile sig_atomic_t stop = 0;

void signal_handler(int signal) {
    log_message("Signal well received");
    stop = 1;
}

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

void log_message(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto now_c = std::chrono::system_clock::to_time_t(now);
    std::cout << std::put_time(std::localtime(&now_c), "%Y-%m-%d %H:%M:%S") << " - " << message << std::endl;
}

int main(int argc, char* argv[])
{
    std::string output_directory;
    log_message("Starting Myo data collection application");

    // Check for command line argument for output directory
    if (argc > 1) {
        output_directory = argv[1];
    } else {
        log_message("Error: Output directory not provided. Usage: " + std::string(argv[0]) + " <output_directory>");
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
            int reconnect_attempts = 0;
            while (!client.connected() && reconnect_attempts < MAX_RECONNECT_ATTEMPTS && !stop) {
                try {
                    log_message("Attempting to connect to Myo...");
                    client.connect();
                    if (client.connected()) {
                        log_message("Successfully connected to Myo!");
                        break;
                    }
                } catch (const std::exception& e) {
                    log_message("Connection error: " + std::string(e.what()));
                }
                reconnect_attempts++;
                log_message("Connection failed. Retrying in " + std::to_string(RECONNECT_DELAY_MS/1000) + " seconds...");
                std::this_thread::sleep_for(std::chrono::milliseconds(RECONNECT_DELAY_MS));
            }
            if (!client.connected()) {
                log_message("Failed to connect to Myo after " + std::to_string(MAX_RECONNECT_ATTEMPTS) + " attempts. Exiting.");
                return 1;
            }

            // Generate a unique filename with timestamp
            auto t = std::time(nullptr);
            auto tm = *std::localtime(&t);
            std::ostringstream oss;
            oss << "myo_data_" << std::put_time(&tm, "%Y%m%d_%H%M%S") << ".csv";
            std::string filename = (fs::path(output_directory) / oss.str()).string();

            // Open CSV file
            std::ofstream csv_file(filename, std::ios::app);
            if (!csv_file.is_open()) {
                log_message("Error: Failed to open CSV file: " + filename);
                return 1;
            }
            
            // Write CSV header
            csv_file << "Timestamp,EMG1,EMG2,EMG3,EMG4,EMG5,EMG6,EMG7,EMG8,";
            csv_file << "OrientationW,OrientationX,OrientationY,OrientationZ,";
            csv_file << "AccX,AccY,AccZ,";
            csv_file << "GyroX,GyroY,GyroZ" << std::endl;

            // Set sleep mode
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

                // Small delay to prevent CPU overload
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }

            csv_file.close();
            if (!client.connected()) {
                log_message("Disconnection detected. Attempting to reconnect...");
            }
        } catch (const std::exception& e) {
            log_message("Error: " + std::string(e.what()));
            log_message("Attempting to reconnect in 5 seconds...");
            std::this_thread::sleep_for(std::chrono::seconds(5));
            client.disconnect();  // Ensure clean disconnect before reconnecting
        }
    }
    client.disconnect();
    log_message("Program terminated gracefully.");

    return 0;
}
