"""Report figures (LTspice runs of design.py), drawn in the IEEE single-column style. Writes report/figures/*.pdf."""
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator
from spice import ROOT, db
import ncm, conventional
from techplot import _load, _ROWS, WREF
from devop import devices

FIG = ROOT / 'report' / 'figures'
FIG.mkdir(parents=True, exist_ok=True)
STYLE = [dict(color='k', ls='-', lw=1.6), dict(color='r', ls=(0, (5, 3)), lw=1.5), dict(color='b', ls=':', lw=1.8)]
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 8,
                     'axes.labelsize': 9, 'axes.labelweight': 'bold', 'axes.linewidth': .8, 'xtick.direction': 'in',
                     'ytick.direction': 'in', 'xtick.top': True, 'ytick.right': True, 'legend.fontsize': 6.5,
                     'legend.framealpha': 1, 'legend.fancybox': False, 'legend.edgecolor': 'k', 'pdf.fonttype': 42,
                     'mathtext.fontset': 'stix'})
LIM = dict(color='.3', ls='-.', lw=.7)


def decorate(ax):
    if ax.get_xscale() == 'log':
        ax.xaxis.set_major_locator(LogLocator(base=10, numticks=12))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10), numticks=100))
    ax.grid(True, which='major', color='.65', lw=.35); ax.grid(True, which='minor', color='.85', lw=.25)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontweight('bold')


def save(fig, name):
    fig.tight_layout(pad=.4, h_pad=.5)
    fig.savefig(FIG / f'{name}.pdf', bbox_inches='tight', pad_inches=.025)
    fig.savefig(FIG / f'{name}.png', dpi=220, bbox_inches='tight', pad_inches=.025)
    plt.close(fig); print('wrote', name)


def fig_conventional():
    f, h = ncm.psrr(1.8, 10e-3); fc, hc = conventional.psrr(1.8, 10e-3)
    fig, ax = plt.subplots(figsize=(3.45, 2.05))
    ax.semilogx(fc, db(hc), label='Conventional LDO (100 uA, 839 pF)'.replace('uA', r'$\mu$A'), **STYLE[1])
    ax.semilogx(f, db(h), label=r'NCM-LDO (289 $\mu$A, 1 nF)', **STYLE[0])
    ax.axhline(-30, **LIM); ax.set(xlim=(10, 1e10), ylim=(-90, 5), xlabel='Frequency (Hz)', ylabel='PSRR (dB)')
    ax.legend(loc='lower left'); decorate(ax); save(fig, 'psrr_conventional')


def fig_envelope():
    curves = {}
    for v in (1.71, 1.8, 1.89):
        for il in (8e-3, 10e-3):
            for ld in (il, f'R{1.4 / il:g}'):
                f, h = ncm.psrr(v, ld); curves[(v, il, isinstance(ld, str))] = db(h)
    env = np.max(np.array(list(curves.values())), axis=0)
    fig, ax = plt.subplots(figsize=(3.45, 2.05))
    ax.semilogx(f, env, label='12-point envelope', **STYLE[0])
    ax.semilogx(f, curves[(1.71, 10e-3, False)], label='1.71 V / 10 mA', **STYLE[1])
    ax.semilogx(f, curves[(1.89, 8e-3, False)], label='1.89 V / 8 mA', **STYLE[2])
    ax.axhline(-30, **LIM); ax.set(xlim=(10, 1e10), ylim=(-90, -20), xlabel='Frequency (Hz)', ylabel='PSRR (dB)')
    ax.legend(loc='lower left'); decorate(ax); save(fig, 'psrr_envelope')


