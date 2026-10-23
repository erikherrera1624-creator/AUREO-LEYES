"""Arma una actualización para la aplicación con lo que se leyó en esta revisión y la publica en actualizaciones/.
uso: python3 kit/construir.py [--etiqueta "texto"]
Lee: kit/tmp/cambios.json (revisar.py), kit/tmp/textos/<clave>.json|.bin (reunir.py), kit/tmp/dof_*.json (dof.py)
Escribe: actualizaciones/<id>.json, indice.json, fuentes.json (versión, huella y control de cada fuente), kit/huellas/<clave>.json
(huella de cada disposición), kit/registro.json y kit/pendientes/ (lecturas que esperan validación: kit/validar.py).

Un cambio de archivo NO se publica automáticamente como reforma. Cada lectura se clasifica:
- reforma: fecha de última reforma posterior a la conocida, o disposiciones agregadas/eliminadas, o fechas de reforma nuevas → se publica
- correccion_editorial: pocas disposiciones con cambios de redacción, sin fecha de reforma nueva → se publica como nueva versión, marcada así
- formato / sin_cambio_texto: mismo texto de fondo (cambió el archivo, la dirección, espacios o puntuación) → no se publica; se actualiza el control
- documento_diferente: el título no corresponde al ordenamiento → no se toca; queda pendiente
- pendiente_validacion: cambió el texto sin evidencia suficiente → no se sobrescribe; queda en kit/pendientes/ para aprobar o descartar
La versión anterior siempre se conserva (la aplicación guarda el historial)."""
import json, os, re, sys, glob, gzip, base64, hashlib, subprocess, tempfile, shutil
from datetime import datetime, timezone, timedelta
K = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(K); sys.path.insert(0, K)
from comun import limpiar_estatal, fechas_unidad, ultima_reforma
from identidad import huellas_unidades, comparar, tokens, norm
from collections import Counter
import anuales
MX = timezone(timedelta(hours=-6)); ahora = datetime.now(MX); hoy = ahora.strftime('%Y-%m-%d')
D = json.load(open(K + '/fuentes.json')); F = {x['clave']: x for x in D['fuentes']}
C = json.load(open(K + '/tmp/cambios.json')) if os.path.exists(K + '/tmp/cambios.json') else {'cambios': [], 'nuevos_docs': []}
REG = json.load(open(K + '/registro.json')) if os.path.exists(K + '/registro.json') else {'fuentes': {}, 'eventos': []}
def evento(clave, tipo, detalle):
    REG.setdefault('eventos', []).append(dict(t=ahora.isoformat(timespec='minutes'), clave=clave, tipo=tipo, detalle=detalle)); REG['eventos'] = REG['eventos'][-500:]
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
# ---------- identidad y clasificación de cada lectura ----------
GENERICAS = {'libre', 'soberano', 'ano', 'dictamen', 'aprobado', 'texto', 'vigente', 'compilado', 'modificacion', 'primera', 'segunda'}
def titulo_coincide(x, pags):
    """El documento leído corresponde al ordenamiento (sus palabras distintivas aparecen en las primeras páginas)."""
    nombre = re.sub(r'\([^)]*\)', ' ', x.get('nombre') or '')
    A = {w for w in tokens(nombre) if w not in GENERICAS and not re.fullmatch(r'(19|20)\d\d', w)}
    if not A: return True
    B = set(norm(' '.join(pags[:3])[:15000]).split())
    return len(A & B) / len(A) >= 0.65
def ejercicio_en_texto(pags):
    c = Counter(int(m.group(1)) for m in anuales.RE_EJ.finditer(norm(' '.join(pags[:2])[:10000])))
    return c.most_common(1)[0][0] if c else None
def fecha_de(t):
    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})', t or ''); return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}' if m else ''
def fecha_anterior(x): return x.get('fecha_reforma') or fecha_de(x.get('etiqueta'))
def huellas_previas(clave):
    f = f'{K}/huellas/{clave}.json'; return json.load(open(f))['u'] if os.path.exists(f) else None
def guardar_huellas(clave, hu, url):
    os.makedirs(K + '/huellas', exist_ok=True); json.dump({'clave': clave, 'fecha': hoy, 'url': url, 'u': hu}, open(f'{K}/huellas/{clave}.json', 'w'), separators=(',', ':'))
