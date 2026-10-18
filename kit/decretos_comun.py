"""Párrafos y apartados de un decreto (misma lógica con que se armaron los decretos de la aplicación)."""
import re, unicodedata
def norm(t): return unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode().lower()
def iso(f): d, m, a = f.split('-'); return f'{a}-{m}-{d}'
NOMBRES = {  # clave: patrón del nombre dentro del decreto
 'cff': r'codigo fiscal de la federacion', 'lisr': r'ley del impuesto sobre la renta', 'liva': r'ley del impuesto al valor agregado',
 'lieps': r'ley del impuesto especial sobre produccion y servicios', 'lfd': r'ley federal de derechos', 'lcf': r'ley de coordinacion fiscal',
 'lss': r'ley del seguro social', 'lifnvt': r'ley del instituto del fondo nacional de la vivienda', 'lsar': r'ley de los sistemas de ahorro para el retiro',
 'ccom': r'codigo de comercio', 'lgsm': r'ley general de sociedades mercantiles', 'lgtoc': r'ley general de titulos y operaciones de credito',
 'lcm': r'ley de concursos mercantiles', 'lfpiorpi': r'ley federal para la prevencion e identificacion de operaciones', 'lic': r'ley de instituciones de credito',
 'lmv': r'ley del mercado de valores', 'lft': r'ley federal del trabajo', 'lfpca': r'ley federal de procedimiento contencioso administrativo',
 'lamp': r'ley de amparo', 'lfpa': r'ley federal de procedimiento administrativo', 'ladua': r'ley aduanera', 'lce': r'ley de comercio exterior',
 'lie': r'ley de inversion extranjera', 'lif_2026': r'ley de ingresos de la federacion', 'lfdc': r'ley federal de los derechos del contribuyente'}
CAB = [re.compile(r'DIARIO OFICIAL', re.I)]
ORD = r'(Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|S[eé]ptimo|Octavo|Noveno|D[eé]cimo|Und[eé]cimo|Duod[eé]cimo|Vig[eé]simo|[ÚU]nico|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO|D[EÉ]CIMO|[ÚU]NICO)'
RE_ARTD = re.compile(r'^\s*(Art[ií]culo|ART[IÍ]CULO)\s+' + ORD + r'(\s+\w+)?\s*[.\-]')
RE_TRANS = re.compile(r'^\s*(TRANSITORIOS?|Transitorios?|Disposiciones?\s+Transitorias?|DISPOSICIONES?\s+TRANSITORIAS?)\b')
def mayus(t): l = [c for c in t if c.isalpha()]; return len(l) > 6 and sum(c.isupper() for c in l) / len(l) > .85
def nueva_linea(l):
    return bool(RE_ARTD.match(l) or RE_TRANS.match(l) or mayus(l) or re.match(r'^\s*(Art[ií]culo|ART[IÍ]CULO)\s+\d', l) or re.match(r'^\s*([IVXL]{1,6}\.|[a-z]\)|\d{1,2}\.)\s', l))
def procesar(pags):
    lineas = []
    for pg in pags:
        ls = pg.split('\n')
        if ls and CAB[0].search(ls[0]) and len(ls[0]) < 140: ls = ls[1:]
        lineas += [l for l in ls if l.strip() and not (CAB[0].search(l) and re.search(r'\d{4}', l) and len(l) < 140)]
    pars = []
    for l in lineas:
        l = l.strip()
        if pars and not nueva_linea(l) and not re.search(r'[.:;"”]$', pars[-1]): pars[-1] += ' ' + l
        else: pars.append(l)
    secs = []; ley_act = []
    for i, p in enumerate(pars):
        n = norm(p)
        if mayus(p) and len(p) < 220 and re.match(r'^(ley|codigo|reglamento|constitucion)', n):
            ley_act = [k for k, pat in NOMBRES.items() if re.search(pat, n)]
            if ley_act: secs.append([i, 'ley', p[:160], ley_act])
        elif RE_ARTD.match(p):
            ks = ley_act or [k for k, pat in NOMBRES.items() if re.search(pat, n[:400])]
            secs.append([i, 'articulo', p[:220], ks])
        elif RE_TRANS.match(p) and len(p) < 120:
            if re.search(r'\b(de la|del)\s+(ley|codigo|reglamento)', n): ley_act = [k for k, pat in NOMBRES.items() if re.search(pat, n)]
            secs.append([i, 'transitorios', p[:120], ley_act])
    return pars, secs
