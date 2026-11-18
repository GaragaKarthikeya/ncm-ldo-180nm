"""gm/Id techplot lookup (180 nm, characterised at W = 5000 um, |VDS| = 0.2 / 0.4 / 1.8 V).

lookup(kind, L, gm/Id, |VDS|, key) interpolates a parameter versus gm/Id; device() sizes a transistor.
"""
import pathlib, numpy as np, openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
WREF = 5000e-6
# row index (0-based) of each quantity in the techplot sheet, for NMOS ('n') and PMOS ('p')
_ROWS = {'n': dict(gm_id=13, gmro=15, id_w=16, cgg=17, cgd=19, ft=24),
         'p': dict(gm_id=33, gmro=35, id_w=36, cgg=37, cgd=38, ft=44)}
_cache = {}


def _load(tag):
    if tag not in _cache:
        f = ROOT / 'techplots' / f'TechPlot_Sim_Data_180nm_VDS_{tag}V.xlsx'
        r = list(openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
        _cache[tag] = lambda i, r=r: np.array(r[i][3:], dtype=float)
    return _cache[tag]


def _at(tag, kind, L, gmid, key):
    g = _load(tag)
    s = np.isclose(g(1), L)
    x = g(_ROWS[kind]['gm_id'])[s]
    y = g(3)[s] if key == 'vgs' else g(_ROWS[kind][key])[s]
    if key in ('cgg', 'cgd'):
        y = np.abs(y) / WREF  # per metre of width
    return float(np.interp(-gmid, -x, y))


def lookup(kind, L, gmid, vds, key):
    """kind 'n'/'p'; key in gmro, id_w (A/m), cgg/cgd (F/m), ft (Hz), vgs (V). Linear in |VDS| between grid points."""
    pts = [(0.2, '0p2'), (0.4, '0p4'), (1.8, '1p8')]
    vds = min(max(vds, 0.2), 1.8)
    for (v0, t0), (v1, t1) in zip(pts[:-1], pts[1:]):
        if vds <= v1:
            w = (vds - v0) / (v1 - v0)
            return (1 - w) * _at(t0, kind, L, gmid, key) + w * _at(t1, kind, L, gmid, key)


def device(kind, L, gmid, vds, Id):
    """Size a device from gm/Id: returns W, gm, gds, Cgg, Cgd, |VGS|, ft, gm*ro, Id/W."""
    idw = lookup(kind, L, gmid, vds, 'id_w')
    W = Id / idw
    gm = gmid * Id
    gmro = lookup(kind, L, gmid, vds, 'gmro')
    return dict(W=W, gm=gm, gds=gm / gmro, gmro=gmro, id_w=idw, ft=lookup(kind, L, gmid, vds, 'ft'),
                cgg=lookup(kind, L, gmid, vds, 'cgg') * W, cgd=lookup(kind, L, gmid, vds, 'cgd') * W,
                vgs=lookup(kind, L, gmid, vds, 'vgs'))
