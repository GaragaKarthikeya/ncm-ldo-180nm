"""Builds design_sheet/NCM_LDO_Design.xlsx: the gm/Id design flow (course format) with live formulas.

Column C = hand calculation / techplot value, E = LTspice (simulated operating point), G = error %.
Techplot values are looked up here (techplot.py) and written as numbers; everything derived from them is a formula.
"""
import json, numpy as np, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from spice import ROOT
from techplot import lookup
from design import D, PASS
from devop import devices
import ncm

S = json.loads((ROOT / 'results' / 'specs.json').read_text())
DEV = {m['name']: m for m in devices()}
L10 = ncm.loopgain(1.8, 10e-3)[2]
um = lambda w: float(w.rstrip('u'))

wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Design flow'
for col, w in zip('ABCDEFGHI', (2, 34, 14, 10, 14, 4, 10, 2, 70)):
    ws.column_dimensions[col].width = w
H1 = Font(bold=True, size=12, color='FFFFFF'); FILL1 = PatternFill('solid', fgColor='1F3864')
H2 = Font(bold=True); FILL2 = PatternFill('solid', fgColor='D9E1F2'); CHOICE = PatternFill('solid', fgColor='FFF2CC')
thin = Border(bottom=Side(style='hair', color='999999'))
row, REF = [2], {}


def step(title, cols=('Hand / Techplots', 'Units', 'Simulation', 'Error', 'Comments')):
    row[0] += 1
    c = ws.cell(row[0], 2, title); c.font = H1
    for k in range(2, 10):
        ws.cell(row[0], k).fill = FILL1
    row[0] += 1
    for k, t in zip((3, 4, 5, 7, 9), cols):
        c = ws.cell(row[0], k, t); c.font = H2; c.fill = FILL2
    ws.cell(row[0], 2).fill = FILL2
    row[0] += 1


def put(name, label, hand, unit='', sim=None, comment='', choice=False, fmt='0.000'):
    """hand / sim: a number or a formula string using {names} of earlier rows (hand column C, sim column E)."""
    r = row[0]; REF[name] = r
    sub = lambda s, col: s.format(**{k: f'{col}{v}' for k, v in REF.items()}) if isinstance(s, str) else s
    ws.cell(r, 2, label)
    ch = ws.cell(r, 3, ('=' + sub(hand, 'C')) if isinstance(hand, str) else hand)
    if hand is None:
        ch.value = '-'
    ws.cell(r, 4, unit)
    if sim is not None:
        ws.cell(r, 5, ('=' + sub(sim, 'E')) if isinstance(sim, str) else sim)
        if hand is not None and hand != '-':
            g = ws.cell(r, 7, f'=IFERROR((E{r}-C{r})/E{r},"")'); g.number_format = '0.0%'
    ws.cell(r, 9, comment).alignment = Alignment(wrap_text=False)
    for k in (3, 5):
        ws.cell(r, k).number_format = fmt
    if choice:
        ch.fill = CHOICE
    for k in range(2, 10):
        ws.cell(r, k).border = thin
    row[0] += 1


def note(text):
    ws.cell(row[0], 9, text).font = Font(italic=True, color='555555'); row[0] += 1


ws.cell(1, 2, 'NCM-LDO (neutralized current-mode LDO), 180 nm: gm/Id design sheet').font = Font(bold=True, size=14)
ws.cell(2, 2, 'Garaga Karthikeya (IMT2024073), Analog CMOS VLSI Design, IIIT Bangalore. Yellow = design choice; '
              'techplot numbers looked up at the stated L and |VDS|; simulation = LTspice operating point at 1.8 V, 10 mA.').font = Font(italic=True)

step('Step 1: List the specifications and classify them', ('Value', 'Units', '', '', 'Class / comment'))
put('vinmin', 'Vin (min)', 1.71, 'V', comment='Shared 1.8 V rail, -5 %')
put('vinnom', 'Vin (nominal)', 1.8, 'V')
put('vout', 'Vout', 1.4, 'V', comment='Moderate: +/-1 %; PLL/VCO supply')
put('imax', 'Iload | max', 10, 'mA', comment='Moderate: 8-10 mA operating, stable down to 0')
put('imin', 'Iload | min (step)', 8, 'mA')
put('psrr', 'PSRR, worst 10 Hz-10 GHz', -30, 'dB', comment='Aggressive: broadband, no hump allowed (relaxed from -40 dB to hold the current budget)')
put('iq', 'Iquiescent', 300, 'uA', comment='Moderate')
put('ctot', 'Total on-chip capacitance', 1, 'nF', comment='Aggressive: everything on chip')
put('dvstep', 'Load-step error (8<->10 mA, 10 ns)', 20, 'mV', comment='Moderate')
put('noise', 'Output noise at 1 MHz', 20, 'nV/rtHz', comment='Moderate')
put('pmspec', 'Phase margin, 0-10 mA', 45, 'deg', comment='Relaxed')

