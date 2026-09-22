# Multi422 - MRU Monitor & Comparator

Multi422 is a Python-based real-time monitoring and comparison tool for Motion Reference Units (MRUs). It allows for concurrent data acquisition from two different devices (typically a Kongsberg unit and a custom "Measure" unit), real-time visualization of motion data, and automated data logging for post-analysis.

## Project Overview

The project is designed to compare performance between a reference MRU and a target MRU. It handles serial communication, parses both custom and NMEA 0183 protocols, and provides a graphical interface for real-time observation.

### Core Technologies
- **Python**: Primary language.
- **Matplotlib**: Used for real-time data plotting (`Plotter/index.py`).
- **Pyserial**: Handles hardware communication via serial ports (`Device/index.py`).
- **Pandas/Numpy**: Data manipulation and CSV logging.
- **Pynput/Pyautogui**: Asynchronous keyboard monitoring and automation (`Utils/classes.py`).

### Architecture
The project follows a modular "folder-as-module" pattern:
- `index.py`: The main entry point. Orchestrates the `Monitor` class, threads, and the GUI.
- `Device/`: Manages serial connections.
    - `index.py`: `Device` class for handling various data formats (raw, JSON, List, NMEA).
    - `NMEA.py`: Custom NMEA 0183 parser for specific maritime sentences.
- `Plotter/`: Contains the `TimeGraph` class for interactive Matplotlib-based plotting.
- `Utils/`: Utility functions and classes.
    - `classes.py`: Implements `AsyncThreading` and `KeyboardListener` for non-blocking operations.
    - `functions.py`: UI and logging helpers (e.g., `sendEvent`).
- `output/`: Automatically generated directory for CSV logs and metadata.
- `Analysis.ipynb`: Jupyter notebook for post-processing the saved data.

---

## Building and Running

### Prerequisites
Ensure you have the required Python packages installed:
```bash
pip install pyserial pandas numpy matplotlib pynput pyautogui
```

### Running the Monitor
1.  **Configure Ports**: Edit `index.py` to set the correct serial ports for `deviceM` and `deviceK` (e.g., `/dev/ttyACM0`, `/dev/ttyUSB0`).
2.  **Start Monitoring**:
    ```bash
    conda activate base
    python index.py
    ```
3.  **Baud Rate Discovery**: If the connection fails, run the discovery script:
    ```bash
    python discoverBaud.py
    ```

### Keyboard Hotkeys (During Runtime)
- `q`: Quit and save data to the `output/` folder.
- `p`: Monitor **Pitch** (Measure vs. Kongsberg).
- `r`: Monitor **Roll** (Measure vs. Kongsberg).
- `y`: Monitor **Yaw** (Measure vs. Kongsberg).
- `a`: Monitor **Acceleration X** (`ax`).
- `w`: Monitor **Angular Velocity X** (`wx`).
- `o`: Monitor **Quaternion 0** (`q0`).

---

## Development Conventions

- **OOP Principles**: All core components (Monitor, Device, Plotter) are encapsulated in classes.
- **Folder-as-Module**: Each directory should have an `index.py` that serves as its primary interface.
- **Naming**: `camelCase` for variables and methods, `PascalCase` for classes (as per global conventions).
- **Asynchronous IO**: Use `AsyncThreading` for any loop that interacts with hardware to keep the UI responsive.
- **Data Persistence**: Always ensure the `save()` method in `index.py` is called upon exit to preserve experiment data.
- **NMEA Parsing**: If adding new NMEA sentences, update the `package` list in `Device/NMEA.py`.

---

## Usage for Analysis
After running a monitoring session, the `output/` folder will contain:
- `reference/data.csv`: Data from the Kongsberg/Reference device.
- `target/data.csv`: Data from the Measure/Target device.
- `info.json`: Metadata about the session.

Open `Analysis.ipynb` to visualize comparisons, calculate errors, and generate reports.
