"""Netlist design/NCM_LDO.asc with LTspice and check it is the same circuit as ncm.netlist() (element by element, node mapping)."""
import subprocess, pathlib, sys
from spice import EXE
from ncm import netlist

asc = pathlib.Path(__file__).resolve().parents[1] / 'design' / 'NCM_LDO.asc'
subprocess.run([EXE, '-netlist', str(asc)], check=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
sch = {}
for l in asc.with_suffix('.net').read_bytes().decode('utf-8', 'replace').splitlines():
    t = l.split()
    if t and t[0][0] in 'MRCVI' and not t[0].startswith('.'):
        n = 4 if t[0][0] == 'M' else 2
        sch[t[0]] = t[1:1 + n]
ref = {}
for l in netlist(1.8, 'R140').splitlines():
    t = l.split()
    if t and t[0][0] in 'MRCVI':
        n = 4 if t[0][0] == 'M' else 2
        ref[t[0]] = ['out' if x == 'fbo' else x for x in t[1:1 + n]]
assert set(sch) == set(ref), set(sch) ^ set(ref)
m, bad = {}, []
for k in ref:
    s = sch[k]
    if k[0] in 'RC' and [m.get(x, x) for x in s[::-1]] == ref[k]:
        s = s[::-1]  # a resistor or capacitor drawn the other way round is the same element
    for a, b in zip(s, ref[k]):
        if m.setdefault(a, b) != b:
            bad.append((k, a, b, m[a]))
inv = {}
for a, b in m.items():
    inv.setdefault(b, []).append(a)
merged = {b: a for b, a in inv.items() if len(a) > 1}
nc = [k for k, v in sch.items() if any(x.startswith('NC_') for x in v)]
print('elements', len(sch), '| mismatches', bad, '| split nets', merged, '| NC pins', nc)
print('OK' if not bad and not merged and not nc else 'DIFFERENT')
