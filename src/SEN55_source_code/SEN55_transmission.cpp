// SEN55 BLE Peripheral with continuous operation
#include <ArduinoBLE.h>
#include <Wire.h>
#include "SensirionI2CSen5x.h"

SensirionI2CSen5x sen5x;
unsigned long lastMeasurementTime = 0;
const unsigned long MEASUREMENT_INTERVAL = 1000;  // 1 second interval

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(100);    
  
  Serial.println("Starting SEN55 Debug Version");
  
  Wire.begin();
  Serial.println("I2C initialized");
  
  Serial.println("Initializing SEN55...");
  sen5x.begin(Wire);

  uint16_t error;
  char errorMessage[256];

  // Reset device
  error = sen5x.deviceReset();
  if (error) {
    Serial.print("Error trying to execute deviceReset(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  }

  // Set temperature offset
  float tempOffset = 0.0;
  error = sen5x.setTemperatureOffsetSimple(tempOffset);
  if (error) {
    Serial.print("Error setting temperature offset: ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  }

  // Start Measurement
  error = sen5x.startMeasurement();
  if (error) {
    Serial.print("Error starting measurement: ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  } else {
    Serial.println("Measurement started successfully");
  }

  // Initialize BLE
  Serial.println("Initializing BLE...");
  if (!BLE.begin()) {
    Serial.println("Failed to initialize BLE!");
    while (1);
  }

  BLE.setLocalName("SEN55");
  Serial.println("Setup complete!");
  
  Serial.println("Waiting for VOC/NOx initialization (this may take several minutes)...");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Only measure every MEASUREMENT_INTERVAL milliseconds
  if (currentTime - lastMeasurementTime >= MEASUREMENT_INTERVAL) {
    lastMeasurementTime = currentTime;
    
    uint16_t error;
    char errorMessage[256];
    uint8_t dataSend[16] = {0}; 

    float massConcentrationPm1p0, massConcentrationPm2p5, massConcentrationPm4p0, massConcentrationPm10p0;
    float ambientHumidity, ambientTemperature, vocIndex, noxIndex;
    
    error = sen5x.readMeasuredValues(
      massConcentrationPm1p0, massConcentrationPm2p5, massConcentrationPm4p0, massConcentrationPm10p0,
      ambientHumidity, ambientTemperature, vocIndex, noxIndex
    );

    if (error) {
      Serial.print("Error reading values: ");
      errorToString(error, errorMessage, 256);
      Serial.println(errorMessage);
      return;
    }

    // Debug raw values
    Serial.println("\n--- Raw Measurements ---");
    Serial.print("PM1.0: "); Serial.print(massConcentrationPm1p0);
    Serial.print("\tPM2.5: "); Serial.print(massConcentrationPm2p5);
    Serial.print("\tPM4.0: "); Serial.print(massConcentrationPm4p0);
    Serial.print("\tPM10.0: "); Serial.println(massConcentrationPm10p0);
    
    Serial.print("Temperature: ");
    if (isnan(ambientTemperature)) {
      Serial.print("n/a");
    } else {
      Serial.print(ambientTemperature);
    }
    
    Serial.print("\tHumidity: ");
    if (isnan(ambientHumidity)) {
      Serial.print("n/a");
    } else {
      Serial.print(ambientHumidity);
    }
    
    Serial.print("\tVOC Index: ");
    if (isnan(vocIndex)) {
      Serial.print("n/a");
    } else {
      Serial.print(vocIndex);
    }
    
    Serial.print("\tNOx Index: ");
    if (isnan(noxIndex)) {
      Serial.println("n/a");
    } else {
      Serial.println(noxIndex);
    }
    
    // Apply calibrations
    ambientTemperature = 1.0095 * ambientTemperature - 4.8051;
    ambientHumidity = 1.4383 * ambientHumidity - 2.5628;
    
    // Pack data for BLE transmission
    dataSend[0] = (uint8_t)(massConcentrationPm1p0);
    dataSend[1] = (uint8_t)((massConcentrationPm1p0 * 100) - (dataSend[0] * 100));

    dataSend[2] = (uint8_t)(massConcentrationPm2p5);
    dataSend[3] = (uint8_t)((massConcentrationPm2p5 * 100) - (dataSend[2] * 100));

    dataSend[4] = (uint8_t)(massConcentrationPm4p0);
    dataSend[5] = (uint8_t)((massConcentrationPm4p0 * 100) - (dataSend[4] * 100));

    dataSend[6] = (uint8_t)(massConcentrationPm10p0);
    dataSend[7] = (uint8_t)((massConcentrationPm10p0 * 100) - (dataSend[6] * 100));

    dataSend[8] = (uint8_t)(ambientHumidity);
    dataSend[9] = (uint8_t)((ambientHumidity * 100) - (dataSend[8] * 100));

    dataSend[10] = (uint8_t)(ambientTemperature);
    dataSend[11] = (uint8_t)((ambientTemperature * 100) - (dataSend[10] * 100));

    // VOC Index
    if (!isnan(vocIndex)) {
      dataSend[12] = (uint8_t)(vocIndex);
      dataSend[13] = (uint8_t)((vocIndex * 100) - (dataSend[12] * 100));
    }

    // NOx Index
    if (!isnan(noxIndex)) {
      dataSend[14] = (uint8_t)(noxIndex);
      dataSend[15] = (uint8_t)((noxIndex * 100) - (dataSend[14] * 100));
    }

    // BLE advertising
    BLEAdvertisingData advData;
    advData.setManufacturerData(0x09A3, dataSend, sizeof(dataSend));
    BLE.setAdvertisingData(advData);
    BLE.advertise();
    
    // Brief advertisement
    delay(100);
    BLE.stopAdvertise();
  }
}