def fig_loop():
    fig, axs = plt.subplots(2, 1, figsize=(3.45, 2.9), sharex=True)
    for il, lab, st in zip((10e-6, 1e-3, 10e-3), (r'10 $\mu$A', '1 mA', '10 mA'), (STYLE[2], STYLE[1], STYLE[0])):
        f, T, m = ncm.loopgain(1.89, il)
        axs[0].semilogx(f, db(T), label=f"{lab}: PM {m['pm_deg']:.0f}" + r'$^\circ$', **st)
        axs[1].semilogx(f, np.unwrap(np.angle(T)) * 180 / np.pi, **st)
    axs[0].axhline(0, color='.4', lw=.7); axs[0].set(ylabel='Loop gain (dB)', ylim=(-60, 100))
    axs[0].legend(loc='lower left', ncol=1)
    axs[1].axhline(-180, **LIM); axs[1].set(ylabel='Phase (deg)', xlabel='Frequency (Hz)', xlim=(10, 1e9), ylim=(-270, 30))
    for a in axs:
        decorate(a)
    save(fig, 'loop_gain')


def fig_pm():
    loads = [10e-6, 30e-6, 0.1e-3, 0.3e-3, 1e-3, 3e-3, 8e-3, 10e-3]
    fig, axs = plt.subplots(2, 1, figsize=(3.45, 2.6), sharex=True)
    for v, st in zip((1.71, 1.89), STYLE):
        m = [ncm.loopgain(v, il)[2] for il in loads]
        axs[0].semilogx(np.array(loads) * 1e3, [x['pm_deg'] for x in m], marker='o', ms=2.5, label=f'{v} V', **st)
        axs[1].semilogx(np.array(loads) * 1e3, [x['fu_Hz'] / 1e6 for x in m], marker='o', ms=2.5, **st)
    axs[0].axhline(45, **LIM); axs[0].set(ylabel='PM (deg)', ylim=(30, 80)); axs[0].legend(loc='lower right')
    axs[1].set(ylabel='Crossover (MHz)', xlabel='Load current (mA)', ylim=(0, 25))
    for a in axs:
        decorate(a)
    save(fig, 'pm_vs_load')


def fig_load_step():
    fig, axs = plt.subplots(2, 1, figsize=(3.45, 2.65), sharex=True)
    for v, st in zip((1.71, 1.89), STYLE):
        t, y = ncm.load_step(v)
        for ax, t0, lab in ((axs[0], 20e-6, f'{v} V'), (axs[1], 60e-6, None)):
            k = (t > t0 - 1e-6) & (t < t0 + 6e-6)
            ax.plot((t[k] - t0) * 1e6, (y[k] - np.interp(t0 - 0.5e-6, t, y)) * 1e3, label=lab, **st)
    for i, ax in enumerate(axs):
        ax.axhline(20, color='.3', ls='--', lw=.6); ax.axhline(-20, color='.3', ls='--', lw=.6)
        ax.set(ylabel=r'$\Delta V_{\rm OUT}$ (mV)', ylim=(-25, 25), xlim=(-0.5, 5))
        ax.set_title('(a) 8 to 10 mA' if i == 0 else '(b) 10 to 8 mA', loc='left', fontsize=8, fontweight='bold', pad=3)
        decorate(ax)
    axs[0].legend(loc='upper right', ncol=2, fontsize=6); axs[1].set_xlabel(r'Time from load transition ($\mu$s)')
    save(fig, 'load_step')


def fig_line_step():
    t, y, vi = ncm.line_step()
    fig, axs = plt.subplots(2, 1, figsize=(3.45, 2.4), sharex=True)
    k = (t > 19e-6) & (t < 26e-6)
    axs[0].plot((t[k] - 20e-6) * 1e6, vi[k], **STYLE[0]); axs[0].set(ylabel=r'$V_{\rm IN}$ (V)', ylim=(1.68, 1.92))
    axs[1].plot((t[k] - 20e-6) * 1e6, (y[k] - np.interp(19e-6, t, y)) * 1e3, **STYLE[0])
    axs[1].set(ylabel=r'$\Delta V_{\rm OUT}$ (mV)', xlabel=r'Time from line step ($\mu$s)', ylim=(-3, 3))
    for a in axs:
        decorate(a)
    save(fig, 'line_step')


