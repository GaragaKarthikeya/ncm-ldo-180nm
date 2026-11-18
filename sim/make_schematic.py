"""NCM-LDO LTspice schematic, laid out by hand like a textbook drawing (NCM_LDO.asc).

Topology drawn as circuits are drawn by people:
  - VIN rail across the top of the power stage; VOUT rail across the top of the two Vout-powered amplifiers
  - power stack in one column: Mref -> (r) -> Mc -> (g) -> Mcn -> (dd) -> Mdrv, with Mpass beside Mref (gates tied)
  - error amplifier: PMOS pair on a tail source, NMOS mirror load, divider, lag-lead Rz-Cz on its output
  - tracking amplifier: two followers flanking a degenerated NMOS pair with a PMOS mirror load
Only the two long feedback nets (r, gc) and the divider tap (fb) use net labels.
Values come from design.py through ncm.netlist(), so the drawing and the simulations cannot drift apart.
"""
import pathlib
from ncm import netlist, op, NODESET

OUT = pathlib.Path(__file__).resolve().parents[1] / 'design' / 'NCM_LDO.asc'

# ---- element values from the simulated netlist ----
vals = {}
for l in netlist(1.8, 'R140').splitlines():
    t = l.split()
    if not t or t[0].startswith('.') or t[0] == 'Rfb':
        continue
    if t[0][0] == 'M':
        vals[t[0]] = (t[5], ' '.join(t[6:]))
    elif t[0][0] == 'V':
        vals[t[0]] = (' '.join(t[3:]), '')
    else:
        vals[t[0]] = (t[3], '')

# ---- placements: name -> (symbol, x, y, orientation) ----
P = {
    # error amplifier
    'Rtop': ('res', -128, -160, 'R0'), 'Rbot': ('res', -128, 0, 'R0'), 'Cff': ('cap', -272, -144, 'R0'),
    'Vref': ('voltage', 96, 80, 'R0'),
    'Itail': ('current', 432, -144, 'R0'),
    'Mpi1': ('pmos4', 272, 128, 'M180'), 'Mpi2': ('pmos4', 592, 128, 'R180'),
    'Mnl1': ('nmos4', 368, 224, 'M0'), 'Mnl2': ('nmos4', 496, 224, 'R0'),
    'Rz': ('res', 640, 208, 'R0'), 'Cz': ('cap', 640, 352, 'R0'),
    # supply, power stack, driver
    'Vin': ('voltage', 880, -224, 'R0'), 'Vcn': ('voltage', 944, 336, 'R0'),
    'Cn': ('cap', 992, -112, 'R0'), 'Rg': ('res', 1216, -272, 'R0'),
    'Mref': ('pmos4', 1152, -64, 'R180'), 'Mpass': ('pmos4', 1312, -64, 'M180'),
    'Mc': ('pmos4', 1056, 128, 'M180'),
    'Mcn': ('nmos4', 1056, 224, 'R0'), 'Mdrv': ('nmos4', 1056, 416, 'R0'),
    # load
    'RL': ('res', 1488, 48, 'R0'), 'Co': ('cap', 1600, 64, 'R0'),
    # start-up kick (below the load, connected by the vin / out / g labels)
    'Msp': ('pmos4', 1520, 400, 'M180'), 'Msn': ('nmos4', 1520, 432, 'R0'), 'Msd': ('nmos4', 1520, 528, 'R0'),
    'Mku': ('nmos4', 1824, 400, 'R0'),
    # tracking amplifier
    'Mfo': ('nmos4', 1840, -112, 'R0'), 'Ifo': ('current', 1888, 64, 'R0'),
    'Ml1': ('pmos4', 2384, -48, 'R180'), 'Ml2': ('pmos4', 2512, -48, 'M180'),
    'M1': ('nmos4', 2288, 96, 'R0'), 'M2': ('nmos4', 2608, 96, 'M0'),
    'Rdeg': ('res', 2496, 224, 'R90'), 'Cdeg': ('cap', 2496, 400, 'R90'),
    'It1': ('current', 2336, 288, 'R0'), 'It2': ('current', 2560, 288, 'R0'),
    'Mfr': ('nmos4', 3056, -112, 'M0'), 'Ifr': ('current', 3008, 64, 'R0'),
}
assert sorted(P) == sorted(vals), (sorted(set(P) ^ set(vals)))

