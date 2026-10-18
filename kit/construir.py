"""Arma una actualización para la aplicación con lo que se leyó en esta revisión y la publica en actualizaciones/.
uso: python3 kit/construir.py [--etiqueta "texto"]
Lee: kit/tmp/cambios.json (revisar.py), kit/tmp/textos/<clave>.json|.bin (reunir.py), kit/tmp/dof_*.json (dof.py)
Escribe: actualizaciones/<id>.json, indice.json y fuentes.json (versión, huella y control de cada fuente)."""
import json, os, re, sys, glob, gzip, base64, hashlib, subprocess, tempfile, shutil
from datetime import datetime, timezone, timedelta
K = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(K); sys.path.insert(0, K)
from comun import limpiar_estatal, fechas_unidad, ultima_reforma
MX = timezone(timedelta(hours=-6)); ahora = datetime.now(MX); hoy = ahora.strftime('%Y-%m-%d')
D = json.load(open(K + '/fuentes.json')); F = {x['clave']: x for x in D['fuentes']}
C = json.load(open(K + '/tmp/cambios.json')) if os.path.exists(K + '/tmp/cambios.json') else {'cambios': [], 'nuevos_docs': []}
CAMPOS = ('tipo', 'numero', 'nn', 'titulo', 'ubicacion', 'texto', 'fechas', 'pagina', 'orden')
AVISO_EST = 'Compilación publicada por el Congreso o la Consejería Jurídica del estado como documento de consulta; el texto con validez oficial es el publicado en el periódico oficial del estado.'
def paginas_de(clave):
    j, b = f'{K}/tmp/textos/{clave}.json', f'{K}/tmp/textos/{clave}.bin'
    if os.path.exists(j): return json.load(open(j))
    if not os.path.exists(b): return None
    datos = open(b, 'rb').read(); cab = datos[:8]
    ext = '.doc' if cab.startswith(b'\xd0\xcf\x11\xe0') else '.docx' if cab.startswith(b'PK') else '.rtf' if cab.startswith(b'{\\rtf') else '.pdf' if b'%PDF' in datos[:2000] else '.html'
    tmp = tempfile.mkdtemp(); src = f'{tmp}/x{ext}'; open(src, 'wb').write(datos)
    if ext == '.pdf':   # escaneado: OCR si está instalado
        if shutil.which('tesseract'): subprocess.run(['python3', K + '/ocr.py', src, tmp + '/o.json']); return json.load(open(tmp + '/o.json')) if os.path.exists(tmp + '/o.json') else None
        print('  sin OCR disponible para', clave); return None
    subprocess.run(['soffice', '--headless', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', tmp, src], capture_output=True, timeout=600)
    txt = open(f'{tmp}/x.txt', encoding='utf-8', errors='replace').read() if os.path.exists(f'{tmp}/x.txt') else ''
    pags, cur = [], ''
    for l in txt.replace('\r', '').split('\n'):
        if len(cur) > 3500: pags.append(cur); cur = ''
        cur += l.rstrip() + '\n'
    return pags + [cur] if txt else None
def dividir(pags, formato):
    t = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False); json.dump(pags, t); t.close()
    r = subprocess.run(['node', K + '/parsear_uno.js', t.name, formato], capture_output=True, text=True, check=True); os.unlink(t.name); return json.loads(r.stdout)
def huella(us): return hashlib.sha256('\n'.join((u.get('numero') or '') + '|' + (u.get('texto') or '') for u in us).encode()).hexdigest()[:24]
leyes, cambiadas, notas = [], [], []
pendientes = [(c['clave'], None) for c in C.get('cambios', [])] + [(n['clave'], n) for n in C.get('nuevos_docs', [])]
for clave, nuevo in pendientes:
    x = F[clave]; pags = paginas_de(clave)
    if not pags: notas.append(f'{clave}: no se pudo leer el texto'); continue
    est = x['ambito'] == 'estatal'
    if est: pags = limpiar_estatal(x['arch'], pags)
    r = dividir(pags, x['formato']); us = r['unidades']; meta = r['meta']
    if len(us) < max(3, int(x.get('unidades', 0) * 0.5)): notas.append(f'{clave}: lectura dudosa ({len(us)} disposiciones contra {x.get("unidades")}), no se publicó'); continue
    h = huella(us)
    cambio = next((c for c in C.get('cambios', []) if c['clave'] == clave), None)
    if h == x.get('huella'):   # el archivo cambió pero el texto es el mismo
        if cambio: x['control'] = cambio['ahora']
        continue
    if est:
        for u in us: u['fechas'] = fechas_unidad(u.get('texto') or '') if u.get('tipo') != 'transitorio' else ''
        fu, linea = ultima_reforma(pags, {'ultima': x.get('ultima_reg', '')})
        todas = sorted({f for u in us for f in (u['fechas'] or '').split(',') if f})
        if fu and todas and todas[-1] > fu: fu = todas[-1]
        etiqueta = f'Texto vigente, última reforma {fu[8:10]}/{fu[5:7]}/{fu[:4]}' if fu else 'Texto vigente (compilación del estado)'
        if clave.endswith('_li'): etiqueta = 'Texto vigente para el ejercicio' + (f' (actualizado al {fu[8:10]}/{fu[5:7]}/{fu[:4]})' if fu else '')
        meta = dict(meta, ultima_reforma=(f'P.O. {fu[8:10]}-{fu[5:7]}-{fu[:4]}' if fu else None), fecha_ultima_reforma=fu)
        reforma, desde, aviso, verif = (f'P.O. {fu[8:10]}/{fu[5:7]}/{fu[:4]}' if fu else ''), fu or hoy, AVISO_EST, 'compilación oficial del estado'
    else:
        fu = meta.get('fecha_ultima_reforma'); reforma = meta.get('ultima_reforma') or ''
        etiqueta = (nuevo or {}).get('titulo') or (f'Texto vigente, última reforma {reforma}' if reforma else 'Texto vigente')
        desde = fu or hoy; aviso = 'Compilación informativa del SAT. Para sustentar actos o resoluciones debe usarse la publicación del DOF.' if clave.startswith('rmf') else ''
        verif = 'oficial (compilación del SAT)' if clave.startswith('rmf') else 'oficial'
    cuerpo = json.dumps({'clave': clave, 'meta': meta, 'unidades': [{k: u.get(k) for k in CAMPOS} for u in us]}, ensure_ascii=False, separators=(',', ':'))
    url = (nuevo or {}).get('url') or x['url']
    v = dict(id='act_' + clave + '_' + h[:10], etiqueta=etiqueta, reforma=reforma, fecha_reforma=fu or '', desde=desde, hasta=None, ejercicio=None, vigente=True, num=len(us), paginas=len(pags),
             aviso=aviso, archivo=url.split('/')[-1], sha256=hashlib.sha256(cuerpo.encode()).hexdigest(), fuente=x.get('ficha', url) if x['modo'] == 'crudo' else url, obtenido=hoy, verificacion=verif, precargado=True)
    leyes.append({'clave': clave, 'version': v, 'b64': base64.b64encode(gzip.compress(cuerpo.encode(), 9)).decode()})
    cambiadas.append((clave, etiqueta, len(us)))
    x.update(version=v['id'], huella=h, unidades=len(us), etiqueta=etiqueta)
    if cambio: x['control'] = cambio['ahora']
    if nuevo:
        x['url'] = nuevo['url']; d = next(d for d in D['descubrir'] if d['clave'] == clave); d['conocidos'].append(nuevo['url'])
# Diario Oficial
dof = {'noticias': {}, 'indicadores': {}, 'reformas': {}, 'decretos': [], 'leyes': []}; fechas_dof = []
for f in sorted(glob.glob(K + '/tmp/dof_*.json')):
    j = json.load(open(f)); fechas_dof.append(re.search(r'dof_(\d{8})', f).group(1))
    for k in ('noticias', 'indicadores'): dof[k].update(j.get(k, {}))
    for k, l in j.get('reformas', {}).items(): dof['reformas'].setdefault(k, []).extend(l)
    dof['decretos'] += j.get('decretos', []); dof['leyes'] += j.get('leyes', [])
I = json.load(open(R + '/indice.json')) if os.path.exists(R + '/indice.json') else {'paquetes': []}
ya = {p['id'] for p in I['paquetes']}
# no repetir decretos o noticias ya publicados en actualizaciones anteriores
publicados = set()
for p in I['paquetes']:
    for k in p.get('claves_dof', []): publicados.add(k)
dof['noticias'] = {k: v for k, v in dof['noticias'].items() if k not in publicados}
dof['decretos'] = [d for d in dof['decretos'] if d['id'] not in publicados]; ids_dec = {d['id'] for d in dof['decretos']}
dof['leyes'] = [x for x in dof['leyes'] if x['id'] in ids_dec]
dof['reformas'] = {k: [r for r in l if r.get('d') in ids_dec] for k, l in dof['reformas'].items()}; dof['reformas'] = {k: l for k, l in dof['reformas'].items() if l}
hay = leyes or dof['noticias'] or dof['indicadores'] or dof['decretos']
if fechas_dof: I['dof_revisado'] = max([I.get('dof_revisado', '')] + [f'{x[:4]}-{x[4:6]}-{x[6:]}' for x in fechas_dof])
I['generado'] = ahora.isoformat(timespec='minutes')
if hay:
    pid = ahora.strftime('%Y%m%d-%H%M')
    while pid in ya: pid += 'b'
    titulo = '; '.join([f"{(F[c]['nombre'] if F[c].get('nombre') else c.upper())}: {e}" for c, e, _ in cambiadas][:6])
    if dof['decretos']: titulo = (titulo + '; ' if titulo else '') + f"{len(dof['decretos'])} decreto(s) de reforma en el DOF"
    if not titulo and dof['noticias']: titulo = f"{len(dof['noticias'])} publicaciones del DOF"
    if '--etiqueta' in sys.argv: titulo = sys.argv[sys.argv.index('--etiqueta') + 1]
    paquete = dict(id=pid, fecha=hoy, titulo=titulo, leyes=leyes + dof['leyes'], reformas=dof['reformas'], decretos=dof['decretos'], noticias=dof['noticias'], indicadores=dof['indicadores'])
    archivo = f'actualizaciones/{pid}.json'; os.makedirs(R + '/actualizaciones', exist_ok=True)
    s = json.dumps(paquete, ensure_ascii=False, separators=(',', ':')); open(R + '/' + archivo, 'w').write(s)
    I['paquetes'].append(dict(id=pid, fecha=hoy, archivo=archivo, titulo=titulo, leyes=[c for c, _, _ in cambiadas] + sorted({k for d in dof['decretos'] for k in d['leyes']}), bytes=len(s),
                              claves_dof=list(dof['noticias']) + [d['id'] for d in dof['decretos']]))
    print('publicada', archivo, round(len(s) / 1e6, 2), 'MB |', titulo)
else: print('sin novedades que publicar')
json.dump(I, open(R + '/indice.json', 'w'), ensure_ascii=False, indent=1)
json.dump(D, open(K + '/fuentes.json', 'w'), ensure_ascii=False, indent=1)
for n in notas: print('AVISO', n)