def clasificar(x, h, hu, fn):
    """→ (clase, detalle). fn = fecha de última reforma que trae el texto nuevo."""
    if h == x.get('huella'): return 'sin_cambio_texto', 'mismo texto; cambió el archivo, su dirección o sus datos de control'
    fa = fecha_anterior(x)
    if fn and fa and fn > fa: return 'reforma', f'última reforma {fa} → {fn}'
    viejo = huellas_previas(x['clave'])
    if viejo:
        c = comparar(viejo, hu)
        if not c['agregadas'] and not c['eliminadas'] and not c['de_fondo']: return 'formato', f"{len(c['cambiadas'])} disposiciones con cambios solo de espacios, puntuación o mayúsculas"
        nuevas_f = [k for k in c['de_fondo'] + c['agregadas'] if any(f > (fa or '') for f in (hu[k][2] or '').split(',') if f)]
        if c['agregadas'] or c['eliminadas'] or nuevas_f:
            return 'reforma', f"{len(c['agregadas'])} agregadas, {len(c['eliminadas'])} eliminadas, {len(c['de_fondo'])} modificadas" + (f"; fechas de reforma nuevas en {', '.join(nuevas_f[:5])}" if nuevas_f else '')
        if len(c['de_fondo']) <= 3: return 'correccion_editorial', f"cambios menores de redacción en {', '.join(c['de_fondo'])}, sin fecha de reforma nueva"
        return 'pendiente_validacion', f"{len(c['de_fondo'])} disposiciones cambiaron sin fecha de reforma nueva"
    if fn and fa and fn < fa: return 'pendiente_validacion', f'la fecha de última reforma del texto ({fn}) es anterior a la conocida ({fa})'
    if fn and not fa: return 'reforma', f'texto con última reforma {fn} (sin fecha anterior registrada)'
    return 'pendiente_validacion', 'el texto cambió, pero no trae una fecha de reforma posterior y aún no hay huellas por disposición para comparar'

leyes, cambiadas, notas, pendientes_nuevos, catalogo = [], [], [], [], []
ANU = json.load(open(K + '/anuales.json')) if os.path.exists(K + '/anuales.json') else {}
def anual_estado(x, estado):
    b = anuales.base(x.get('anterior') or x['clave']); ANU.setdefault(b, {}).update(estado=estado, ejercicio=x.get('ejercicio'), clave_nueva=x['clave'], fecha=hoy)
def reg(clave, **kw): REG['fuentes'].setdefault(clave, {}).update(kw)
def apartar(x, clave, clase, detalle, version, cuerpo, cambio, url):
    """Lectura dudosa: no se sobrescribe nada; queda guardada para aprobarla o descartarla con kit/validar.py."""
    os.makedirs(K + '/pendientes', exist_ok=True)
    json.dump(dict(clave=clave, clase=clase, detalle=detalle, fecha=hoy, url=url, version=version, control=(cambio or {}).get('ahora'), ficha={k: x.get(k) for k in ('nombre', 'ambito', 'estado', 'ejercicio', 'anterior')}),
              open(f'{K}/pendientes/{clave}.json', 'w'), ensure_ascii=False, indent=1)
    open(f'{K}/pendientes/{clave}.gz', 'wb').write(gzip.compress(cuerpo.encode(), 9))
    if cambio and cambio.get('ahora'): x['control_en_revision'] = cambio['ahora']
    if url != x.get('url'): x['url_en_revision'] = url
    pendientes_nuevos.append((clave, clase, detalle)); reg(clave, resultado='pendiente_validacion', motivo=detalle, pendiente=False); evento(clave, clase, detalle)
    if x.get('anterior') and anuales.es_anual(x): anual_estado(x, 'pendiente_validacion')

trabajo = [(c['clave'], 'cambio', c) for c in C.get('cambios', [])] + [(n['clave'], 'descubierto', n) for n in C.get('nuevos_docs', [])] \
        + [(n['clave'], 'anual', n) for n in C.get('anuales_nuevos', [])] + [(k, 'validar', {}) for k in C.get('validar', [])]
