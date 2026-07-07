# GEMINI Project Context: MRU (Motion Reference Unit)

## 1. Project Overview
The **MRU (Motion Reference Unit)** project is a comprehensive hardware, firmware, and software ecosystem designed to measure, filter, and output motion data (pitch, roll, yaw, heave, acceleration, and angular velocity). It appears to be an embedded system built around an **ESP32-S3** microcontroller, interfacing with high-precision IMU sensors (such as the **Inertial Labs Kernel-120** and MPU6050/9250).

The project is highly focused on **Calibration, Validation, and Testing**, comparing the custom MRU ("Target") against high-end commercial reference units (like **Kongsberg MRU**) and mechanical ground truths ("Reference", such as an Encoder, a Motorized Table, or a Pendulum).

This file serves as a master context document for any AI agent working on this repository, allowing it to quickly grasp the architecture, file locations, and domain terminology to maximize efficiency and accuracy.

---

## 2. Terminology & Core Concepts
- **MRU (Motion Reference Unit)**: A device used primarily in marine and aerospace applications to measure wave motion, ship pitch/roll/heave, etc.
- **Target / Measure**: Refers to the custom MRU device being developed and tested (often connected via `/dev/ttyUSB0` or similar).
- **Reference**: The ground truth for motion. It can be a mechanical test rig (e.g., the Motorized Table simulating waves, or an optical Encoder on a pendulum).
- **Kongsberg**: A highly accurate, industry-standard commercial MRU used as a benchmark for comparison.
- **Kernel / Kernel-120**: An IMU sensor from Inertial Labs used inside the custom MRU.
- **Telemetry**: The custom MRU outputs data via USB, RS232, and RS422 interfaces.
- **NMEA**: Standard data format used by marine electronics, supported by this MRU.

---

## 3. Directory Structure & Deep Dive

### `Hardware/`
Contains all the embedded C++ (Arduino framework) code for the MRU and the test rigs.
- **`Embedded/Main/`**: The core ESP32-S3 firmware for the MRU.
  - `objects/sensors/Kernel/`: Interfaces with the Inertial Labs Kernel sensor. It handles binary protocols (HR_MODE, QT_MODE, OR_MODE), and includes onboard **Fusion** (Madgwick 6-DOF AHRS) and **Heave** (double-integrator with damping) algorithms.
  - `objects/telemetry/serial/`: Manages serial communications (RS232, RS422, USB COM). *Note: There have been past bugs here with the `NextSerial` class logic (losing bytes at 9600 baud).*
  - `objects/processing/`: Applies dynamic linear fits (`y = ax + b`) and low-pass filters to sensor data based on calibration JSONs.
  - `device/`: Main loop and task scheduling (FreeRTOS structure).
- **`TableMotor/`**: Firmware (`TableMotor.ino`) for a 2-axis motorized table driven by `FastAccelStepper`. It simulates wave motions (pitch and roll) using sine waves and outputs the exact simulated angles/accelerations to be used as ground truth ("Reference").
- **`Encoder/` & `Listener/` & `Hexapod/`**: Firmware for other test setups (reading rotary encoders on a pendulum, or moving a hexapod servo).

### `Monitor/`
A Python-based desktop tool used during live testing.
- Connects to multiple serial ports simultaneously (e.g., Target MRU, Reference Table, Kongsberg MRU).
- Synchronizes the data streams, normalizes them, and plots them in real-time using `matplotlib`/`pandas`.
- Saves the synchronized runs into an `output/` folder as `reference/data.csv`, `target/data.csv`, and `mru/data.csv` for post-analysis.

### `Calibration/`
The validation pipeline. It contains datasets from various experiments (`Pendulum_Compare_MRU`, `Table`, `Pendulum_Encoder_Kernel`).
- **`generate_certificates.py`**: A master Python script that iterates through test folders, runs headless Jupyter Notebooks (`Analysis.ipynb`) to calculate errors/metrics between the Target and Reference, and invokes `Certificate/index.py` to generate PDF **Calibration Certificates** with plotted graphs and signatures.