step('Step 2: Evaluate interim design goals')
put('head', 'Headroom (Vin,min - Vout)', '{vinmin}-{vout}', 'V', comment='Only 310 mV: no room for a series isolator; the pass device sets dropout')
put('di', 'dI (load step)', '({imax}-{imin})/1000', 'A')
put('dv', 'dV allowed', '{dvstep}/1000', 'V')
put('coutb', 'Cout available (budget - Cz - Cff - Cn)', D['Cout'], 'F', choice=True, fmt='0.00E+00', comment='~890 pF left after the compensation capacitors')
put('dt', 'dt = Cout*dV/dI (loop response time)', '{coutb}*{dv}/{di}', 's', fmt='0.00E+00', comment='Cout alone must hold the output until the loop responds')
put('fumin', 'fu,min ~ 1/(2*pi*dt)', '1/(2*PI()*{dt})', 'Hz', fmt='0.00E+00', comment='-> main-loop crossover must reach ~18 MHz at 10 mA')
note('PSRR above fu cannot come from loop gain: it has to come from cancelling the pass-device leak paths (gm, gds, Cgd).')

step('Step 3: Power FET sizing (Mpass, PMOS, L = 180 nm)')
p = DEV['Mpass']
put('gmid', 'gm/Id', 10, '1/V', sim=p['gm_id'], choice=True, comment='Moderate inversion: VSG ~0.66 V keeps W (and Cgd) reasonable inside 310 mV headroom')
put('idp', 'Id', '{imax}/1000', 'A', sim=p['Id'], fmt='0.000E+00')
put('idw', 'Id/W', PASS['id_w'], 'A/m', sim=p['Id'] / (um(p['W']) * 1e-6), comment='Techplot PMOS L=180n, |VDS|=0.31 V (interpolated)')
put('wp', 'W', '{idp}/{idw}*1E6', 'um', sim=um(p['W']), fmt='0.0')
put('gmp', 'gm', '{gmid}*{idp}', 'A/V', sim=p['gm'], fmt='0.0000')
put('gmrop', 'gm*ro', PASS['gmro'], 'V/V', sim=p['gmro'], fmt='0.0', comment='Simulated |VDS| = 0.40 V at 1.8 V (techplot at 0.31 V): ro grows with VDS')
put('rop', 'ro', '{gmrop}/{gmp}', 'ohm', sim='{gmrop}/{gmp}', fmt='0.0')
put('cggp', 'Cgg', PASS['cgg'], 'F', sim=p['Cgg'], fmt='0.00E+00')
put('ftp', 'ft', PASS['ft'], 'Hz', sim='{gmp}/(2*PI()*{cggp})', fmt='0.00E+00')
put('cgdp', 'Cgd', PASS['cgd'], 'F', sim=p['Cgd'], fmt='0.00E+00', comment='This Cgd is the leak the Cn neutralisation must cancel')
put('vsgp', '|VSG|', PASS['vgs'], 'V', sim=p['vgs'])
put('floor', 'Leak gain if the gate stops following Vin: gm*(ro||RL)', '20*LOG10({gmp}*{rop}*({vout}/{idp})/({rop}+{vout}/{idp}))', 'dB', fmt='0.0',
    comment='Every 1 % of gate-tracking error reaches the output with this gain: the gate must follow Vin to better than ~-50 dB')

