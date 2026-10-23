"""Leyes anuales (leyes de ingresos, presupuestos): descubre la del ejercicio siguiente sin tocar el código cada año.
Cada ordenamiento anual de fuentes.json (nombre con «Ley de Ingresos» o «Presupuesto de Egresos» y un ejercicio) genera,
desde el 1 de septiembre de su ejercicio, la búsqueda del siguiente:
  1. sondeo: la misma dirección con el año cambiado (LIF_2026.pdf → LIF_2027.pdf, …/2026/… → …/2027/…);
  2. listados oficiales del estado (fuentes.json → listados): renglón con «ingresos», el nombre del estado y el año nuevo.
Lo encontrado se valida (documento real, dominio oficial) y se lee; construir.py confirma el ejercicio en el texto antes de publicarlo.
Si no aparece, queda «pendiente de publicación» (o «pendiente de verificación» si ya debió publicarse). Estado en kit/anuales.json."""
import re
from urllib.parse import unquote
from identidad import norm, titulo_norm, tokens, anios, origen, es_oficial, url_norm

RE_EJ = re.compile(r'(?:ejercicio(?: fiscal)?(?: del ano| de| del| para el)?|miscelanea fiscal para(?: el)?) ((?:19|20)\d{2})')

def ejercicio(x):
    if x.get('ejercicio'): return int(x['ejercicio'])
    m = RE_EJ.search(norm(x.get('nombre') or ''))
    if m: return int(m.group(1))
    m = re.search(r'_((?:19|20)\d{2})$', x.get('clave') or '')
    return int(m.group(1)) if m else None

def es_anual(x):
    n = norm(x.get('nombre') or '')
    return ('ley de ingresos' in n or 'presupuesto de egresos' in n or n.startswith('resolucion miscelanea fiscal')) and bool(ejercicio(x))

def base(clave): return re.sub(r'_(?:19|20)\d{2}$', '', clave)
def clave_nueva(x, T): return base(x['clave']) + '_' + str(T)

def vigentes(D):
    """El ordenamiento anual más reciente de cada familia (la base de la clave)."""
    ult = {}
    for x in D['fuentes']:
        if not es_anual(x) or x.get('archivado'): continue
        b = base(x['clave'])
        if b not in ult or ejercicio(x) > ejercicio(ult[b]): ult[b] = x
    return list(ult.values())

def en_temporada(N, hoy): return hoy >= f'{N}-09-01'

def candidatos(D, hoy):
    """Direcciones a sondear para el ejercicio siguiente: [{id, base, ejercicio, url, modo, origen}]."""
    out = []
    for x in vigentes(D):
        N = ejercicio(x); T = N + 1
        if not en_temporada(N, hoy): continue
        urls = []
        if str(N) in x['url']: urls.append(x['url'].replace(str(N), str(T)))
        if str(N)[2:] + '.' in x['url'] and str(N) not in x['url']: urls.append(x['url'].replace(str(N)[2:] + '.', str(T)[2:] + '.'))
        for i, u in enumerate(dict.fromkeys(urls)):
            out.append(dict(id=f"{x['clave']}@{T}@{i}", base=x['clave'], ejercicio=T, url=u, modo=x['modo'], origen=origen(u)))
    return out

def _del_estado(x, l):
    return (l.get('estado') or '') == (x.get('estado') or '') and (l.get('ambito') or ('estatal' if l.get('estado') else 'federal')) == x['ambito']

def buscar_en_listados(x, T, filas, listados):
    """Renglones de los listados del mismo estado que parecen la ley anual del ejercicio T."""
    L = {l['id']: l for l in listados}
    nombre = re.sub(r'(19|20)\d{2}', ' ', x.get('nombre') or '')
    clave_tipo = 'presupuesto' if 'presupuesto' in norm(nombre) else 'ingresos'
    res = []
    for lid, texto, url, fila in filas:
        l = L.get(lid)
        if not l or not _del_estado(x, l): continue
        todo = f'{texto} {fila} {unquote(url)}'
        if clave_tipo not in norm(todo) or str(T) not in anios(norm(todo)): continue
        if 'municip' in norm(todo) and 'municip' not in norm(nombre): continue      # la del estado, no la de un municipio
        # parecido con el nombre del ordenamiento (sin el año)
        A = set(tokens(nombre)); B = set(tokens(todo))
        if A and len(A & B) / len(A) < 0.6: continue
        res.append(dict(url=url, titulo=(texto or fila)[:200], via='listado ' + lid))
    # preferir PDF, luego Word
    res.sort(key=lambda r: (0 if r['url'].lower().split('?')[0].endswith('.pdf') else 1))
    return res

def procesar(D, ANU, sondeos, filas, hoy, extra_oficiales=()):
    """Actualiza ANU (kit/anuales.json) y regresa la lista de leyes anuales nuevas por leer."""
    nuevos = []
    cands = candidatos(D, hoy)
    for x in vigentes(D):
        N = ejercicio(x); T = N + 1; b = base(x['clave'])
        if not en_temporada(N, hoy): continue
        e = ANU.setdefault(b, {})
        if e.get('estado') in ('incorporada', 'pendiente_validacion') and e.get('ejercicio') == T: continue
        e.update(clave_actual=x['clave'], ejercicio_actual=N, ejercicio=T, revisado=hoy)
        hallado = None
        for c in [c for c in cands if c['base'] == x['clave']]:
            r = sondeos.get(c['id'])
            if r is None: continue
            e.setdefault('sondeos', {})[c['url']] = (r.get('err') or 'encontrado')[:80]
            if r.get('ok') and es_oficial(r.get('f') or c['url'], extra_oficiales): hallado = dict(url=r.get('f') or c['url'], titulo='', via='sondeo'); break
        if not hallado:
            for r in buscar_en_listados(x, T, filas, D.get('listados', [])):
                if es_oficial(r['url'], extra_oficiales) and url_norm(r['url']) != url_norm(x['url']): hallado = r; break
        if hallado:
            e.update(estado='detectada', detectada=hoy, url=hallado['url'], via=hallado['via'])
            nuevos.append(dict(clave=clave_nueva(x, T), base=x['clave'], ejercicio=T, url=hallado['url'], titulo=hallado['titulo'],
                               modo='pdf' if x['modo'] == 'html' and not hallado['url'].endswith(('.htm', '.html')) else x['modo'], origen=origen(hallado['url']), via=hallado['via']))
        else:
            e['estado'] = 'pendiente_verificacion' if hoy >= f'{T}-01-20' else 'pendiente_publicacion'
    return nuevos

def descubrir_siguiente(D, hoy):
    """Páginas «descubrir» del ejercicio siguiente (p. ej. la RMF 2027 en el minisitio del SAT), desde el 15 de noviembre."""
    out, claves = [], {x['clave'] for x in D['fuentes']}
    for d in D.get('descubrir', []):
        m = re.search(r'(?:19|20)\d{2}', d['clave'])
        if not m: continue
        N = int(m.group(0)); T = N + 1; nueva = d['clave'].replace(str(N), str(T))
        if hoy < f'{N}-11-15' or nueva in claves or any(e['clave'] == nueva for e in D.get('descubrir', [])): continue
        pat = r'(?:Resoluci[oó]n|RMF)[^/]*' + str(T)
        for pag in dict.fromkeys([d['pagina'].replace(str(N), str(T)), re.sub(r'[^/]+$', 'index.html', d['pagina'])]):
            out.append(dict(clave=nueva, base=d['clave'], ejercicio=T, pagina=pag, patron=pat, conocidos=[], derivado=True))
    return out
