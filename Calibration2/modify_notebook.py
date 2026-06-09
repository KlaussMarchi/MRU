import json

with open('Analysis.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        # CELL 1
        if "SENSOR_PREFIX = 'target_'" in source and "getStatus" in source:
            source = source.replace("getStatus     = lambda var: 'pitch' if var in ['pitch', 'wx', 'ay'] else 'roll'\n", "")
            
        # LinearFit
        if "class LinearFit:" in source:
            source = source.replace("status=getStatus(var)", "status=var")
            source = source.replace("status    = 'pitch' if axis_name in ['pitch', 'wx', 'ay'] else 'roll'", "status    = axis_name")
            
        # CalibrationAnalysis
        if "class CalibrationAnalysis:" in source:
            new_ca = """class CalibrationAnalysis:
    def __init__(self, model, df, var, status):
        self.status = status
        self.model = model
        self.df_dyn_plot = df.loc[df.status == status]
        self.df_stat_plot  = df.loc[df.status == 'static']
        self.var = var

    def getRMS(self, values):
        if len(values) == 0: return 0.0
        return float(np.sqrt(np.mean(np.array(values)**2)))

    def update(self):
        yRef_stat = self.df_stat_plot['ref_'    + self.var]
        yMod_stat = self.df_stat_plot['model_'  + self.var]
        yTgt_stat = self.df_stat_plot['target_' + self.var]
        
        if self.model:
            idx = self.model.variables.index(self.var)
            yRef_dyn = self.df_dyn_plot['ref_'   + self.var]
            yMod_dyn = self.df_dyn_plot['model_' + self.var]
            
            r2   = float(self.model.metrics[self.var]['r2'])
            mae  = float(self.model.metrics[self.var]['mae'])
            rmse = float(self.model.metrics[self.var]['rmse'])
            correctionMatrixRow = [float(c) for c in self.model.M[idx, :].tolist()]
            
            rms_dyn = self.getRMS(yMod_dyn - yRef_dyn)
            ptp_dyn = (np.max(yRef_dyn) - np.min(yRef_dyn)) if len(yRef_dyn) > 0 else 0
            rms_scale_factor = (rms_dyn / ptp_dyn) if ptp_dyn != 0 else 0.0
        else:
            r2 = mae = rmse = 0.0
            correctionMatrixRow = []
            rms_dyn = rms_scale_factor = 0.0

        time_drift = 0.0
        if len(self.df_stat_plot) > 1:
            time_drift = float(np.polyfit(self.df_stat_plot['time'], yRef_stat - yMod_stat, 1)[0] * 3600)
            
        self.metrics = {
            'r2': float(r2),
            'mae': float(mae),
            'rmse': float(rmse),
            'precision': float(2*np.std(yRef_stat - yMod_stat)) if len(yRef_stat) > 0 else 0.0,

            'rms_stat': self.getRMS(yMod_stat - yRef_stat), 
            'rms_dyn':  rms_dyn,
            
            'rms_scale_factor': rms_scale_factor,
            'std_stat': float(np.std(yMod_stat, ddof=1)) if len(yMod_stat) > 0 else 0.0,
            'time_drift': time_drift,
            'correctionMatrixRow': correctionMatrixRow, 
        }

    def display(self):
        metrics = self.metrics.copy()
        if 'correctionMatrixRow' in metrics:
            del metrics['correctionMatrixRow']
        display(pd.DataFrame([metrics]))"""
            source = new_ca
            
        # Main Loop
        if "groups = {" in source and "spacing_seconds =" in source:
            new_loop = """groups = {
    'Euler Angles':  ['pitch', 'roll'],
    'Gyroscope':     ['wx', 'wy', 'wz'],
    'Accelerometer': ['ax', 'ay', 'az']
}

spacing_seconds = 30
history = {}

for label, variables in groups.items():
    if label == 'Euler Angles':
        model = LinearFit(df, variables, fuse=False) 
        model.update()
        model.display()
    else:
        model = None
    
    for idx, var in enumerate(variables):
        if var not in ['pitch', 'roll', 'wx', 'wy', 'wz', 'ax', 'ay', 'az']:
            continue

        status = var if var in ['pitch', 'roll'] else 'static'
        
        if model:
            df['model_'  + var] = df[[f'{SENSOR_PREFIX}{v}' for v in variables]].values @ model.M[idx] + model.B[idx]
        else:
            df['model_'  + var] = df[f'{SENSOR_PREFIX}{var}']

        print('-'*85, var.upper(), '-'*85)
        
        cal = CalibrationAnalysis(model, df, var, status)
        cal.update()
        cal.display()

        if model:
            model.plot(idx)
            plt.show()

            plt.figure(figsize=(20, 5))
            plotCurves(df, f'model_{var}', f'ref_{var}', limits=(0, 1))
            plt.show()
    
        if model:
            model.metrics[var] = cal.metrics
        history[var]       = cal.metrics
                
        if model:
            exporter = ResultExporter('Certificate', var, model)
            exporter.export()

            df_dyn_plot   = df.loc[df.status == status]
            df_stat_plot  = df.loc[df.status == 'static']

            # ----------------------------- GRÁFICOS DE ZOOM ----------------------------- 
            print(f'Dinamic Tests ({var})')
            spacing = spacing_seconds/(df_dyn_plot.time.max() - df_dyn_plot.time.min())
            
            plt.figure(figsize=(20, 10))
            plt.subplot(2, 2, 1); plotCurves(df_dyn_plot, f'model_{var}', f'ref_{var}', limits=(0, 1))
            plt.subplot(2, 2, 2); plotCurves(df_dyn_plot, f'model_{var}', f'ref_{var}', limits=(0.15, 0.15+spacing))
            plt.subplot(2, 2, 3); plotCurves(df_dyn_plot, f'model_{var}', f'ref_{var}', limits=(0.45, 0.45+spacing))
            plt.subplot(2, 2, 4); plotCurves(df_dyn_plot, f'model_{var}', f'ref_{var}', limits=(0.8, 0.8+spacing))
            plt.show()

            print(f'Static Tests ({var})')
            spacing = spacing_seconds/(df_stat_plot.time.max() - df_stat_plot.time.min())
            
            plt.figure(figsize=(20, 10))
            plt.subplot(2, 2, 1); plotCurves(df_stat_plot, f'model_{var}', f'ref_{var}', limits=(0, 1), norm=False)
            plt.subplot(2, 2, 2); plotCurves(df_stat_plot, f'model_{var}', f'ref_{var}', limits=(0.15, 0.15+spacing), norm=False)
            plt.subplot(2, 2, 3); plotCurves(df_stat_plot, f'model_{var}', f'ref_{var}', limits=(0.55, 0.55+spacing), norm=False)
            plt.subplot(2, 2, 4); plotCurves(df_stat_plot, f'model_{var}', f'ref_{var}', limits=(0.85, 0.85+spacing), norm=False)
            plt.show(); print('\\n\\n')"""
            source = new_loop
            
        cell['source'] = [line + '\n' for line in source.split('\n')]
        # Remove the extra newline at the end if it wasn't there
        if cell['source'][-1] == '\n':
            cell['source'] = cell['source'][:-1]
        else:
            cell['source'][-1] = cell['source'][-1].rstrip('\n')

with open('Analysis.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print("Modification complete.")