step('Step 4: Mirror power stage (Mref, cascode Mc, Cn, Rg)')
mref, mc = DEV['Mref'], DEV['Mc']
put('n', 'Mirror ratio N = Wpass/Wref', D['N'], '', choice=True, comment='Pass current = N x reference current: the driver works on Id/N, gds is matched through r = Vout')
put('iref', 'Iref = Id/N', '{idp}/{n}', 'A', sim=mref['Id'], fmt='0.000E+00')
put('wref', 'Wref = W/N', '{wp}/{n}', 'um', sim=um(mref['W']), fmt='0.000')
put('gmref', 'gm,ref = gm/Id * Iref', '{gmid}*{iref}', 'A/V', sim=mref['gm'], fmt='0.000E+00')
put('cn', 'Cn ~ Cgd(Mpass)', '{cgdp}', 'F', sim=D['Cn'], fmt='0.00E+00', comment='Injects the jw*Cgd*Vin current the mirror would otherwise multiply by N; final value tuned to 1.0 pF')
put('gmidc', 'Mc gm/Id', 16, '1/V', sim=mc['gm_id'], choice=True, comment='Weak/moderate inversion for gm per uA: Mc must pass Cn current into g up to ~300 MHz')
put('idwc', 'Mc Id/W', lookup('p', 180e-9, 16, 0.4, 'id_w'), 'A/m', sim=mc['Id'] / (um(mc['W']) * 1e-6), comment='Techplot PMOS L=180n, |VDS|=0.4 V')
put('wc', 'Mc W = Iref/(Id/W)', '{iref}/{idwc}*1E6', 'um', sim=um(mc['W']), fmt='0.0', comment='Rounded up to 40 um')
put('fcn', 'Cn-path ceiling gm,c/(2*pi*Cn)', '{gmidc}*{iref}/(2*PI()*{cn})', 'Hz', fmt='0.00E+00', comment='Above this the neutralising current saturates: sets the ~-31 dB floor at 40-400 MHz')
put('cg', 'Gate-node capacitance Cg ~ Cgg(pass)+Cgg(ref)', '{cggp}*(1+1/{n})', 'F', fmt='0.00E+00')
put('fpg', 'Gate pole (gm,ref)/(2*pi*Cg) at 10 mA', '{gmref}/(2*PI()*{cg})', 'Hz', fmt='0.00E+00')
put('fpgl', 'Gate pole at 10 uA load (Iref ~ 1.7 uA, subthreshold)', '25*1.7E-6/(2*PI()*{cg})', 'Hz', fmt='0.00E+00', comment='Falls onto the crossover: PM collapses to ~20 deg without Rg')
put('rg', 'Rg (Vin -> g)', D['Rg'], 'ohm', choice=True, comment='Load-independent floor on the gate-node conductance; its current is not mirrored')
put('fpgr', 'Gate pole floor 1/(2*pi*Rg*Cg)', '1/(2*PI()*{rg}*{cg})', 'Hz', fmt='0.00E+00')
put('irg', 'Rg current = VSG/Rg', '{vsgp}/{rg}', 'A', sim=mref['vgs'] / D['Rg'], fmt='0.000E+00')

step('Step 5: Error amplifier (Vout-powered, PMOS input, NMOS mirror load, L = 540 nm)')
pi, nl = DEV['Mpi1'], DEV['Mnl1']
put('vref', 'Vref', D['Vref'], 'V', choice=True)
put('beta', 'beta = Vref/Vout', '{vref}/{vout}', 'V/V')
put('idiv', 'Divider current', 5e-6, 'A', choice=True, fmt='0.0E+00')
put('rtot', 'Rtop + Rbot = Vout/Idiv', '{vout}/{idiv}', 'ohm', sim=D['Rtop'] + D['Rbot'], fmt='0')
put('rbot', 'Rbot = beta*(Rtop+Rbot)', '{beta}*{rtot}', 'ohm', sim=D['Rbot'], fmt='0')
put('itail', 'Tail current', D['Itail'], 'A', choice=True, fmt='0.0E+00')
put('gmidpi', 'Input pair gm/Id', 13, '1/V', sim=pi['gm_id'], choice=True, comment='Low noise and offset per uA; L = 540 nm for gain')
put('idwpi', 'Input pair Id/W', lookup('p', 540e-9, 13, 0.4, 'id_w'), 'A/m', sim=pi['Id'] / (um(pi['W']) * 1e-6), comment='Techplot PMOS L=540n, |VDS|=0.4 V')
put('wpi', 'Input pair W = (Itail/2)/(Id/W)', '{itail}/2/{idwpi}*1E6', 'um', sim=um(pi['W']), fmt='0.0')
put('gmpi', 'gm,in', '{gmidpi}*{itail}/2', 'A/V', sim=pi['gm'], fmt='0.000E+00')
put('gmidnl', 'Mirror load gm/Id', 10, '1/V', sim=nl['gm_id'], choice=True)
put('idwnl', 'Mirror load Id/W', lookup('n', 540e-9, 10, 0.4, 'id_w'), 'A/m', sim=nl['Id'] / (um(nl['W']) * 1e-6), comment='Techplot NMOS L=540n, |VDS|=0.4 V')
put('wnl', 'Mirror load W', '{itail}/2/{idwnl}*1E6', 'um', sim=um(nl['W']), fmt='0.0')
put('gmrop_ea', 'Input pair gm*ro', lookup('p', 540e-9, 13, 0.4, 'gmro'), 'V/V', sim=pi['gmro'], fmt='0.0')
put('gmron_ea', 'Mirror load gm*ro', lookup('n', 540e-9, 10, 0.4, 'gmro'), 'V/V', sim=nl['gmro'], fmt='0.0', comment='Diode-side |VDS| = 0.64 V in simulation vs 0.4 V techplot: ro is higher')
put('aea', 'OTA DC gain gm,in*(ro,p || ro,n)', '{gmpi}/({gmpi}/{gmrop_ea}+{gmidnl}*{itail}/2/{gmron_ea})', 'V/V', fmt='0.0')

