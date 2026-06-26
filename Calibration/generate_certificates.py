import json
import os
import shutil
import subprocess

experiments = [
    'Pendulum_Compare_MRU',
    'Pendulum_Encoder_Kernel',
    'Pendulum_Encoder_Kongsberg',
    'Table'
]

axes = ['x', 'z']

def run_notebook(path):
    print(f"  Running {path}...")
    try:
        subprocess.run([
            'jupyter', 'nbconvert', '--to', 'notebook', '--execute', '--inplace', path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Failed to run {path}: {e}")

output_dir = '/home/klauss/Projects/MRU/Calibration_SALVA2/Documents/calibrations'
os.makedirs(output_dir, exist_ok=True)

for exp in experiments:
    exp_path = os.path.join('/home/klauss/Projects/MRU/Calibration_SALVA2', exp)
    if not os.path.isdir(exp_path):
        continue
    
    info_path = os.path.join(exp_path, 'info.json')
    if not os.path.exists(info_path):
        continue
    
    with open(info_path, 'r') as f:
        info = json.load(f)
        
    has_target = 'target' in info
    exp_axes = axes if has_target else [None]
    
    for axis in exp_axes:
        if axis is not None:
            print(f"\n--- Processing {exp} - Axis {axis} ---")
            info['target']['axis'] = axis
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=4)
        else:
            print(f"\n--- Processing {exp} ---")
            
        target_format_nb = os.path.join(exp_path, 'Format', 'Target', 'Analysis.ipynb')
        if os.path.exists(target_format_nb):
            run_notebook(target_format_nb)
            
        ref_format_nb = os.path.join(exp_path, 'Format', 'Reference', 'Analysis.ipynb')
        if os.path.exists(ref_format_nb):
            run_notebook(ref_format_nb)
            
        format_nb = os.path.join(exp_path, 'Format', 'Analysis.ipynb')
        if os.path.exists(format_nb):
            run_notebook(format_nb)
            
        main_nb = os.path.join(exp_path, 'Analysis.ipynb')
        if os.path.exists(main_nb):
            run_notebook(main_nb)
            
    print(f"\n--- Generating Certificate for {exp} ---")
    cert_dir = os.path.join(exp_path, 'Certificate')
    cert_script = os.path.join(cert_dir, 'index.py')
    
    if os.path.exists(cert_script):
        try:
            subprocess.run(['python3', 'index.py'], cwd=cert_dir, check=True)
            
            cert_pdf = os.path.join(cert_dir, 'release', 'certificate.pdf')
            os.makedirs(output_dir, exist_ok=True)
            if os.path.exists(cert_pdf):
                dest_pdf = os.path.join(output_dir, f'certificate_{exp}.pdf')
                shutil.copy(cert_pdf, dest_pdf)
                print(f"Copied certificate to {dest_pdf}")
            else:
                import glob
                pdfs = glob.glob(os.path.join(cert_dir, 'release', '*.pdf'))
                if pdfs:
                    dest_pdf = os.path.join(output_dir, f'certificate_{exp}.pdf')
                    shutil.copy(pdfs[0], dest_pdf)
                    print(f"Copied certificate {pdfs[0]} to {dest_pdf}")
                else:
                    print(f"Warning: Certificate not found in {cert_dir}/release")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to generate certificate for {exp}: {e}")

print("\nAll done!")