# ---- wires as polylines (every segment orthogonal) ----
W = [
    # error amplifier: VOUT rail, divider, reference
    [(-112, -192), (432, -192)], [(-112, -144), (-112, -192)], [(432, -144), (432, -192)],
    [(-112, -64), (-112, 16)], [(-112, -16), (-160, -16)], [(-112, 96), (-112, 144)],
    [(-256, -144), (-256, -176), (-112, -176)], [(-256, -80), (-256, -56), (-112, -56)],   # Cff across Rtop
    [(96, 96), (96, 48), (272, 48)], [(96, 176), (96, 224)],
    # tail and pair
    [(432, -64), (432, -16)], [(320, -16), (544, -16)], [(320, 32), (320, -16)], [(544, 32), (544, -16)],
    [(320, 80), (368, 80), (368, -16)], [(544, 80), (496, 80), (496, -16)],
    [(592, 48), (640, 48)],
    # mirror load
    [(320, 128), (320, 224)], [(544, 128), (544, 224)],
    [(368, 304), (496, 304)], [(320, 176), (432, 176), (432, 304)],
    [(320, 320), (320, 368)], [(544, 320), (544, 368)],
    [(320, 272), (272, 272), (272, 320)], [(544, 272), (592, 272), (592, 320)],
    # od -> Rz/Cz and on to the driver gate
    [(544, 176), (800, 176), (800, 560), (1008, 560), (1008, 496), (1056, 496)],
    [(656, 176), (656, 224)], [(656, 304), (656, 352)], [(656, 416), (656, 464)],
    # supply rail and Vin
    [(880, -208), (880, -256), (1408, -256)], [(880, -128), (880, -80)],
    [(1008, -112), (1008, -256)], [(1104, -160), (1104, -256)], [(1360, -160), (1360, -256)],
    [(1104, -112), (1056, -112), (1056, -256)], [(1360, -112), (1408, -112), (1408, -256)],
    # mirror gates, r node, Cn, cascode
    [(1152, -144), (1312, -144)], [(1232, -176), (1232, -144)],   # Rg: top pin on the VIN rail, bottom to g
    [(1104, -64), (1104, 32)], [(1008, -48), (1008, -16), (1104, -16)],
    [(1104, 80), (1152, 80), (1152, -16), (1104, -16)],
    [(1056, 48), (1008, 48)],
    # g node: Mc drain -> Mcn drain, and back up to the mirror gates
    [(1104, 128), (1104, 224)], [(1104, 176), (1296, 176), (1296, -144)],
    # driver
    [(1056, 304), (944, 304), (944, 352)], [(944, 432), (944, 480)],
    [(1104, 320), (1104, 368), (1104, 416)], [(1104, 512), (1104, 560)],
    [(1104, 272), (1152, 272), (1152, 320)], [(1104, 464), (1152, 464), (1152, 512)],
    # output and load, then up to the tracking amplifier's VOUT rail
    [(1360, -64), (1360, 16), (1712, 16), (1712, -192), (3008, -192)],
    [(1504, 16), (1504, 64)], [(1504, 144), (1504, 192)],
    [(1616, 16), (1616, 64)], [(1616, 128), (1616, 176)],
    # start-up kick: Msp pull-up from vin, Msn+Msd stack pull-down (gates = out), node k drives follower Mku (vin -> od)
    [(1568, 304), (1568, 272)], [(1568, 352), (1616, 352), (1616, 288), (1568, 288)], [(1520, 320), (1472, 320)],
    [(1568, 400), (1568, 432)], [(1520, 512), (1472, 512)], [(1568, 480), (1600, 480)],
    [(1520, 608), (1488, 608), (1488, 528), (1568, 528)], [(1568, 576), (1600, 576)], [(1568, 624), (1568, 656)],
    [(1568, 416), (1792, 416), (1792, 480), (1824, 480)],
    [(1872, 400), (1872, 368)], [(1872, 496), (1872, 528)], [(1872, 448), (1920, 448)],
    # follower for Vout (Mfo) and its sink
    [(1888, -112), (1888, -192)], [(1840, -32), (1792, -32), (1792, -192)],
    [(1888, -16), (1888, 64)], [(1888, -64), (1936, -64), (1936, -16)], [(1888, 144), (1888, 192)],
    [(1888, 16), (2192, 16), (2192, 176), (2288, 176)],
    # PMOS mirror load
    [(2336, -144), (2336, -192)], [(2560, -144), (2560, -192)],
    [(2336, -96), (2288, -96), (2288, -192)], [(2560, -96), (2608, -96), (2608, -192)],
    [(2384, -128), (2512, -128)],
    [(2336, -48), (2336, 96)], [(2336, 32), (2448, 32), (2448, -128)],
    [(2560, -48), (2560, 96)], [(2560, 32), (2656, 32)],
    # NMOS pair, degeneration, tails
    [(2336, 144), (2400, 144), (2400, 192)], [(2560, 144), (2512, 144), (2512, 192)],
    [(2336, 192), (2336, 288)], [(2336, 240), (2400, 240)], [(2384, 240), (2384, 416), (2432, 416)],
    [(2560, 192), (2560, 288)], [(2480, 240), (2560, 240)], [(2496, 416), (2512, 416), (2512, 240)],
    [(2336, 368), (2336, 416)], [(2560, 368), (2560, 416)],
    # follower for r (Mfr) and its sink
    [(3008, -112), (3008, -192)], [(3056, -32), (3104, -32)],
    [(3008, -16), (3008, 64)], [(3008, -64), (2960, -64), (2960, -16)], [(3008, 144), (3008, 192)],
    [(3008, 16), (2704, 16), (2704, 176), (2608, 176)],
]
F = [  # net labels and grounds
    (-112, -192, 'out'), (-160, -16, 'fb'), (640, 48, 'fb'), (-112, 144, '0'), (96, 224, '0'),
    (320, 368, '0'), (544, 368, '0'), (272, 320, '0'), (592, 320, '0'), (656, 464, '0'),
    (880, -256, 'vin'), (880, -80, '0'), (1008, 48, 'gc'), (1008, -16, 'r'),
    (944, 480, '0'), (1104, 560, '0'), (1152, 320, '0'), (1152, 512, '0'),
    (1712, 16, 'out'), (1504, 192, '0'), (1616, 176, '0'),
    (1936, -16, '0'), (1888, 192, '0'), (2400, 192, '0'), (2512, 192, '0'),
    (2336, 416, '0'), (2560, 416, '0'), (2656, 32, 'gc'), (3104, -32, 'r'),
    (2960, -16, '0'), (3008, 192, '0'),
    (1568, 272, 'vin'), (1472, 320, 'out'), (1472, 512, 'out'), (1600, 480, '0'), (1600, 576, '0'), (1568, 656, '0'),
    (1872, 368, 'vin'), (1872, 528, 'od'), (1920, 448, '0'),
]
TITLES = [(-160, -352, 'Error amplifier (powered from Vout)'), (880, -352, 'Supply, mirror power stage and driver'),
         (1792, -352, 'Tracking amplifier (powered from Vout): holds r = Vout'),
         (1440, 240, 'Start-up kick (powered from Vin)')]

