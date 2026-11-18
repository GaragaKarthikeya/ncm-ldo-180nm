"""Start-up detector alone: Vin = 1.71/1.8/1.89 V, Vout swept 0 -> 1.4 V. Trip point = Vout where k falls through Vin/2."""
import numpy as np
from spice import run
from design import D
def trip(vin):
    n = (f"Vin vin 0 {vin}\nVo out 0 0\nVod od 0 0.3\n"
         f"Msp k out vin vin pmos292p W={D['Wsp']*1e6:g}u L={D['Lsp']*1e6:g}u\n"
         f"Msn k out sd 0 nmos292p W={D['Wsn']*1e6:g}u L={D['Lsn']*1e9:g}n\nMsd sd sd 0 0 nmos292p W={D['Wsd']*1e6:g}u L={D['Lsn']*1e9:g}n\n"
         f"Mku vin k od 0 nmos292p W={D['Wku']*1e6:g}u L={D['Lku']*1e6:g}u\n.dc Vo 0 1.4 0.001\n")
    r = run('trip', n)[0]
    vo, k, iku = r['v(out)'].real, r['v(k)'].real, np.abs(r['id(mku)'].real)
    return float(np.interp(vin / 2, k[::-1], vo[::-1])), float(iku[0]), float(k[-1]), float(np.abs(r['id(msp)'].real[-1]))
if __name__ == '__main__':
    for v in (1.71, 1.8, 1.89):
        t, i0, k14, isp = trip(v)
        print(f"Vin {v}: trip Vout {t:.3f} V | kick current at Vout=0 (od=0.3 V) {i0*1e6:.2f} uA | k at Vout=1.4: {k14*1e3:.0f} mV | detector current {isp*1e9:.1f} nA")
