"""Identidad persistente de cada ordenamiento: no depende solo del nombre del archivo, su dirección o su fecha.
- familia(url): carpeta + nombre del archivo sin la fecha que algunos congresos le agregan («Ley de Ingresos del Estado de Jalisco-240926.pdf»)
- titulo_norm / parecido: títulos normalizados (sin acentos, mayúsculas, fechas ni palabras de relleno) para comparar con el catálogo
- es_oficial(url): dominio de gobierno mexicano (.gob.mx) o de la lista «oficiales_extra» de fuentes.json
- huellas_unidades / comparar: huella por disposición (exacta y «de fondo», que ignora espacios, puntuación y mayúsculas)"""
import re, unicodedata, hashlib, posixpath
from urllib.parse import urlparse, unquote

def norm(t):
    t = unicodedata.normalize('NFD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', t)).strip()

VACIAS = set('a al de del el en la las los para por y e o con sus su que se le lo como mas'.split())
RELLENO = set('descargar descarga pdf doc docx ver archivo documento vigente actualizada actualizado texto'.split())

def tokens(t):
    return [w for w in norm(t).split() if w not in VACIAS and w not in RELLENO and len(w) > 1]

def titulo_norm(t):
    t = norm(t)
    t = re.sub(r'\b\d{1,2} \d{1,2} (19|20)\d{2}\b', ' ', t)          # fechas 09/09/2026 (ya sin signos)
    t = re.sub(r'\b(decreto|acuerdo|dec|dto)\b.*$', ' ', t)           # «… DECRETO 30223», «ACUERDO 224/LXIII/23»
    t = re.sub(r'\b\d{4,}\b(?<!(?:19|20)\d\d)', ' ', t)                  # números de decreto o expediente (no años)
    return ' '.join(w for w in t.split() if w not in RELLENO)

def parecido(a, b):
    """Coincidencia de palabras (0 a 1) entre dos títulos, tomando como base el más corto."""
    A, B = set(tokens(a)), set(tokens(b))
    if not A or not B: return 0.0
    return len(A & B) / min(len(A), len(B))

def anios(t):
    return set(re.findall(r'\b(?:19|20)\d{2}\b', t or ''))

def familia(url):
    p = urlparse(url or '')
    ruta = unquote(p.path or '')
    if p.query and not ruta.lower().endswith(('.pdf', '.doc', '.docx', '.rtf', '.htm', '.html')):
        ruta += '?' + unquote(p.query)                                   # descargas por número: «descarga?uuid=…», «ley&cual=337»
    nombre = posixpath.basename(ruta.rstrip('/')) or ruta
    carpeta = posixpath.basename(posixpath.dirname(ruta.rstrip('/')))
    base, ext = posixpath.splitext(nombre)
    if len(ext) > 6: base, ext = nombre, ''
    b = norm(base)
    b = re.sub(r'(?:\s+\d{6}|\s+\d{8})+$', '', b)                       # sufijos de fecha: -240926, _20260618
    b = re.sub(r'\s+(ultima reforma|actualizad[ao]|vigente|reformad[ao])(\s.*)?$', '', b)
    return f'{norm(carpeta)}|{b.strip()}|{ext.lower()}'

def url_norm(url):
    p = urlparse(url or '')
    return (p.netloc.lower().replace('www.', '') + unquote(p.path) + ('?' + unquote(p.query) if p.query else '')).rstrip('/')

def origen(url):
    p = urlparse(url); return f'{p.scheme}://{p.netloc}'

def host(url):
    return urlparse(url or '').netloc.lower().replace('www.', '')

def es_oficial(url, extra=()):
    h = host(url).split(':')[0]
    return h.endswith('.gob.mx') or h in {host('https://' + e) if '//' not in e else host(e) for e in extra}

def fecha_en_nombre(url):
    """Fecha de publicación que algunos congresos ponen en el nombre del archivo (ddmmaa o aaaammdd) → 'aaaa-mm-dd' o ''."""
    n = posixpath.basename(unquote(urlparse(url or '').path))
    m = re.search(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)', n)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.search(r'(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)', n)
    if m and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12: return f'20{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return ''

# ---------- huellas por disposición ----------
def _h(t): return hashlib.sha256(t.encode()).hexdigest()[:12]

def huellas_unidades(us):
    """{clave de la disposición: [huella exacta, huella de fondo, fechas de reforma]}; la clave repite el número si aparece dos veces."""
    out, vistos = {}, {}
    for u in us:
        k = (u.get('tipo') or '') + ':' + (u.get('nn') or u.get('numero') or str(u.get('orden', '')))
        vistos[k] = vistos.get(k, 0) + 1
        if vistos[k] > 1: k += '#' + str(vistos[k])
        texto = u.get('texto') or ''
        out[k] = [_h(texto), _h(norm(texto)), u.get('fechas') or '']
    return out

def comparar(viejo, nuevo):
    agregadas = [k for k in nuevo if k not in viejo]
    eliminadas = [k for k in viejo if k not in nuevo]
    exactas = [k for k in nuevo if k in viejo and nuevo[k][0] != viejo[k][0]]
    fondo = [k for k in exactas if nuevo[k][1] != viejo[k][1]]
    return dict(agregadas=agregadas, eliminadas=eliminadas, cambiadas=exactas, de_fondo=fondo)