DIRECTIVES = ['!.include ../models/models_292p.txt', '!' + NODESET, '!.options numdgt=12',
              '!.ac dec 50 1k 10G', '!.meas AC worst_psrr MAX mag(V(out)) FROM 10k TO 1G',
              '!.meas AC f_worst WHEN mag(V(out))=worst_psrr', ';.op', ';.noise V(out) Vin dec 20 1k 100Meg',
              ';NCM-LDO (neutralized current-mode LDO), 180 nm: 1.8 V -> 1.40 V, 10 mA, overhead 289 uA, 1.0 nF.',
              ';Pass = 100 x Mref mirror (gds cancelled); Cn ~ Cgd(Mpass) supplies the gate current at node r;',
              ';the tracking amplifier holds r = Vout through cascode Mc (body tied to r).',
              ';Rg (Vin->g) keeps the gate-node pole up at light load; its current is not mirrored.',
              ';Cff across Rtop: beta -> 1 above ~100 kHz, so the loop crosses at ~21 MHz and the divider noise is bypassed.',
              ';Start-up: while Vout < ~2 Vth, k is high and follower Mku charges od (held by Cz), turning the driver on; off afterwards.']
# Named internal nodes so the netlist reads like the design (wire points that carry these names)
NAMED = [(320, -16, 'tp'), (544, 176, 'od'), (656, 304, 'z'), (320, 176, 'a2'), (1104, 176, 'g'),
         (1104, 368, 'dd'), (944, 304, 'vcn'), (96, 48, 'refd'), (2336, 32, 'd1'), (1888, 16, 'os'),
         (3008, 16, 'rsh'), (2336, 240, 's1'), (2560, 240, 's2'), (1568, 416, 'k'), (1568, 528, 'sd')]

