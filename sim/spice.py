"""Minimal LTspice batch runner and ASCII .raw reader.

Set LTSPICE_EXE if LTspice is not at the default ADI install path.
"""
import os, subprocess, pathlib, time, numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODELS = ROOT / 'models' / 'models_292p.txt'
EXE = os.environ.get('LTSPICE_EXE', r'C:\Program Files\ADI\LTspice\LTspice.exe')
WORK = ROOT / '.work'
_N = 0


def run(name, netlist, timeout=180):
    """Write the netlist, run LTspice -b -ascii, return a list of dicts (one per .step) of signal arrays."""
    global _N
    WORK.mkdir(parents=True, exist_ok=True)
    _N += 1
    cir = WORK / f'{name}_{os.getpid()}_{_N}.cir'  # unique file per run (avoids Windows file locks)
    cir.write_text(f'* {name}\n.include "{MODELS.as_posix()}"\n{netlist}\n.end\n', encoding='ascii')
    raw = cir.with_suffix('.raw')
    for attempt in range(4):  # LTspice batch occasionally cannot open a freshly written file on Windows
        r = subprocess.run([EXE, '-b', '-ascii', str(cir)], timeout=timeout,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode == 0 and raw.exists():
            return read_raw(raw)
        time.sleep(0.5 * (attempt + 1))
    log = cir.with_suffix('.log')
    raise RuntimeError(log.read_text(errors='ignore') if log.exists() else f'LTspice failed: {cir}')


def read_raw(path):
    txt = pathlib.Path(path).read_bytes()
    txt = txt.decode('utf-16-le') if txt[1:2] == b'\x00' else txt.decode('latin-1')
    header, values = txt.split('Values:', 1)
    nvar = int(header.split('No. Variables:')[1].split()[0])
    names = [l.split()[1].lower() for l in header.split('Variables:')[-1].strip().splitlines()]

    def num(x):
        try:
            return float(x)
        except ValueError:
            return float('nan')

    conv = lambda s: complex(*map(num, s.split(','))) if ',' in s else num(s)
    tok, data, i = values.split(), [], 0
    while i < len(tok):
        i += 1
        data.append([conv(t) for t in tok[i:i + nvar]])
        i += nvar
    a = np.array(data)
    x = a[:, 0].real
    cuts = [0] + [k for k in range(1, len(x)) if x[k] == x[0] and x[k - 1] != x[0]] + [len(x)]
    return [{n: a[s:e, j] for j, n in enumerate(names)} for s, e in zip(cuts[:-1], cuts[1:])]


db = lambda x: 20 * np.log10(np.abs(x))