### `Analysis/`, `Filters/`, `Fusion/`, `Math/`, `MathFusion/`, `Optimizer/`
A massive collection of data science and algorithm development workspaces.
- Predominantly **Jupyter Notebooks (`.ipynb`)** and CSV datasets.
- Used to design, simulate, and optimize digital filters (Butterworth, Laplace, first/second-order TF), sensor fusion algorithms (Kalman, Mahony, Madgwick), and Heave estimation.
- Once an algorithm is mathematically proven in Python/Jupyter here, it is usually ported to C++ in `Hardware/Embedded/Main/objects/processing/` or `objects/sensors/Kernel/`.

### `Updater/`
A Python script (`index.py`) that performs over-the-serial (or OTA) firmware updates. It handshakes with the ESP32-S3 bootloader, base64 encodes the compiled `.bin` file in chunks, and flashes the MRU without needing the Arduino IDE.

### `Documents/`
Contains PDFs and manuals:
- `Kernel_ICD_rev-1.42_May_2025.pdf`, `kernel_datasheet.pdf`: Documentation for the Inertial Labs IMU.
- Kongsberg MRU manuals.
- Software GUIs and Windows Drivers for testing the sensors natively.

### `Management/`
Project management artifacts: Schematics (`Esquematico.xlsx`), patents analysis, and macro-delivery PDFs.

---

## 4. Software Architecture Summary
1. **Acquisition**: The ESP32-S3 reads raw IMU data from the Kernel-120 or MPU6050 via high-speed UART.
2. **Processing**: On-board algorithms apply the Madgwick AHRS filter (for Pitch, Roll, Yaw) and a double-integrator Heave filter.
3. **Telemetry**: The data is broadcasted simultaneously over USB, RS232 (pins 10/11), and RS422 (pins 12/13) at 9600 or 115200 baud.
4. **Validation**: The `Monitor` python script catches this telemetry alongside ground-truth data from the `TableMotor`. 
5. **Certification**: The `Calibration` notebooks process the CSVs, calculate the RMSE/variance, and generate a final PDF certificate.

---

## 5. Deep Architectural Insights (Firmware Details)
- **Madgwick AHRS (`fusion/index.h`)**: The C++ firmware explicitly contains a bit-exact single-precision float port of a Madgwick 6-DOF filter. It calculates the quaternion array from `ax, ay, az, wx, wy, wz` and extracts Euler angles.
- **Heave Estimator (`heave/index.h`)**: Heave (vertical displacement) is calculated by taking a projected acceleration vector (`a_proj`) and feeding it into a heavily damped double integrator with specific empirically tuned coefficients (`fc`, `zeta`, `px, py, pz`, `scale`, `offset`).
- **Dynamic Calibration (`processing/index.h`)**: The system supports live JSON-based calibration updates over Telemetry. These updates instantiate parameters (`a`, `b`, and `fc` for low-pass filtering) in a `LinearFit` class for all 9-DOF axes.

## 6. Guidelines for AI Agents
When tasked with a problem in this repository, follow these steps:
- **Embedded Fixes**: If modifying `Hardware/Embedded/Main/`, remember the system runs on FreeRTOS tasks. Be highly aware of `delay()`, loop times, and `Serial` buffer constraints.
- **Math/Filters**: If asked to tweak a filter, test it in the `Analysis/` or `Filters/` Jupyter notebooks first using existing CSV datasets before porting to C++.
- **Data Collection**: If the user is running a test, ensure `Monitor/index.py` is configured with the correct COM ports (`/dev/ttyUSB0`, etc.).
- **Always adhere to OOP principles** (as per user rules) and maintain the highly modular folder-as-module structure present in both the Python and C++ codebases.

---
*Created automatically to maximize contextual understanding.*
