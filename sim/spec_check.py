"""Full specification check of the NCM-LDO (LTspice, TT, 27 C, ideal reference/bias). Writes results/specs.json.

Every number in the report's result table comes from this file.
"""
import json, numpy as np
from spice import ROOT, db
import ncm
from design import D, CAP_TOTAL, VOUT

LINES, R = (1.71, 1.8, 1.89), {}

# 1. DC output over line and load (current-source load)
vo = {f'{v}_{il*1e3:g}mA': ncm.op(v, il)['v(out)'] for v in LINES for il in (0, 10e-6, 0.1e-3, 1e-3, 8e-3, 10e-3)}
R['vout'] = vo
hv = [x for k, x in vo.items() if k.endswith(('_8mA', '_10mA'))]
R['vout_8_10mA'] = [min(hv), max(hv)]
R['vout_0_10mA'] = [min(vo.values()), max(vo.values())]
R['line_reg_mV'] = (vo['1.89_10mA'] - vo['1.71_10mA']) * 1e3
R['load_reg_8_10_mV'] = (vo['1.8_8mA'] - vo['1.8_10mA']) * 1e3
R['load_reg_0_10_mV'] = (vo['1.8_0mA'] - vo['1.8_10mA']) * 1e3

# 2. Quiescent current (1.8 V, 10 mA): supply current minus load current
o = ncm.op(1.8, 10e-3)
R['iq_uA'] = (-o['i(vin)'] - 10e-3) * 1e6
R['op'] = {k: v for k, v in o.items() if k.startswith(('v(', 'id('))}

# 3. Dropout at 10 mA: lowest Vin at which Vout is within 1 % of its 1.8 V value
r = ncm.run('drop', ncm.netlist(1.8, 10e-3, ac=False) + ncm.NODESET + '\n.dc Vin 1.3 1.9 0.001\n')[0]
vs, vv = r['v(vin)'].real, r['v(out)'].real
k = int(np.argmax(vv >= 0.99 * np.interp(1.8, vs, vv)))
R['dropout_mV'], R['dropout_vin'] = (vs[k] - vv[k]) * 1e3, vs[k]

# 4. PSRR over 10 Hz - 10 GHz (also reported over 10 kHz - 1 GHz), current and resistive (140 / 175 ohm) loads
ps = {}
for v in LINES:
    for il in (8e-3, 10e-3):
        for kind, ld in (('I', il), ('R', f'R{VOUT / il:g}')):
            f, h = ncm.psrr(v, ld)
            w, fw = ncm.worst(f, h, 10, 10e9)
            w2, fw2 = ncm.worst(f, h)
            ps[f'{kind}_{v}_{il*1e3:g}mA'] = dict(worst_dB=w, f_Hz=fw, worst_10k_1G_dB=w2, f_10k_1G_Hz=fw2,
                                                  at={str(x): float(np.interp(x, f, db(h))) for x in (10, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10)})
R['psrr'] = ps
R['psrr_worst_dB'] = max(x['worst_dB'] for x in ps.values())            # 10 Hz - 10 GHz
R['psrr_worst_10k_1G_dB'] = max(x['worst_10k_1G_dB'] for x in ps.values())
R['psrr_light'] = {f'{v}_{il*1e3:g}mA': ncm.worst(*ncm.psrr(v, il), 10, 10e9)[0] for v in (1.71, 1.89) for il in (0, 0.1e-3, 1e-3)}

# 5. Main loop: gain, crossover, phase margin from no load to full load
R['loop'] = {f'{v}_{il*1e3:g}mA': ncm.loopgain(v, il)[2] for v in (1.71, 1.89) for il in (0, 10e-6, 0.1e-3, 1e-3, 8e-3, 10e-3)}
R['pm_min_deg'] = min(x['pm_deg'] for x in R['loop'].values())
R['loop_gain_dB'] = [min(x['T0_dB'] for x in R['loop'].values()), max(x['T0_dB'] for x in R['loop'].values())]
R['fu_10mA_MHz'] = [R['loop'][f'{v}_10mA']['fu_Hz'] / 1e6 for v in (1.71, 1.89)]
R['ea_gain_dB'] = [min(x['A_ea_dB'] for x in R['loop'].values()), max(x['A_ea_dB'] for x in R['loop'].values())]

# 6. Output noise (1.8 V, 10 mA)
f, n = ncm.noise()
R['noise_1MHz_nV'] = float(np.interp(1e6, f, n) * 1e9)
R['noise_1k_100M_uVrms'] = float(np.sqrt(np.trapezoid(n ** 2, f)) * 1e6)

# 7. Load step 8 <-> 10 mA (10 ns edges) and line step 1.71 <-> 1.89 V (10 ns edges, 10 mA)
ls = {}
for v in (1.71, 1.89):
    t, y = ncm.load_step(v)
    v0, v1 = np.interp(19e-6, t, y), np.interp(59e-6, t, y)
    ls[f'{v}V'] = dict(under_mV=(v0 - y[(t > 20e-6) & (t < 60e-6)].min()) * 1e3, over_mV=(y[t > 60e-6].max() - v1) * 1e3)
R['load_step'] = ls
t, y, _ = ncm.line_step()
b = np.interp(19e-6, t, y)
R['line_step_mV'] = [(y[t > 20e-6].min() - b) * 1e3, (y[t > 20e-6].max() - b) * 1e3]

# 8. Capacitance
R['cap_total_pF'] = CAP_TOTAL * 1e12

out = ROOT / 'results' / 'specs.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(R, indent=1, default=float))
print(json.dumps({k: v for k, v in R.items() if k not in ('vout', 'psrr', 'loop', 'op')}, indent=1, default=float))

# 9. Start-up from 0 V (no .nodeset): Vin ramps of 0.1 / 10 / 100 us to 1.71 and 1.89 V, 140 ohm / 10 mA / no load
import startup
su = {}
for vfin in (1.71, 1.89):
    for tr in (100e-9, 10e-6, 100e-6):
        for load in ('R', 'I', 'none'):
            t, r = startup.run_startup(tr, load, vfin)
            su[f'{vfin}V_{tr*1e6:g}us_{load}'] = startup.summary(t, r, tr, vfin)
R['startup'] = su
R['startup_all_ok'] = all(abs(x['vend'] - 1.4) < 0.014 for x in su.values())
R['startup_settle_max_us'] = max(x['t_settle_us'] for x in su.values())
R['startup_peak_max_V'] = max(x['vmax'] for x in su.values())
R['startup_peak_loaded_V'] = max(x['vmax'] for k, x in su.items() if not k.endswith('none'))
out.write_text(json.dumps(R, indent=1, default=float))
print('startup', R['startup_all_ok'], R['startup_settle_max_us'], R['startup_peak_max_V'], R['startup_peak_loaded_V'])
