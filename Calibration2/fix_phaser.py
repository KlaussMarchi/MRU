import json

with open('Analysis.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        if "class Phaser:" in source:
            new_phaser = """class Phaser:
    def __init__(self, target, reference):
        self.target    = target
        self.reference = reference

    def get(self, df):
        x_norm = normalize(df[self.target])
        y_norm = normalize(df[self.reference])

        correlation = np.correlate(y_norm, x_norm, mode='full')
        lags = np.arange(-len(df) + 1, len(df))
        lag  = lags[np.argmax(correlation)]
        return lag

    def set(self, df, lag):
        # Desloca todas as colunas que possuem o prefixo do sensor (SENSOR_PREFIX)
        # para alinhar todo o dispositivo em relação à referência.
        prefix = self.target.split('_')[0] + '_'
        cols_to_shift = [col for col in df.columns if col.startswith(prefix)]
        for col in cols_to_shift:
            df.loc[:, col] = df[col].shift(lag)
        df = df.dropna().reset_index(drop=True)
        return df


phaser = Phaser(SENSOR_PREFIX + 'roll', 'ref_roll')
lag    = phaser.get(df.loc[df.status == 'roll'])

df = phaser.set(df, lag)
print('System LAG:', lag, 'samples')"""
            
            cell['source'] = [line + '\n' for line in new_phaser.split('\n')]
            if cell['source'][-1] == '\n':
                cell['source'] = cell['source'][:-1]
            else:
                cell['source'][-1] = cell['source'][-1].rstrip('\n')

with open('Analysis.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print("Phaser fixed.")
