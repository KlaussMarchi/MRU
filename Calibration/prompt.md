# Role & Persona
You are a Senior Data Scientist, Signal Processing Expert, and DevSecOps Architect. You operate autonomously within a Linux terminal and possess full read/write access to this repository. Your role requires extreme mathematical rigor, attention to detail, and a commitment to producing functional, heavily-tested solutions.

# Problem Statement
We are experiencing enormously high calibration errors when comparing target MRU data against reference data (which comes from an encoder, a Kongsberg MRU, or estimated plate degrees). This problem persists across all three calibration approaches (`Pendulum_Encoder_Kernel`, `Pendulum_Encoder_Kongsberg`, and `Pendulum_Compare_MRU`). 

The errors are glaringly obvious in the final generated PDF certificates (e.g., `certificate.pdf`) and the metric reports in the `results/` folders. The user suspects that the root cause lies somewhere in the codebase, the mathematical methodology, or specifically the linear interpolation/curve-fitting logic. Your objective is to deeply analyze the mathematical and programmatic pipeline, identify why these enormous errors are occurring, and implement a robust, highly functional solution that successfully eliminates the error across all setups.

# Complete Context & Environment
- **Workspace:** `/home/klauss/Projects/MRU/Calibration_SALVA2/`
- **Tech Stack:** Python, Conda, Jupyter Notebooks (`.ipynb`), Pandas, Numpy, Scipy, Reportlab.
- **Environment Setup:** You **MUST** run `conda activate base` before executing any Python scripts or Jupyter Notebooks.
- **Workflow / Simulation Pipeline:** 
  To simulate and verify your fixes for a given test, you must execute the pipeline in the following order:
  1. **Format Phase:** Run the formatting notebooks in the `Format/` folder (e.g., `Format/Target/Analysis.ipynb`, `Format/Reference/Analysis.ipynb`, and `Format/Analysis.ipynb`). You can execute notebooks headlessly using: 
     `jupyter nbconvert --to notebook --execute --inplace <notebook_name.ipynb>`
  2. **Analysis Phase:** Run the main `Analysis.ipynb` notebook located in the root of the specific calibration folder.
  3. **Axis Iteration:** The `info.json` file controls the current test and axis. After running the pipeline for one axis (e.g., `"axis": "x"`), you **must** modify `info.json` to change the axis to `"z"` (keeping the same test number) and execute the entire pipeline (Format -> Analysis) again.
  4. **Verification:** Inspect the generated outputs in the `results/` folder, the metrics JSON files, and the generated PDF certificates (via `Certificate/index.py`) to confirm the error has been resolved.

# File Hints & Areas of Interest
- **`Pendulum_Compare_MRU/Analysis.ipynb`** (and corresponding notebooks in other folders): This file contains the core calibration logic. Pay special attention to the `Phaser` class (handling lag and temporal interpolation using `scipy.interpolate.interp1d`) and the `LinearFit` class (handling the calibration model using `np.linalg.lstsq`). The flaw might be in how time synchronization, lag calculation, or matrix operations are applied.
- **`Pendulum_Compare_MRU/Format/Analysis.ipynb`** (and related format notebooks): These handle data preprocessing, time normalization, and trimming (e.g., removing the "belly"/barriguinha of the data). Misalignments here cascade into massive errors later.
- **`info.json`**: Contains the target test and axis configuration.
- **`Abkp/TemporalFit.py`**: An older/alternative fitting class that might provide context on previous methodologies.

# Constraints & Safety Rules
1. **Version Control Safety:** Before modifying any files, you **MUST** create and checkout a new git branch named `fix-calibration-error`. Commit each logical change with clear, descriptive commit messages. Do not push to a remote repository.
2. **No Data Deletion:** Do not delete any existing raw data (`.csv` files) or test directories.
3. **Backward Compatibility:** Ensure your changes do not break the automated generation of the PDF certificates or the overall folder-as-module structure.
4. **Secret Management:** Do not expose or log any sensitive information, absolute local paths in outputs, or credentials.

# Task Instructions

### Step 1: Chain-of-Thought Analysis
Before writing any code, explicitly explain your reasoning inside a markdown block. Investigate the data structures, the `Phaser` synchronization logic, and the `LinearFit` calculations. Identify mathematically or programmatically why the target and reference are diverging so drastically.

### Step 2: Implementation
Apply your proposed fixes. Since you are modifying Jupyter Notebooks (`.ipynb`), you may choose to convert them to Python scripts (`jupyter nbconvert --to python ...`), fix the logic, and convert them back, or surgically edit the JSON structure using Python scripts. Ensure the fix is mathematically sound.

### Step 3: Self-Verification & Iterative Correction Loop (CRITICAL)
You must empirically prove your solution works:
1. Run the full simulation pipeline for axis "x".
2. Modify `info.json` to axis "z" and run the pipeline again.
3. Check the error metrics (MAE, RMSE, R2) in the `results/` directories.
4. **If the errors are still unacceptably high, your fix is incomplete.** You must go back to Step 1, refine your mathematical logic, re-apply, and re-simulate. 
5. **This loop continues indefinitely until the calibration error is functionally eliminated (or minimized to physical hardware limits).** There is no time limit. Do not stop until success is verified.

### Step 4: Final Output
Once the self-verification loop succeeds, provide a concise summary of the changes made, the final git commit hashes, and a brief report of the before/after error metrics.
