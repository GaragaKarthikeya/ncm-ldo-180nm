"""Power-up check: Vin ramps 0 -> Vfinal from an all-zero state (no .nodeset), with the start-up kick in the netlist.

Ideal current sources cannot be used here (they force current even with no supply), so every bias source is made
compliant: it scales with the voltage across it and with Vin (as a real bias generator powered from Vin would).
Vref (0.5 V) and Vcn (0.9 V) come up with Vin. The load is 140 ohm, a compliant 10 mA sink, or none.
"""
import re, numpy as np
from spice import run
import ncm


def startup_netlist(tr=10e-6, load='R', vfin=1.8):
    n = ncm.netlist(1.8, 10e-3, ac=False)
    up = "limit(V(vin)/1.2,0,1)"                       # bias generators reach full value once Vin > 1.2 V
    n = n.replace("Vin vin 0 1.8", f"Vin vin 0 PWL(0 0 {tr} {vfin})")
    n = re.sub(r"Vref refd 0 (\S+)", lambda m: f"Bref refd 0 V={m[1]}*{up}", n)
    n = re.sub(r"Vcn vcn 0 (\S+)", lambda m: f"Bcn vcn 0 V={m[1]}*{up}", n)
    n = re.sub(r"Itail out tp (\S+)", lambda m: f"Btail out tp I={m[1]}*{up}*limit(V(out,tp)/0.1,0,1)", n)
    for nm, nd in (('Ifo', 'os'), ('Ifr', 'rsh'), ('It1', 's1'), ('It2', 's2')):
        n = re.sub(rf"{nm} {nd} 0 (\S+)", lambda m: f"B{nm[1:]} {nd} 0 I={m[1]}*{up}*limit(V({nd})/0.1,0,1)", n)
    ld = {'R': "RL out 0 140", 'I': "Bload out 0 I=10m*limit(V(out)/0.2,0,1)", 'none': ""}[load]
    return n.replace("Iload out 0 0.01", ld)


def run_startup(tr=10e-6, load='R', vfin=1.8, after=30e-6):
    T = tr + after
    r = run('startup', startup_netlist(tr, load, vfin) + '.save V(out) V(vin) V(k) V(g) V(od) Id(Mku)\n'
            + f'.tran 0 {T} 0 {min(max(tr / 200, 2e-9), 20e-9)}\n')[0]
    return r['time'].real, r


def summary(t, r, tr, vfin):
    vo = r['v(out)'].real
    vreg = vo[-1]
    ok = np.abs(vo - vreg) <= 0.01 * vreg
    bad = np.where(~ok)[0]
    tset = t[bad[-1]] - tr if len(bad) else 0.0
    return dict(vend=vreg, vmax=vo.max(), t_settle_us=tset * 1e6, k_end=r['v(k)'].real[-1], imk_end=abs(r['id(mku)'].real[-1]))


if __name__ == '__main__':
    for vfin in (1.71, 1.89):
        for tr in (100e-9, 10e-6, 100e-6):
            for load in ('R', 'I', 'none'):
                t, r = run_startup(tr, load, vfin)
                s = summary(t, r, tr, vfin)
                print(f"Vin->{vfin} ramp {tr*1e6:7.2f}us load {load:4s}: Vout {s['vend']:.4f} (max {s['vmax']:.4f}) "
                      f"settled (1%) {s['t_settle_us']:6.2f}us after ramp | k {s['k_end']*1e3:5.0f} mV, I(Mk) {s['imk_end']*1e9:6.1f} nA", flush=True)
