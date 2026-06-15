# Sensors Module

## Project Overview
This directory contains the C++ firmware module for a Motion Reference Unit (MRU) / IMU Sensor Fusion system. It is designed to run on an embedded platform (likely ESP32, given the usage of `esp_timer.h` and `HardwareSerial`). The module reads raw sensor data from a "Kernel" hardware component via UART, parses binary data packets, and performs complex sensor fusion and filtering.

### Key Features
*   **Kernel Communication (`Kernel/`)**: Manages the UART connection to the sensor hardware. Supports multiple data packet modes (High-Resolution `HR_MODE`, Quaternion `QT_MODE`, Orientation `OR_MODE`).
*   **Protocol Parsing (`Kernel/protocol/`)**: Implements strict binary packet checksum validation and extraction of acceleration, gyroscope, and orientation metrics.
*   **Gyroscope Calibration (`Kernel/gyrocal/`)**: A dynamic calibrator (`GyroCalibrator`) that gathers samples to calculate and subtract static bias from gyroscope readings.
*   **Orientation Filter (`Kernel/orientation/`)**: Implements a Madgwick sensor fusion algorithm (`OrientationParser`) to compute Euler angles (Pitch, Roll, Yaw) and Quaternions from raw accelerometer and gyroscope data.
*   **Heave Calculation (`Kernel/heave/`)**: Uses a high-pass filter and double integration (`Heave` class) to estimate vertical displacement (heave) based on global z-axis acceleration.

## Directory Overview
The directory strictly follows a **folder-as-module** pattern. Each sub-component is encapsulated within its own directory and exposed via an `index.h` file.

*   `index.h`: The main entry point. Defines the `Sensors` template class that orchestrates the Kernel communication, processing, and sensor data lifecycle.
*   `Kernel/index.h`: Defines the core `KernelSensor` class and specific protocol model classes (`KernelModelHR`, `KernelModelQuaternion`, `KernelModelOrientation`).
*   `Kernel/documents/`: Contains datasheets and Interface Control Documents (ICD) for the physical Kernel sensor.
*   `Kernel/gyrocal/index.h`: Implements the `GyroCalibrator` logic.
*   `Kernel/heave/index.h`: Implements the `Heave` displacement calculation filter.
*   `Kernel/orientation/index.h`: Implements the `OrientationParser` (Madgwick filter).
*   `Kernel/protocol/index.txt`: Documentation detailing the binary structure of the Kernel HR data packets.

## Building and Running
*   **Framework**: Designed for Arduino/ESP32 environments.
*   **Build System**: This module is a dependency of the larger `Hardware/Embedded/Main` project. It relies on the main project's build system (e.g., PlatformIO, ESP-IDF, or Arduino IDE) to compile. 
*   **Commands**: *(TODO: Integrate with the primary build system commands used in the root project space.)*

## Development Conventions
*   **Language**: C++ (Embedded). All code and documentation must be strictly written in English (though legacy comments/strings in Portuguese exist, new code must be in English).
*   **Architecture**: Header-only classes. Method implementations are written inline within class declarations inside the `index.h` files. 
*   **Object-Oriented Programming (OOP)**: Logic must be encapsulated into focused, state-managing classes (e.g., `Heave`, `OrientationParser`). 
*   **Naming Conventions**: 
    *   Classes use `PascalCase` (e.g., `KernelSensor`, `GyroCalibrator`).
    *   Variables, instances, arguments, and methods use `camelCase` (e.g., `heaveFilter`, `extract_i16`, `checksumValid`).
*   **Include Guards**: Use standard `#ifndef SENSORS_H` / `#define SENSORS_H` or `#pragma once` to prevent double inclusion.
*   **Math and Types**: Prefer explicit standard integer types (`int32_t`, `uint16_t`, `uint8_t`) for binary protocol parsing and explicit floats (`1.0f`) for mathematical sensor fusion calculations. Utilize standard math library (`<cmath>`).