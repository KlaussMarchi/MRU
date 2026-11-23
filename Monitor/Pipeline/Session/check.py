# CONFERE QUE A SESSÃO EM BLOCOS (stream, mru.csv) SAI IGUAL BYTE A BYTE À DO load() INTEIRO NA MEMÓRIA (target.csv)
# USO: python Pipeline/Session/check.py   (reference: debug FORÇA O CAMINHO ANTIGO; null, O NOVO)
import numpy as np, os, subprocess, sys, tempfile, filecmp

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.py')
ROWS   = 450_000    # MAIS DE DOIS BLOCOS DE 200 000

rng  = np.random.default_rng(1)
t    = np.arange(ROWS) * 0.005
t[300_000:] -= t[300_000]    # O MRU REINICIOU: O time VOLTA A ZERO E O RELÓGIO GANHA OUTRO DESLOCAMENTO
host = 1.763e9 + np.arange(ROWS) * 0.005 + rng.uniform(0, 0.002, ROWS)
ints = rng.integers(-20000, 20000, (ROWS, 9))
header = 'host,layout,time,tmp,pitch,roll,yaw,ax,ay,az,wx,wy,wz,heave,heave_rate,q0,q1,q2,q3'


def line(i, mixed):
    tmp    = '' if i == ROWS - 10 else '352'    # NaN SÓ NO ÚLTIMO BLOCO: O pandas INTEIRO LÊ A COLUNA COMO float
    layout = 'raw' if mixed and i < 100_000 else 'scale'
    time   = '' if i == 5 else f'{t[i]:.3f}'
    return f'{host[i]:.6f},{layout},{time},{tmp},' + ','.join(map(str, ints[i])) + ',0.001,,,,,'


def run(folder, reference, mixed):
    name    = f'{reference}-{mixed}'
    journal = os.path.join(folder, f'rec-{name}')
    os.makedirs(journal)

    with open(os.path.join(journal, 'target.journal.csv'), 'w') as file:
        file.write(header + '\n' + '\n'.join(line(i, mixed) for i in range(ROWS)) + '\n')

    meta = os.path.join(folder, f'meta-{name}.json')
    open(meta, 'w').write(f'{{"mode": "teste", "reference": {"null" if reference == "new" else chr(34) + "debug" + chr(34)}, "warnings": []}}')
    subprocess.run([sys.executable, SCRIPT, journal, os.path.join(folder, name), meta], check=True, stdout=subprocess.DEVNULL)
    return os.path.join(folder, name, 'mru.csv' if reference == 'new' else 'target.csv')


with tempfile.TemporaryDirectory() as folder:
    for mixed in [True, False]:
        old, new = run(folder, 'old', mixed), run(folder, 'new', mixed)
        assert filecmp.cmp(old, new, shallow=False), f'o mru.csv em blocos difere do target.csv inteiro (layout {"misto" if mixed else "único"})'
        print('ok: mru.csv em blocos igual ao target.csv inteiro, layout', 'misto' if mixed else 'único', ROWS, 'linhas')