step('Step 6: Driver (Mdrv, cascode Mcn) and tracking amplifier')
md, mcn, m1, mf = DEV['Mdrv'], DEV['Mcn'], DEV['M1'], DEV['Mfo']
put('idrv', 'Driver current = Iref + Irg', '{iref}+{irg}', 'A', sim=md['Id'], fmt='0.000E+00')
put('gmiddrv', 'Mdrv gm/Id (L = 1 um)', 9, '1/V', sim=md['gm_id'], choice=True, comment='Long L: high output resistance, low mismatch in the current that sets Iref')
put('gmdrv', 'gm,drv', '{gmiddrv}*{idrv}', 'A/V', sim=md['gm'], fmt='0.000E+00')
put('idwdrv', 'Mdrv Id/W', lookup('n', 1.08e-6, 9, 0.4, 'id_w'), 'A/m',
    sim=md['Id'] / (um(md['W']) * 1e-6), comment='Techplot NMOS at the nearest L = 1.08 um, |VDS|=0.4 V (drawn L = 1 um, simulated |VDS| = 0.23 V)')
put('wdrv', 'Mdrv W', '{idrv}/{idwdrv}*1E6', 'um', sim=um(md['W']), fmt='0.0')
put('itrk', 'Tracking pair current (each side)', D['It'], 'A', choice=True, fmt='0.0E+00')
put('gmidtrk', 'Tracking pair gm/Id', 20, '1/V', sim=m1['gm_id'], choice=True, comment='Weak inversion: maximum gm per uA for bandwidth')
put('iflw', 'Follower current (each)', D['If'], 'A', choice=True, fmt='0.0E+00', comment='Level-shift r and Vout down so the NMOS pair fits under a 1.4 V supply')

step('Step 7: Compensation (output-pole dominant, lag-lead, feed-forward)')
put('cout', 'Cout', D['Cout'], 'F', choice=True, fmt='0.00E+00')
put('rz', 'Rz', D['Rz'], 'ohm', choice=True)
put('cz', 'Cz', D['Cz'], 'F', choice=True, fmt='0.0E+00')
put('fz', 'Lag-lead zero 1/(2*pi*Rz*Cz)', '1/(2*PI()*{rz}*{cz})', 'Hz', fmt='0.00E+00', comment='Above it the OTA gain is gm,in*Rz: the loop gain no longer falls with the OTA')
put('cff', 'Cff (across Rtop)', D['Cff'], 'F', choice=True, fmt='0.0E+00')
put('fzff', 'Cff zero 1/(2*pi*Rtop*Cff)', '1/(2*PI()*({rtot}-{rbot})*{cff})', 'Hz', fmt='0.00E+00', comment='Above it beta -> 1: removes the divider pole and the divider noise')
put('neff', 'Effective mirror gain gm,pass/(gm,ref+1/Rg)', '{gmp}/({gmref}+1/{rg})', 'A/A', fmt='0.0')
put('fu', 'Crossover fu = gm,in*Rz*gm,drv*Neff/(2*pi*Cout)', '{gmpi}*{rz}*{gmdrv}*{neff}/(2*PI()*{cout})', 'Hz', sim=L10['fu_Hz'], fmt='0.00E+00',
    comment='beta = 1 above the Cff zero; hand value ignores the gate pole (hence higher)')
put('pm', 'PM ~ 90 - atan(fu/f,gate)', '90-DEGREES(ATAN({fu}/({fpg}+{fpgr})))', 'deg', sim=L10['pm_deg'], fmt='0.0', comment='Other poles (od, dd, tracking loop) take the rest')
put('dvh', 'Load-step error dI/(2*pi*fu*Cout)', '{di}/(2*PI()*{fu}*{cout})*1000', 'mV', sim=S['load_step']['1.71V']['under_mV'], fmt='0.0')