for clave, tipo, info in trabajo:
    if tipo == 'anual':
        b = F[info['base']]; T = info['ejercicio']; N = anuales.ejercicio(b)
        x = {k: v for k, v in b.items() if k not in ('control', 'control_en_revision', 'url_en_revision', 'version', 'huella', 'etiqueta', 'fecha_reforma', 'urls_anteriores')}
        x.update(clave=clave, url=info['url'], origen=info['origen'], modo=info['modo'], ejercicio=T, anterior=b['clave'], nombre=(b.get('nombre') or '').replace(str(N), str(T)), unidades=0)
    else:
        x = F[clave]
    url = info.get('url_nueva') or info.get('url') or x['url']
    pags = paginas_de(clave)
    if not pags: notas.append(f'{clave}: no se pudo leer el texto'); reg(clave, resultado='falla_lectura', motivo='no se pudo leer el texto', pendiente=True); continue
    est = x['ambito'] == 'estatal'
    if est: pags = limpiar_estatal(x['arch'], pags)
    r = dividir(pags, x['formato']); us = r['unidades']; meta = r['meta']
    minimo = max(3, int((F[info['base']] if tipo == 'anual' else x).get('unidades', 0) * (0.3 if tipo == 'anual' else 0.5)))
    if len(us) < minimo:
        notas.append(f'{clave}: lectura dudosa ({len(us)} disposiciones contra {x.get("unidades")}), no se publicó'); reg(clave, resultado='lectura_dudosa', motivo=f'{len(us)} disposiciones', pendiente=True); continue
    cambio = info if tipo == 'cambio' else None
    # ¿es la ley anual del ejercicio siguiente publicada con la misma dirección o el mismo nombre de archivo?
    if tipo == 'cambio' and anuales.es_anual(x):
        Tt = ejercicio_en_texto(pags)
        if Tt and Tt > anuales.ejercicio(x):
            nueva = anuales.clave_nueva(x, Tt)
            if nueva in F: notas.append(f'{clave}: el archivo ya trae el ejercicio {Tt}, que ya está registrado como {nueva}'); continue
            b = x; x = {k: v for k, v in b.items() if k not in ('control', 'control_en_revision', 'url_en_revision', 'version', 'huella', 'etiqueta', 'fecha_reforma', 'urls_anteriores')}
            x.update(clave=nueva, url=url, ejercicio=Tt, anterior=b['clave'], nombre=(b.get('nombre') or '').replace(str(anuales.ejercicio(b)), str(Tt)), unidades=0)
            b['archivado'] = True; reg(b['clave'], resultado='ejercicio_concluido', motivo=f'su dirección ya publica el ejercicio {Tt}', pendiente=False)
            evento(b['clave'], 'ley_anual_detectada', f'{Tt}: {url} (misma familia de archivo)'); tipo = 'anual'; clave = nueva; cambio = None
            os.makedirs(K + '/tmp/textos', exist_ok=True)
    if not titulo_coincide(x, pags):
        apartar(x, clave, 'documento_diferente', 'el título del documento no corresponde al ordenamiento', None, json.dumps({'clave': clave, 'meta': meta, 'unidades': [{k: u.get(k) for k in CAMPOS} for u in us]}, ensure_ascii=False), cambio, url)
        continue
    if tipo == 'anual':
        Tt = ejercicio_en_texto(pags)
        if Tt != x['ejercicio']:
            notas.append(f'{clave}: el documento no confirma el ejercicio {x["ejercicio"]} (dice {Tt}); no se publicó'); reg(clave, resultado='pendiente_validacion', motivo=f'ejercicio en el texto: {Tt}'); continue
    if est:
        for u in us: u['fechas'] = fechas_unidad(u.get('texto') or '') if u.get('tipo') != 'transitorio' else ''
        fu, linea = ultima_reforma(pags, {'ultima': x.get('ultima_reg', '')})
        todas = sorted({f for u in us for f in (u['fechas'] or '').split(',') if f})
        if fu and todas and todas[-1] > fu: fu = todas[-1]
    else:
        fu = meta.get('fecha_ultima_reforma')
    h = huella(us); hu = huellas_unidades(us)
    if tipo == 'descubierto': clase, detalle = 'reforma', 'nueva compilación publicada por la autoridad'
    elif tipo == 'anual': clase, detalle = 'ley_anual_nueva', f"ley del ejercicio {x['ejercicio']}"
    else: clase, detalle = clasificar(x, h, hu, fu)
    if tipo == 'validar' and clase == 'sin_cambio_texto': clase, detalle = 'validada', 'el texto del sitio coincide con el de la aplicación'
    # ----- versión (se arma siempre: se publica o se aparta) -----
    if est:
        etiqueta = f'Texto vigente, última reforma {fu[8:10]}/{fu[5:7]}/{fu[:4]}' if fu else 'Texto vigente (compilación del estado)'
        if anuales.es_anual(x) or clave.endswith('_li'): etiqueta = f"Texto para el ejercicio {anuales.ejercicio(x)}" + (f' (actualizado al {fu[8:10]}/{fu[5:7]}/{fu[:4]})' if fu else '')
        meta = dict(meta, ultima_reforma=(f'P.O. {fu[8:10]}-{fu[5:7]}-{fu[:4]}' if fu else None), fecha_ultima_reforma=fu)
        reforma, desde, aviso, verif = (f'P.O. {fu[8:10]}/{fu[5:7]}/{fu[:4]}' if fu else ''), fu or hoy, AVISO_EST, 'compilación oficial del estado'
    else:
        reforma = meta.get('ultima_reforma') or ''
        etiqueta = info.get('titulo') if tipo == 'descubierto' and info.get('titulo') else (f'Texto vigente, última reforma {reforma}' if reforma else 'Texto vigente')
        if anuales.es_anual(x): etiqueta = f"Texto para el ejercicio {anuales.ejercicio(x)}" + (f', última reforma {reforma}' if reforma else '')
        desde = fu or hoy; aviso = 'Compilación informativa del SAT. Para sustentar actos o resoluciones debe usarse la publicación del DOF.' if clave.startswith('rmf') else ''
        verif = 'oficial (compilación del SAT)' if clave.startswith('rmf') else 'oficial'
    if clase == 'correccion_editorial': etiqueta += ' (corrección editorial)'
    if tipo == 'anual': desde = f"{x['ejercicio']}-01-01" if hoy < f"{x['ejercicio']}-01-01" else desde
    cuerpo = json.dumps({'clave': clave, 'meta': meta, 'unidades': [{k: u.get(k) for k in CAMPOS} for u in us]}, ensure_ascii=False, separators=(',', ':'))
    v = dict(id='act_' + clave + '_' + h[:10], etiqueta=etiqueta, reforma=reforma, fecha_reforma=fu or '', desde=desde, hasta=None, ejercicio=x.get('ejercicio') if anuales.es_anual(x) else None,
             vigente=True, num=len(us), paginas=len(pags), aviso=aviso, archivo=url.split('/')[-1], sha256=hashlib.sha256(cuerpo.encode()).hexdigest(),
             fuente=x.get('ficha', url) if x['modo'] == 'crudo' else url, obtenido=hoy, verificacion=verif, precargado=True, tipo_cambio=clase, motivo_cambio=detalle)
    # ----- decisión -----
    if clase in ('documento_diferente', 'pendiente_validacion'):
        apartar(x, clave, clase, detalle, v, cuerpo, cambio, url); continue
    guardar_huellas(clave, hu, url)
    if clase in ('sin_cambio_texto', 'formato', 'validada'):
        if cambio and cambio.get('ahora'): x['control'] = cambio['ahora']
        if url != x['url']: x.setdefault('urls_anteriores', []).append(x['url']); x['url'] = url; x['control'] = {}
        x.pop('control_en_revision', None); x.pop('url_en_revision', None)
        reg(clave, resultado=clase, motivo=detalle, pendiente=False); evento(clave, clase, detalle); continue
    # reforma, corrección editorial, compilación nueva o ley anual nueva: se publica (la versión anterior se conserva en la aplicación)
    ent = {'clave': clave, 'version': v, 'b64': base64.b64encode(gzip.compress(cuerpo.encode(), 9)).decode()}
    if tipo == 'anual':
        ent['catalogo'] = dict(clave=clave, nombre=x.get('nombre'), ambito=x['ambito'], estado=x.get('estado', ''), ejercicio=x['ejercicio'], anterior=x.get('anterior'),
                               tipo='ley' if 'ley' in norm(x.get('nombre')) else 'presupuesto', materia='fiscal', formato=x['formato'])
        catalogo.append(ent['catalogo'])
        x.pop('control', None); x['control'] = {}
        if clave not in F: D['fuentes'].append(x); F[clave] = x
        anual_estado(x, 'incorporada')
    leyes.append(ent); cambiadas.append((clave, etiqueta, len(us)))
    x.update(version=v['id'], huella=h, unidades=len(us), etiqueta=etiqueta, fecha_reforma=fu or x.get('fecha_reforma', ''))
    if cambio and cambio.get('ahora'): x['control'] = cambio['ahora']
    if url != x['url'] and tipo != 'anual': x.setdefault('urls_anteriores', []).append(x['url']); x['url'] = url; x['control'] = {}
    x.pop('control_en_revision', None); x.pop('url_en_revision', None)
    reg(clave, resultado='publicada', motivo=f'{clase}: {detalle}', pendiente=False); evento(clave, clase, detalle)
    if tipo == 'descubierto':
        x['url'] = info['url']; d = next(d for d in D['descubrir'] if d['clave'] == clave); d['conocidos'].append(info['url'])
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
PEND = sorted(os.path.basename(f)[:-5] for f in glob.glob(K + '/pendientes/*.json'))
json.dump(ANU, open(K + '/anuales.json', 'w'), ensure_ascii=False, indent=1)
I['revision'] = dict(fecha=I['generado'], fuentes_con_falla=sorted(k for k, r in REG['fuentes'].items() if r.get('resultado') in ('falla', 'falla_lectura', 'lectura_dudosa')),
                     pendientes_de_validacion=PEND, leyes_anuales={b: {'ejercicio': e.get('ejercicio'), 'estado': e.get('estado')} for b, e in ANU.items()},
                     fuentes_revisadas=sum(1 for r in REG['fuentes'].values() if (r.get('ultima_consulta') or '')[:10] == hoy))
