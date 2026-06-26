# Project Overview
This repository contains a comprehensive data analysis and calibration suite designed for Inertial Measurement Units (IMUs) and Motion Reference Units (MRUs). The project facilitates different calibration setups, primarily focused on comparing sensor outputs against reference data under various controlled physical setups (e.g., Pendulum and Table). It automates temporal curve-fitting, error metric calculation, and the generation of PDF calibration certificates.

The repository is structured into distinct experimental setups/sub-projects:
- **`Pendulum_Compare_MRU/`**: Calibration routines comparing the MRU under test against another reference MRU using a pendulum setup.
- **`Pendulum_Encoder_Kernel/`**: Calibration using an encoder (Kernel) on a pendulum as the reference.
- **`Pendulum_Encoder_Kongsberg/`**: Calibration using an encoder (Kongsberg) on a pendulum as the reference.
- **`Table/`**: Calibration routines utilizing a motorized table. This directory also includes the Arduino control code (`TableMotor/TableMotor.ino`) for driving the table.

## Key Technologies & Dependencies
* **Languages**: Python (primary for analysis and reporting), C++ (Arduino, for motor control).
* **Environment**: Conda (`conda activate base` is required before running Python commands).
* **Python Libraries**: `numpy`, `scipy`, `pandas`, `matplotlib`, `reportlab` (for PDF generation).
* **Interactive Tools**: Jupyter Notebooks (`.ipynb`) are extensively used for interactive signal processing (e.g., Butterworth filters), data exploration, and visual analysis.

## Development Conventions
* **Modular Structure**: The project strictly adheres to a folder-as-module pattern. Each functional component is typically enclosed in a dedicated folder, with an `index.py` acting as the main entry point (e.g., `Certificate/index.py`, `Monitor/index.py`).
* **Object-Oriented Programming**: The Python codebase follows OOP principles. Code must be structured using classes and encapsulation.
* **Naming Conventions**: 
  - `PascalCase` for Classes.
  - Strictly `camelCase` for variables, methods, instances, and arguments.
* **Typing & Comments**: Type hints/annotations in Python should NOT be used. Comments should be kept to an absolute minimum in favor of clean, expressive, and self-documenting code.
* **Data Organization**: Raw and processed data are organized within each setup's directories (e.g., `results/`, `output/`), usually separated into `reference/` and `target/` with metadata stored in `info.json` files.

## Building and Running
* **Data Analysis**: Navigate to the specific setup directory (e.g., `Pendulum_Compare_MRU/Format/`) and use Jupyter Notebooks (`Analysis.ipynb`) to process raw `.csv` data, filter signals, and generate evaluation metrics.
* **Certificate Generation**: After metrics are generated and placed in the appropriate `results/` folder, run the automated reporting script to produce the PDF certificate.
  ```bash
  conda activate base
  cd <Setup_Directory>
  python Certificate/index.py
  ```
* **Hardware Interfacing**: Use scripts in the `Monitor/` directories (e.g., `discoverBaud.py`, `index.py`) to interface with sensors and log data. Arduino code in `Table/TableMotor/` requires the Arduino IDE or CLI to flash to the hardware.
