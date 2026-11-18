"""Evaluate the design sheet's formulas without Excel (sanity check of make_design_sheet.py)."""
import re, math, openpyxl, sys
from spice import ROOT
ws = openpyxl.load_workbook(ROOT / 'design_sheet' / 'NCM_LDO_Design.xlsx')['Design flow']
F = dict(PI=lambda: math.pi, LOG10=math.log10, DEGREES=math.degrees, ATAN=math.atan, SQRT=math.sqrt)
cache = {}
def val(ref):
    if ref in cache: return cache[ref]
    v = ws[ref].value
    if isinstance(v, str) and v.startswith('='):
        e = v[1:]
        if e.startswith('IFERROR('):
            e = e[8:].rsplit(',', 1)[0]
        e = re.sub(r'\b([A-Z])(\d+)\b', lambda m: f'val("{m[1]}{m[2]}")', e).replace('^', '**')
        try: v = eval(e, {'val': val, **F})
        except Exception: v = None
    cache[ref] = v; return v
def table():
    out = []
    for r in range(1, ws.max_row + 1):
        b = ws.cell(r, 2).value
        if b and ws.cell(r, 3).value is not None and (ws.cell(r, 4).value is not None or ws.cell(r, 5).value is not None):
            out.append((r, b, val(f'C{r}'), ws.cell(r, 4).value, val(f'E{r}') if ws.cell(r, 5).value is not None else None,
                        val(f'G{r}') if ws.cell(r, 7).value is not None else None))
        elif b:
            out.append((r, b, None, None, None, None))
    return out
if __name__ == '__main__':
    f = lambda x: f'{x:.4g}' if isinstance(x, (int, float)) else ''
    for r, b, h, u, s, e in table():
        print(f'{r:3d} {b[:50]:50s} {f(h):>11s} {u or "":8s} {f(s):>11s} {(f"{e*100:6.1f}%" if isinstance(e, float) else ""):>8s}')