if hay:
    pid = ahora.strftime('%Y%m%d-%H%M')
    while pid in ya: pid += 'b'
    titulo = '; '.join([f"{(F[c]['nombre'] if F[c].get('nombre') else c.upper())}: {e}" for c, e, _ in cambiadas][:6])
    if dof['decretos']: titulo = (titulo + '; ' if titulo else '') + f"{len(dof['decretos'])} decreto(s) de reforma en el DOF"
    if not titulo and (dof['noticias'] or dof['indicadores']):
        fs = ', '.join(f'{x[6:]}/{x[4:6]}/{x[:4]}' for x in fechas_dof)
        titulo = f"DOF del {fs}: {len(dof['noticias'])} publicaciones fiscales" + (' e indicadores' if dof['indicadores'] else '')
    if '--etiqueta' in sys.argv: titulo = sys.argv[sys.argv.index('--etiqueta') + 1]
    paquete = dict(id=pid, fecha=hoy, titulo=titulo, leyes=leyes + dof['leyes'], reformas=dof['reformas'], decretos=dof['decretos'], noticias=dof['noticias'], indicadores=dof['indicadores'])
    if catalogo: paquete['catalogo'] = catalogo
    archivo = f'actualizaciones/{pid}.json'; os.makedirs(R + '/actualizaciones', exist_ok=True)
    s = json.dumps(paquete, ensure_ascii=False, separators=(',', ':')); open(R + '/' + archivo, 'w').write(s)
    I['paquetes'].append(dict(id=pid, fecha=hoy, archivo=archivo, titulo=titulo, leyes=[c for c, _, _ in cambiadas] + sorted({k for d in dof['decretos'] for k in d['leyes']}), bytes=len(s),
                              claves_dof=list(dof['noticias']) + [d['id'] for d in dof['decretos']]))
    print('publicada', archivo, round(len(s) / 1e6, 2), 'MB |', titulo)
else: print('sin novedades que publicar')
json.dump(I, open(R + '/indice.json', 'w'), ensure_ascii=False, indent=1)
json.dump(D, open(K + '/fuentes.json', 'w'), ensure_ascii=False, indent=1)
json.dump(REG, open(K + '/registro.json', 'w'), ensure_ascii=False, indent=1)
for n in notas: print('AVISO', n)
for c, cl, d in pendientes_nuevos: print('PENDIENTE DE VALIDACIÓN', c, cl, '-', d, '(kit/validar.py)')
