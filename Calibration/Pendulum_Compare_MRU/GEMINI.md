# Project Overview
This project is a data analysis and calibration suite designed for Inertial Measurement Units (IMUs) or Motion Reference Units (MRUs). It processes raw sensor data (yaw, pitch, roll, angular velocities, and accelerations), performs temporal curve-fitting to compare target sensor outputs against reference data, and automatically generates PDF calibration certificates.

The codebase is primarily written in Python, utilizing Jupyter Notebooks for interactive data exploration and scripts for automated reporting.

## Key Components
* **`Abkp/TemporalFit.py`**: Contains the `TemporalFit` class, which uses `scipy.optimize.curve_fit` to model sensor responses and calculate key error metrics such as RMSE, MAE, and R-squared values.
* **`Certificate/index.py`**: A reporting module that uses `reportlab` to parse metrics (`metrics.json`) and plots (e.g., `error.png`, `ref_vs_model.png`) from the `results/` directory to generate a final `certificate.pdf`.
* **`Abkp/Kernel/protocol.txt`**: Documentation defining the byte-level structure for extracting "MODO HR CALIBRATED DATA" (payload parsing for yaw, pitch, roll, wx, wy, wz, ax, ay, az, and temperature).
* **`Format/Analysis.ipynb`** (and other notebooks): Interactive environments for applying signal processing (like Butterworth filters) and evaluating data sets. 

## Building and Running
* **Data Processing**: Open and run the Jupyter Notebooks (e.g., `Analysis.ipynb`) to process raw `.csv` data files, apply filters, and generate the necessary metrics and plots.
* **Certificate Generation**: After analysis is complete and `metrics.json`/plots are populated in the `results` folders, generate the PDF certificate by running the report script:
  ```bash
  conda activate base  # Ensure your conda environment is active
  python Certificate/index.py
  ```
* **Dependencies**: The project requires `numpy`, `scipy`, `pandas`, `matplotlib`, and `reportlab`.

## Development Conventions
* **Structure**: The project relies on a folder-as-module pattern, with `index.py` acting as the main entry point for specific components (e.g., `Certificate/index.py`).
* **Data Organization**: Test data is structured in directories by test case and axis (e.g., `test1/rolling_x/`), separated into `reference/` and `target/` subfolders containing `data.csv` and `info.json` metadata files.
* **Style**: Code generally follows Object-Oriented Principles. Classes are named using `PascalCase` (e.g., `TemporalFit`, `ReportData`), while methods and variables use `camelCase` or `snake_case` depending on the context. Ensure adherence to the global instruction to use `camelCase` for new methods/variables and strictly OOP where applicable.