def fig_noise():
    f, n = ncm.noise()
    fig, ax = plt.subplots(figsize=(3.45, 1.85))
    ax.loglog(f, n * 1e9, **STYLE[0]); ax.plot([1e6], [np.interp(1e6, f, n) * 1e9], 'ko', ms=3)
    ax.axhline(20, **LIM); ax.set(xlim=(1e3, 1e8), xlabel='Frequency (Hz)', ylabel=r'Noise (nV/$\sqrt{\rm Hz}$)')
    decorate(ax); save(fig, 'noise')


def fig_tracking():
    """Why PSRR flattens at ~ -31 dB: above ~30 MHz the gate stops following Vin and r stops following Vout."""
    r = ncm.run('trk', ncm.netlist(1.89, 10e-3) + ncm.NODESET + '\n.ac dec 50 100k 3G\n')[0]
    f = r['frequency'].real
    fig, ax = plt.subplots(figsize=(3.45, 2.05))
    ax.semilogx(f, db(r['v(out)']), label=r'$V_{\rm OUT}/V_{\rm IN}$ (PSRR)', **STYLE[0])
    ax.semilogx(f, db(1 - r['v(g)']), label=r'Gate error $1-V_{\rm G}/V_{\rm IN}$', **STYLE[1])
    ax.semilogx(f, db(r['v(r)'] - r['v(out)']), label=r'Tracking error $(V_{\rm R}-V_{\rm OUT})/V_{\rm IN}$', **STYLE[2])
    ax.set(xlim=(1e5, 3e9), ylim=(-70, 10), xlabel='Frequency (Hz)', ylabel='Magnitude (dB)')
    ax.legend(loc='upper left'); decorate(ax); save(fig, 'tracking')


def fig_techplot():
    """Techplots used for sizing, with every transistor's simulated operating point marked."""
    g = _load('0p4')
    devs = {m['name']: m for m in devices()}
    fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.9))
    groups = [('p', 180e-9, 'PMOS 180 nm', STYLE[0], ['Mpass', 'Mref', 'Mc', 'Ml1']),
              ('p', 540e-9, 'PMOS 540 nm', STYLE[1], ['Mpi1']),
              ('n', 540e-9, 'NMOS 540 nm', STYLE[2], ['Mnl1', 'Mcn'])]
    for kind, L, lab, st, names in groups:
        s = np.isclose(g(1), L)
        x = g(_ROWS[kind]['gm_id'])[s]; ok = (x > 3) & (x < 24)
        axs[0].semilogy(x[ok], g(_ROWS[kind]['id_w'])[s][ok], label=lab, **st)
        axs[1].plot(x[ok], g(_ROWS[kind]['gmro'])[s][ok], **st)
        for nm in names:
            m = devs[nm]; W = float(m['W'].rstrip('u')) * 1e-6
            axs[0].plot(m['gm_id'], m['Id'] / W, 'o', color=st['color'], ms=3, mfc='w')
            axs[1].plot(m['gm_id'], m['gmro'], 'o', color=st['color'], ms=3, mfc='w')
    axs[0].annotate('Mpass', (devs['Mpass']['gm_id'], devs['Mpass']['Id'] / 1223e-6), xytext=(13, 20), fontsize=6,
                    arrowprops=dict(arrowstyle='-', lw=.5))
    axs[0].set(xlabel=r'$g_m/I_D$ (1/V)', ylabel=r'$I_D/W$ (A/m)', ylim=(0.05, 200))
    axs[1].set(xlabel=r'$g_m/I_D$ (1/V)', ylabel=r'$g_m r_o$ (V/V)', ylim=(0, 160))
    axs[0].legend(loc='lower left', fontsize=5.5, handlelength=1.6)
    for a in axs:
        decorate(a)
    save(fig, 'techplot')


if __name__ == '__main__':
    import sys
    todo = sys.argv[1:] or [k[4:] for k in globals() if k.startswith('fig_')]
    for k in todo:
        globals()['fig_' + k]()