# Spread crowded regions: every coordinate right of a boundary moves right by its shift. Boundaries sit in empty
# columns (no symbol has its origin and a pin on opposite sides), so pins stay on their wires and only
# horizontal wires that cross a boundary stretch.
SHIFTS = [(464, 320),    # error-amp pair / mirror: room for both inner text blocks
          (600, 160),    # Mnl2 text vs Rz/Cz
          (960, 128),    # Vin vs Cn
          (1040, 256),   # Cn vs Mref text
          (1250, 96),    # Mc text vs the gate-feedback wire and Mpass
          (2260, 128),   # Mfo text vs Ml1 text
          (2504, 384),   # tracking pair M1/M2 text blocks and the degeneration network
          (2680, 128)]   # Ml2 text vs Mfr text


def X(x):
    return x + sum(s for b, s in SHIFTS if x > b)


def eng(v):
    """180000.0 -> 180k, 1.15e-12 -> 1.15p (leave non-numeric values alone)."""
    try:
        f = float(v)
    except ValueError:
        return v
    for p, s in [(1e9, 'G'), (1e6, 'Meg'), (1e3, 'k'), (1, ''), (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n'), (1e-12, 'p'), (1e-15, 'f')]:
        if abs(f) >= p * 0.999:
            return f'{f / p:.4g}{s}'
    return v


lines = ['Version 4.1', f'SHEET 1 {X(3328)} 1120']
for pl in W:
    for (x1, y1), (x2, y2) in zip(pl[:-1], pl[1:]):
        assert x1 == x2 or y1 == y2, ('diagonal', pl)
        lines.append(f'WIRE {X(x1)} {y1} {X(x2)} {y2}')
for x, y, n in F + NAMED:
    lines.append(f'FLAG {X(x)} {y} {n}')
# ---- DC operating point of the same netlist (shown on the drawing) ----
_o = op(1.8, 10e-3)
OPV = {k[2:-1]: v for k, v in _o.items() if k.startswith('v(')}
OPI = {k[3:-1].lower(): abs(v) for k, v in _o.items() if k.startswith('id(')}


def amps(i):
    return f'{i*1e3:.3g}mA' if i >= 1e-3 else f'{i*1e6:.3g}uA'


idtext = []
for name, (sym, x, y, rot) in P.items():
    lines.append(f'SYMBOL {sym} {X(x)} {y} {rot}')
    if sym in ('nmos4', 'pmos4'):
        # show name and W/L; hide the model name (as in the project's existing schematics)
        # text block beside the device, beyond its bulk wire and ground symbol: name / W/L / Id, top to bottom
        fy = rot in ('M180', 'R180')                # vertically flipped: local y counts up from the bottom
        lines.append(f"WINDOW 0 128 {72 if fy else 24} Left 2")
        lines.append('WINDOW 3 56 72 Invisible 2')  # model name hidden
        lines.append(f"WINDOW 39 128 {40 if fy else 56} Left 2")
    lines.append(f'SYMATTR InstName {name}')
    v, sl = vals[name]
    lines.append(f'SYMATTR Value {eng(v) if sym in ("res", "cap", "current") else v}')
    if sl:
        lines.append(f'SYMATTR SpiceLine {sl}')
    if sym in ('nmos4', 'pmos4'):  # drain current one line beyond W/L, on the same side as the attribute text
        flip_x = rot in ('M0', 'R180'); flip_y = rot in ('M180', 'R180')
        tx = X(x) + (-128 if flip_x else 128); ty = y + (-8 if flip_y else 88)
        idtext.append(f"TEXT {tx} {ty} {'Right' if flip_x else 'Left'} 2 ;Id={amps(OPI[name.lower()])}")
lines += idtext
for x, y, t in TITLES:
    lines.append(f'TEXT {X(x)} {y} Left 2 ;{t}')
# node voltages next to the named nodes
for x, y, n in NAMED + [(1712, 16, 'out'), (1008, 48, 'gc'), (1008, -16, 'r'), (880, -256, 'vin'), (-160, -16, 'fb')]:
    if n in OPV and n != 'z':
        if n in ('os', 'rsh'):   # these sit where the follower's Id text goes: put the voltage below-left instead
            lines.append(f'TEXT {X(x) - 8} {y + 24} Right 1 ;{OPV[n]:.3f} V')
        else:
            lines.append(f'TEXT {X(x) + 8} {y - 24} Left 1 ;{OPV[n]:.3f} V')
for i, d in enumerate(DIRECTIVES):
    lines.append(f'TEXT -160 {672 + 32 * i} Left 2 {d}')
txt = '\n'.join(lines) + '\n'
assert all(ord(c) < 128 for c in txt)
OUT.write_bytes(txt.encode('ascii'))
print(OUT, len(P), 'symbols', sum(len(p) - 1 for p in W), 'wire segments')
