"""LaTeX tables for the report, generated from results/specs.json and the simulated operating point."""
import json
from spice import ROOT
from design import D
from devop import devices

S = json.loads((ROOT / 'results' / 'specs.json').read_text())
OUT = ROOT / 'report' / 'tables'
OUT.mkdir(parents=True, exist_ok=True)
ok = r'\textbf{Met}'


def results():
    ls = max(max(v['under_mV'], v['over_mV']) for v in S['load_step'].values())
    lo, hi = S['vout_0_10mA']
    rows = [
        ('Input range', '1.71--1.89 V', '1.71--1.89 V', ok),
        (r'$V_{\rm OUT}$, 0--10 mA, all $V_{\rm IN}$', r'1.4 V $\pm$1\%', f'{lo:.4f}--{hi:.4f} V', ok),
        ('Line regulation (10 mA)', '--', f"{S['line_reg_mV']:.2f} mV", '--'),
        ('Load regulation 8$\\to$10 / 0$\\to$10 mA', '--', f"{S['load_reg_8_10_mV']:.2f} / {S['load_reg_0_10_mV']:.1f} mV", '--'),
        ('Dropout at 10 mA', r'$\le$300 mV', f"{S['dropout_mV']:.0f} mV", ok),
        (r'Worst PSRR, 10 Hz--10 GHz\textsuperscript{a}', r'$\le-30$ dB', f"{S['psrr_worst_dB']:.1f} dB", ok),
        ('DC loop gain, 0--10 mA', '--', f"{S['loop_gain_dB'][0]:.0f}--{S['loop_gain_dB'][1]:.0f} dB", '--'),
        ('Error-amplifier DC gain', '--', f"{S['ea_gain_dB'][0]:.1f}--{S['ea_gain_dB'][1]:.1f} dB", '--'),
        ('Loop crossover at 10 mA', '--', f"{min(S['fu_10mA_MHz']):.1f} MHz", '--'),
        (r'Quiescent current\textsuperscript{b}', r'$\le$300 $\mu$A', f"{S['iq_uA']:.0f} $\\mu$A", ok),
        ('Total capacitance', r'$\le$1 nF', f"{S['cap_total_pF']:.0f} pF", ok),
        ('Phase margin, 0--10 mA', r'$\ge45^\circ$', f"{S['pm_min_deg']:.1f}$^\\circ$ min", ok),
        (r'Noise at 1 MHz', r'$\le$20 nV/$\sqrt{\rm Hz}$', f"{S['noise_1MHz_nV']:.1f} nV/$\\sqrt{{\\rm Hz}}$", ok),
        (r'Load step 8$\leftrightarrow$10 mA, 10 ns', r'$\pm$20 mV', f'$\\pm${ls:.1f} mV', ok),
        (r'Line step 1.71$\leftrightarrow$1.89 V, 10 ns', '--', f"{S['line_step_mV'][0]:.1f} / +{S['line_step_mV'][1]:.1f} mV", '--'),
        (r'Start-up from 0 V\textsuperscript{c}', 'Starts', f"$\\le${S['startup_settle_max_us']:.0f} $\\mu$s",
         ok if S['startup_all_ok'] else r'\textbf{Not met}'),
    ]
    body = '\n'.join(' & '.join(r) + r' \\' for r in rows)
    (OUT / 'results.tex').write_text(r"""\begin{table}[!t]
\centering
\caption{Simulated performance against the specification}
\label{tab:results}
\footnotesize
\setlength{\tabcolsep}{2pt}
\begin{tabular}{@{}lccc@{}}
\toprule
Parameter & Target & NCM-LDO & Status \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}

\vspace{2pt}
\parbox{\columnwidth}{\scriptsize LTspice, typical models, 27$^\circ$C, ideal reference and bias sources.
\textsuperscript{a}Over 1.71/1.8/1.89 V, 8/10 mA, current-source and resistive loads (12 cases).
\textsuperscript{b}At 1.8 V, 10 mA; supply current minus load current.
\textsuperscript{c}$V_{\rm IN}$ ramps of 0.1/10/100 $\mu$s to 1.71/1.89 V, 140-$\Omega$/10-mA/no load (18 cases); settling to 1\% after the ramp ends; peak """ + f"{S['startup_peak_max_V']:.3f}" + r""" V.}
\end{table}
""")


