"""Simulated small-signal parameters of every transistor at the design's DC operating point (1.8 V, 10 mA).

LTspice's batch log does not list device operating points, so each MOSFET is re-simulated alone with ideal
sources at its exact simulated terminal voltages: AC on the gate gives gm and Cgg, AC on the drain gives gds and Cgd.
"""
import numpy as np
from spice import run
import ncm


def devices(vin=1.8, il=10e-3):
    o = ncm.op(vin, il)
    v = lambda n: 0.0 if n == '0' else o[f'v({n})']
    devs = []
    for l in ncm.netlist(vin, il, ac=False).splitlines():
        t = l.split()
        if t and t[0][0] == 'M':
            p = dict(x.split('=') for x in t[6:])
            devs.append(dict(name=t[0], d=t[1], g=t[2], s=t[3], b=t[4], model=t[5], W=p['W'], L=p['L'],
                             vd=v(t[1]), vg=v(t[2]), vs=v(t[3]), vb=v(t[4]), Id=abs(o[f'id({t[0].lower()})'])))

    def bench(ac_on):
        s = []
        for k, m in enumerate(devs):
            s += [f"Vd{k} d{k} 0 {m['vd']}" + (' AC 1' if ac_on == 'd' else ''),
                  f"Vg{k} g{k} 0 {m['vg']}" + (' AC 1' if ac_on == 'g' else ''),
                  f"Vs{k} s{k} 0 {m['vs']}", f"Vb{k} b{k} 0 {m['vb']}",
                  f"X{k} d{k} g{k} s{k} b{k} {m['model']} W={m['W']} L={m['L']}".replace(f"X{k}", f"M{k}")]
        return run('devop', '\n'.join(s) + '\n.ac list 1k 100Meg\n')[0]

    rg, rd = bench('g'), bench('d')
    w = 2 * np.pi * 100e6
    for k, m in enumerate(devs):
        m['gm'] = abs(rg[f'i(vd{k})'][0].real)
        m['Cgg'] = abs(rg[f'i(vg{k})'][1].imag) / w
        m['gds'] = abs(rd[f'i(vd{k})'][0].real)
        m['Cgd'] = abs(rd[f'i(vg{k})'][1].imag) / w
        m['gm_id'] = m['gm'] / m['Id']
        m['gmro'] = m['gm'] / m['gds']
        m['vgs'] = abs(m['vg'] - m['vs']); m['vds'] = abs(m['vd'] - m['vs'])
    return devs


if __name__ == '__main__':
    for m in devices():
        print(f"{m['name']:6s} W={m['W']:>8s} L={m['L']:>5s} Id={m['Id']*1e6:8.2f}uA gm/Id={m['gm_id']:5.1f} gm*ro={m['gmro']:6.1f} "
              f"|VGS|={m['vgs']:.3f} |VDS|={m['vds']:.3f} Cgg={m['Cgg']*1e15:7.1f}f Cgd={m['Cgd']*1e15:6.1f}f")