step('Step 8: Start-up kick (powered from Vin)')
note('Both amplifiers run from Vout, so Vout = 0 is a stable state: without a kick the LDO never starts (verified in simulation).')
import startup, trip
_trip = trip.trip(1.8)
_t, _r = startup.run_startup(100e-9, 'R', 1.8, after=20e-6)
_t0 = float(_t[np.argmax(_r['v(out)'].real > 0.1)] - 100e-9)
put('vthsd', 'Detector stack: |VGS| per device (weak inversion)', lookup('n', 540e-9, 22, 0.4, 'vgs'), 'V', choice=False,
    comment='Techplot NMOS L=540n at gm/Id = 22 (the stack carries only ~nA-uA)')
put('vtrip', 'Trip point ~ 2 VGS (Msn + Msd)', '2*{vthsd}', 'V', sim=_trip[0], comment='Must lie above 0 and below the regulated 1.4 V with margin')
put('ikick', 'Kick current into OD (Mku, W/L 0.5/4 um)', 14e-6, 'A', sim=_trip[1], fmt='0.0E+00', choice=True, comment='Sized small: a stronger kick causes chatter / overshoot')
put('tdel', 'Delay before Vout rises ~ Cz*VGS(Mdrv)/Ikick', '{cz}*0.6/{ikick}', 's', sim=_t0, fmt='0.00E+00',
    comment='OD must charge Cz up to the driver threshold; Cz holds the kick, so the hand-over does not chatter')

step('Step 9: Performance results', ('Expected', 'Units', 'Simulated', 'Error', 'Comment'))
put('r_iq', 'Quiescent current (sum of branches)', '({iref}+{irg}+{itail}+2*{iflw}+2*{itrk}+{idiv})*1E6', 'uA', sim=S['iq_uA'], fmt='0.0',
    comment='Iref + Rg + OTA tail + 2 followers + 2 tracking tails + divider')
put('r_cap', 'Total capacitance', '({cout}+{cz}+{cff}+{cn}+' + f"{D['Cdeg']})*1E12", 'pF', sim=S['cap_total_pF'], fmt='0.0')
put('r_vout', 'Vout (1.8 V, 10 mA)', '{vout}', 'V', sim=S['vout']['1.8_10mA'], fmt='0.0000', comment='Target 1.4 V +/-1 %: met')
put('r_psrr', 'Worst PSRR, 10 Hz-10 GHz', None, 'dB', sim=S['psrr_worst_dB'], fmt='0.0', comment='Target <= -30 dB: met (1.71/1.8/1.89 V, 8/10 mA, R and I loads)')
put('r_pm', 'Minimum phase margin 0-10 mA', None, 'deg', sim=S['pm_min_deg'], fmt='0.0', comment='Target >= 45 deg: met (1.71 and 1.89 V, 0 to 10 mA)')
put('r_noise', 'Noise at 1 MHz', None, 'nV/rtHz', sim=S['noise_1MHz_nV'], fmt='0.0', comment='Target <= 20 nV/rtHz: met')
put('r_drop', 'Dropout at 10 mA', None, 'mV', sim=S['dropout_mV'], fmt='0.0', comment='Target <= 300 mV: met')

# second sheet: every transistor's simulated operating point
w2 = wb.create_sheet('Operating points')
hdr = ['Device', 'W', 'L', 'Id (uA)', 'gm/Id (1/V)', 'gm (mS)', 'gm*ro', '|VGS| (V)', '|VDS| (V)', 'Cgg (fF)', 'Cgd (fF)']
for k, h in enumerate(hdr, 1):
    c = w2.cell(1, k, h); c.font = H2; c.fill = FILL2; w2.column_dimensions[chr(64 + k)].width = 12
for i, m in enumerate(DEV.values(), 2):
    for k, v in enumerate([m['name'], m['W'], m['L'], m['Id'] * 1e6, m['gm_id'], m['gm'] * 1e3, m['gmro'], m['vgs'], m['vds'],
                           m['Cgg'] * 1e15, m['Cgd'] * 1e15], 1):
        c = w2.cell(i, k, v)
        if isinstance(v, float):
            c.number_format = '0.00'
ws.freeze_panes = 'C3'
wb.calculation.fullCalcOnLoad = True
out = ROOT / 'design_sheet' / 'NCM_LDO_Design.xlsx'
out.parent.mkdir(exist_ok=True); wb.save(out); print('wrote', out)
