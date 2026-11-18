"""NCM-LDO netlist and the standard measurements (LTspice batch).

Nodes: vin (supply), out (1.4 V), g (pass/mirror gate), r (reference drain, held = out), gc (cascode gate),
od (error-amp output), z (lag-lead), dd (driver drain), fbd (divider tap), tp (OTA tail), a2, d1, os, rsh, s1, s2.
"""
import numpy as np
from spice import run, db
from design import D

NODESET = ".nodeset V(out)=1.401 V(g)=1.048 V(r)=1.397 V(gc)=0.828 V(od)=0.612 V(tp)=1.069 V(a2)=0.636 V(d1)=0.790"


def netlist(vin=1.8, load=10e-3, ac=True, loop=False, d=D):
    """load: a number (A, current-source load), 'R<ohms>' (resistive load) or a PWL(...) string.
    ac: 1 V AC on the supply (PSRR).  loop: break the loop at the error-amp input gate for loop gain."""
    vsrc = f"Vin vin 0 {vin}" + (" AC 1" if ac else "") if isinstance(vin, (int, float)) else f"Vin vin 0 {vin}"
    ld = f"RL out 0 {load[1:]}" if isinstance(load, str) and load.startswith('R') else f"Iload out 0 {load}"
    s = [vsrc,
         # error amplifier (supply = out)
         f"Rtop out fbd {d['Rtop']}", f"Rbot fbd 0 {d['Rbot']}", f"Cff out fbd {d['Cff']}", f"Vref refd 0 {d['Vref']}",
         f"Itail out tp {d['Itail']}",
         f"Mpi1 a2 refd tp tp pmos292p W={d['Wpi']*1e6:g}u L={d['Lea']*1e9:g}n",
         f"Mpi2 od {'fbg' if loop else 'fbd'} tp tp pmos292p W={d['Wpi']*1e6:g}u L={d['Lea']*1e9:g}n",
         f"Mnl1 a2 a2 0 0 nmos292p W={d['Wnl']*1e6:g}u L={d['Lea']*1e9:g}n",
         f"Mnl2 od a2 0 0 nmos292p W={d['Wnl']*1e6:g}u L={d['Lea']*1e9:g}n",
         f"Rz od z {d['Rz']}", f"Cz z 0 {d['Cz']}",
         # driver
         f"Mdrv dd od 0 0 nmos292p W={d['Wdrv']*1e6:g}u L={d['Ldrv']*1e6:g}u",
         f"Mcn g vcn dd 0 nmos292p W={d['Wcn']*1e6:g}u L=540n", f"Vcn vcn 0 {d['Vcn']}",
         # mirror power stage
         f"Mc g gc r r pmos292p W={d['Wc']*1e6:g}u L=180n",
         f"Mref r g vin vin pmos292p W={d['Wpass']*1e6/d['N']:.3f}u L=180n",
         f"Mpass out g vin vin pmos292p W={d['Wpass']*1e6:.0f}u L=180n",
         f"Cn vin r {d['Cn']}", f"Rg vin g {d['Rg']}",
         # tracking amplifier (supply = out)
         f"Mfo out out os 0 nmos292p W={d['Wf']*1e6:g}u L=180n", f"Ifo os 0 {d['If']}",
         f"Mfr out r rsh 0 nmos292p W={d['Wf']*1e6:g}u L=180n", f"Ifr rsh 0 {d['If']}",
         f"M1 d1 os s1 0 nmos292p W={d['Wp']*1e6:g}u L=180n", f"M2 gc rsh s2 0 nmos292p W={d['Wp']*1e6:g}u L=180n",
         f"It1 s1 0 {d['It']}", f"It2 s2 0 {d['It']}", f"Rdeg s1 s2 {d['Rdeg']}", f"Cdeg s1 s2 {d['Cdeg']}",
         f"Ml1 d1 d1 out out pmos292p W={d['Wl']*1e6:g}u L=180n", f"Ml2 gc d1 out out pmos292p W={d['Wl']*1e6:g}u L=180n",
         # load and output capacitor
         ld, f"Co out 0 {d['Cout']}", ".options numdgt=12"]
    if loop:
        s.append("Vt fbg fbd 0 AC 1")
    return '\n'.join(s) + '\n'


def _seed(vin, il):
    """Both amplifiers run from Vout, so the DC solution is not unique: seed every case with a .nodeset.
    Light loads get their own solution (first solved from the 8-10 mA seed)."""
    if isinstance(il, (int, float)) and il < 1e-3:
        o = op(vin, il, seed=NODESET)
        return '.nodeset ' + ' '.join(f"V({k})={o[f'v({k})']:.4f}" for k in
                                      ('out', 'g', 'r', 'gc', 'od', 'tp', 'a2', 'd1', 'dd', 'fbd'))
    return NODESET


def op(vin=1.8, il=10e-3, seed=None, d=D):
    n = netlist(vin, il, ac=False, d=d) + (seed or _seed(vin, il)) + '\n'
    r = run('op', n + f'.dc Vin {vin} {vin + 0.001} 0.001\n')[0]
    return {k: float(v.real[0]) for k, v in r.items()}


def psrr(vin=1.8, il=10e-3, fmin=10, fmax=10e9, ppd=50, d=D):
    r = run('psrr', netlist(vin, il, d=d) + _seed(vin, il) + f'\n.ac dec {ppd} {fmin} {fmax}\n')[0]
    return r['frequency'].real, r['v(out)']


def worst(f, h, lo=1e4, hi=1e9):
    b = (f >= lo) & (f <= hi); y = db(h)[b]
    return float(y.max()), float(f[b][np.argmax(y)])


def loopgain(vin=1.8, il=10e-3, d=D):
    """Series AC source between the divider tap and the error-amp input gate (an exact break: a gate draws no DC)."""
    r = run('loop', netlist(vin, il, ac=False, loop=True, d=d) + _seed(vin, il) + '\n.ac dec 100 10 10G\n')[0]
    f = r['frequency'].real; T = -r['v(fbd)'] / r['v(fbg)']
    m = db(T); ph = np.unwrap(np.angle(T)) * 180 / np.pi
    c = np.where((m[:-1] >= 0) & (m[1:] < 0))[0]
    fu = float(f[c[-1]]) if len(c) else np.nan
    pm = float(min((180 + ph[k]) % 360 for k in c)) if len(c) else np.nan
    return f, T, dict(T0_dB=float(m[0]), fu_Hz=fu, pm_deg=pm)


def noise(vin=1.8, il=10e-3, d=D):
    r = run('noise', netlist(vin, il, d=d) + NODESET + '\n.noise V(out) Vin dec 20 1k 100Meg\n')[0]
    return r['frequency'].real, np.abs(r['v(onoise)'])


def load_step(vin=1.8, lo=8e-3, hi=10e-3, d=D):
    pwl = f"PWL(0 {lo} 20u {lo} 20.01u {hi} 60u {hi} 60.01u {lo})"
    r = run('lstep', netlist(vin, pwl, ac=False, d=d) + NODESET + '\n.tran 0 100u 0 1n\n')[0]
    return r['time'].real, r['v(out)'].real


def line_step(il=10e-3, lo=1.71, hi=1.89, d=D):
    pwl = f"PWL(0 {lo} 20u {lo} 20.01u {hi} 60u {hi} 60.01u {lo})"
    r = run('vstep', netlist(pwl, il, ac=False, d=d) + NODESET + '\n.tran 0 100u 0 1n\n')[0]
    return r['time'].real, r['v(out)'].real, r['v(vin)'].real