def sizing():
    role = dict(Mpass='Pass device', Mref='Mirror reference', Mc='Cascode ($r=V_{\\rm OUT}$)', Mcn='Driver cascode',
                Mdrv='Driver', Mpi1='EA input pair', Mnl1='EA mirror load', Mfo='Follower ($V_{\\rm OUT}$)',
                Mfr='Follower ($r$)', M1='Tracking pair', Ml1='Tracking load')
    devs = {m['name']: m for m in devices()}
    rows = []
    for n, r in role.items():
        m = devs[n]
        L = m['L'].replace('n', ' nm').replace('u', ' $\\mu$m')
        W = m['W'].replace('u', '')
        sym = n.replace('M', 'M$_{', 1) + '}$' if n != 'M1' else 'M$_{1,2}$'
        sym = {'Mpi1': 'M$_{\\rm PI1,2}$', 'Mnl1': 'M$_{\\rm NL1,2}$', 'Ml1': 'M$_{\\rm L1,2}$', 'Mpass': 'M$_{\\rm PASS}$',
               'Mref': 'M$_{\\rm REF}$', 'Mc': 'M$_{\\rm C}$', 'Mcn': 'M$_{\\rm CN}$', 'Mdrv': 'M$_{\\rm DRV}$',
               'Mfo': 'M$_{\\rm FO}$', 'Mfr': 'M$_{\\rm FR}$'}.get(n, sym)
        Id = f"{m['Id']*1e3:.2f} mA" if m['Id'] > 1e-3 else f"{m['Id']*1e6:.1f} $\\mu$A"
        rows.append(f"{sym} & {r} & {W} / {L} & {Id} & {m['gm_id']:.1f} & {m['gmro']:.0f} \\\\")
    rows.append(r'\midrule')
    for n, sym, r in (('Msp', 'M$_{\\rm SP}$', 'Start-up detector'), ('Msn', 'M$_{\\rm SN,SD}$', 'Start-up detector'),
                      ('Mku', 'M$_{\\rm KU}$', 'Start-up kick')):
        m = devs[n]
        L = m['L'].replace('n', ' nm').replace('u', ' $\\mu$m')
        Id = f"{m['Id']*1e9:.0f} nA" if m['Id'] > 1e-9 else 'off'
        rows.append(f"{sym} & {r} & {m['W'].replace('u', '')} / {L} & {Id} & -- & -- \\\\")
    (OUT / 'sizing.tex').write_text(r"""\begin{table}[!t]
\centering
\caption{Transistor sizes and simulated operating point (1.8 V, 10 mA)}
\label{tab:sizing}
\footnotesize
\setlength{\tabcolsep}{1.6pt}
\begin{tabular}{@{}llcccc@{}}
\toprule
Device & Role & $W$ ($\mu$m) / $L$ & $I_D$ & $g_m/I_D$ & $g_mr_o$ \\
\midrule
""" + '\n'.join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def budget():
    devs = {m['name']: m for m in devices()}
    irg = devs['Mref']['vgs'] / D['Rg']
    items = [('Mirror reference ($I_D/N$)', devs['Mref']['Id']), ('$R_G$ (gate pull-up)', irg),
             ('Error-amplifier tail', D['Itail']), ('Tracking followers (2$\\times$)', 2 * D['If']),
             ('Tracking pair tails (2$\\times$)', 2 * D['It']), ('Feedback divider', 1.4 / (D['Rtop'] + D['Rbot'])),
             ('Start-up detector', devs['Msp']['Id'])]
    rows = '\n'.join(f"{a} & {b*1e6:.1f} \\\\" for a, b in items)
    (OUT / 'budget.tex').write_text(r"""\begin{table}[!t]
\centering
\caption{Quiescent-current budget (1.8 V, 10 mA)}
\label{tab:budget}
\footnotesize
\begin{tabular}{@{}lc@{}}
\toprule
Branch & Current ($\mu$A) \\
\midrule
""" + rows + r"""
\midrule
Sum of branches & """ + f"{sum(b for _, b in items)*1e6:.1f}" + r""" \\
Simulated (supply $-$ load) & """ + f"{S['iq_uA']:.1f}" + r""" \\
\bottomrule
\end{tabular}
\end{table}
""")


if __name__ == '__main__':
    results(); sizing(); budget(); print('tables written to', OUT)
