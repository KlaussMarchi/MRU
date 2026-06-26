# Project Overview
This project focuses on Digital Signal Processing (DSP) and sensor fusion for a Motion Reference Unit (MRU). Its primary objective is to implement a robust, drift-free algorithm to calculate "heave" (vertical displacement) from IMU sensor data (accelerometer, gyroscope, and orientation metrics). The project utilizes a hybrid architecture:
- **Python (`heave.py`, `optimizer.py`, `Analysis.ipynb`)**: Used for data analysis, rapid prototyping, and parameter optimization (maximizing the $R^2$ score against reference data).
- **C++ (`heave.h`)**: The final optimized algorithm is strictly ported to a C++ header for deployment on an ESP32 microcontroller, ensuring 1-to-1 functional parity with the Python prototype.

# Key Directories and Files
- `Heave/heave.py`: The core Python implementation of the Heave calculation algorithm.
- `Heave/heave.h`: The C++ ESP32 port of the Heave algorithm.
- `Heave/prompt.md`: Contains autonomous AI constraints, data scaling factors, and calculation details.
- `Heave/files/`: Contains raw CSV test datasets (`test_1_x.csv`, `test_2_z.csv`, etc.).
- `Heave/docs/`: PDF documentation, diagrams, and reference materials.
- `Fusion/` & `Heave/Analysis.ipynb`: Jupyter Notebooks for data loading, scaling, and establishing ground-truth (`cal_heave`) references.

# Building and Running
- **Environment**: This project utilizes Conda. You must activate the base environment before executing python scripts.
  ```bash
  conda activate base
  ```
- **Optimization Loop**: Develop and run optimization logic (e.g., in a script like `optimizer.py`) within the Conda environment to discover optimal DSP filter parameters. Ensure the output $R^2$ score is maximized and output drift is minimized.
- **Time Handling Constraint**: The C++ algorithm utilizes absolute time in microseconds (via `esp_timer_get_time()`). To keep Python and C++ implementations identical, the Python `update()` method expects `timestamp_us` as an absolute timestamp in microseconds.

# Development Conventions
- **Python Constraints**: Do **NOT** use type hints or annotations in Python files.
- **Naming Conventions**: 
  - Use `PascalCase` for classes (e.g., `Heave`).
  - Strictly use `camelCase` for all variables, methods, instances, and arguments.
- **Architecture**: Strictly adhere to Object-Oriented Programming (OOP) principles. Keep all logic cleanly encapsulated in the relevant classes.
- **C++ Parity**: The C++ implementation must exactly mirror the mathematical behavior of the Python class to prevent functional divergence.
- **Data Scaling**: Raw data from the CSV logs must be scaled before processing:
  - Accelerations (`ax`, `ay`, `az`): `(value / 1000000.0) * 9.80665` (converts to $m/s^2$)
  - Angular velocities (`wx`, `wy`, `wz`): `value / 100000.0`
  - Orientations (`pitch`, `roll`, `yaw`): `value / 1000.0`
- **Version Control**: 
  - Always create a new Git branch before modifying any files (e.g., `git checkout -b feature/optimization`).
  - Commit logical changes with clear commit messages. Do NOT stage or commit untracked files unless they are specifically required.
- **Verification**: Simulate, test, and verify every change. For DSP changes, execute the optimizer, review the $R^2$ score, and iterate indefinitely until the solution is highly accurate and long-term stable.