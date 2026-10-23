"""uso: python3 kit/revisar.py CORRIDA
Compara los encabezados obtenidos (kit/tmp/cab/CAB*.json) con el último control de cada fuente, lee los listados oficiales
(kit/tmp/cab/LST*.json) y los sondeos de leyes anuales, y decide qué textos hay que leer.
Escribe: kit/tmp/cambios.json, kit/tmp/extraer.json (lotes por sitio), kit/registro.json (estado y bitácora de cada fuente)
y kit/anuales.json (leyes de ingresos del ejercicio siguiente).
Reglas:
- Una fuente sin control previo solo registra su línea base (no es cambio).
- Una falla (sin respuesta, página de error, documento incompleto, redirección a un dominio no oficial) NUNCA cambia el
  control: se conserva la última versión válida y la fuente queda pendiente para la siguiente revisión (también la matutina).
- Un cambio de dominio solo se acepta si el destino es oficial (.gob.mx o fuentes.json → oficiales_extra).
- Un archivo renombrado (misma familia en el listado oficial, otra dirección) se trata como posible versión nueva."""
import json, os, glob, re, sys
from datetime import datetime, timezone, timedelta
K = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, K)
from identidad import familia, titulo_norm, parecido, es_oficial, url_norm, origen, host, fecha_en_nombre, anios
import anuales

corrida = sys.argv[1] if len(sys.argv) > 1 else ''
MX = timezone(timedelta(hours=-6)); AHORA = datetime.now(MX).isoformat(timespec='minutes'); HOY = AHORA[:10]
D = json.load(open(K + '/fuentes.json')); F = {x['clave']: x for x in D['fuentes']}
EXTRA = D.get('oficiales_extra', [])
def cargar(n, d): return json.load(open(K + '/' + n)) if os.path.exists(K + '/' + n) else d
REG = cargar('registro.json', {'fuentes': {}, 'eventos': []}); ANU = cargar('anuales.json', {})
def evento(clave, tipo, detalle):
    REG['eventos'].append(dict(t=AHORA, corrida=corrida, clave=clave, tipo=tipo, detalle=detalle)); REG['eventos'] = REG['eventos'][-500:]

# ---------- 1. encabezados ----------
obt, sondeos, sitios = {}, {}, []
for f in sorted(glob.glob(K + '/tmp/cab/CAB*.json')):
    j = json.loads(open(f).read())
    if isinstance(j.get('cab'), dict): obt.update(j['cab']); sondeos.update(j.get('son') or {}); sitios.append(j.get('sitio') or {})
    else: obt.update(j)                                                    # formato anterior del kit
plan = cargar('tmp/plan.json', [])
esperadas = {c for p in plan for c in p.get('claves', [])}
cambios, base, fallas, dominios = [], [], [], []
for k in sorted(esperadas - set(obt)):                                     # el sitio no se pudo abrir o no respondió nada
    if k in F: obt[k] = {'s': 0, 'ok': 0, 'err': 'sin respuesta del sitio (la página no abrió o la instrucción no terminó)', 'u': F[k]['url']}
for k, c in obt.items():
    x = F.get(k)
    if not x: continue
    r = REG['fuentes'].setdefault(k, {})
    r.update(ultima_consulta=c.get('t') or AHORA, url=c.get('u') or x['url'], url_final=c.get('f') or '', intentos=c.get('n', 1), verificacion=c.get('v', ''))
    ok = bool(c.get('s')) and c['s'] < 400 and c.get('ok', 1) != 0
    if ok and c.get('f') and host(c['f']) != host(x['url']):              # el documento redirigió a otro dominio
        if es_oficial(c['f'], EXTRA):
            dominios.append(dict(clave=k, antes=x['url'], ahora=c['f'])); evento(k, 'cambio_de_dominio', f"{x['url']} → {c['f']}")
            x.setdefault('urls_anteriores', []).append(x['url']); x['url'] = c['f']; x['origen'] = origen(c['f'])
        else:
            ok = False; c['err'] = 'redirige a un dominio que no es oficial: ' + host(c['f'])
    if not ok:
        motivo = c.get('err') or f"HTTP {c.get('s')}"
        r.update(resultado='falla', motivo=motivo, fallas_consecutivas=r.get('fallas_consecutivas', 0) + 1, pendiente=True)
        fallas.append(dict(clave=k, motivo=motivo, veces=r['fallas_consecutivas'])); evento(k, 'falla', motivo); continue
    nuevo = {'lm': c.get('lm', ''), 'et': c.get('et', ''), 'cl': c.get('cl', ''), 'h': c.get('h', '')}
    r.update(fallas_consecutivas=0, ultimo_ok=AHORA, motivo='')
    viejo = x.get('control')
    if not viejo:
        x['control'] = nuevo; base.append(k); r.update(resultado='linea_base', pendiente=False); continue
    def distinto(a, b):
        return (a['h'] and a['h'] != b.get('h')) or (a['lm'] and a['lm'] != b.get('lm')) or (a['et'] and a['et'] != b.get('et')) \
            or (not a['lm'] and not a['et'] and not a['h'] and a['cl'] and a['cl'] != b.get('cl'))
    if distinto(nuevo, viejo):
        if x.get('control_en_revision') and not distinto(nuevo, x['control_en_revision']):
            r.update(resultado='pendiente_validacion', pendiente=False)   # ya se leyó y espera validación (kit/validar.py)
        else:
            cambios.append({'clave': k, 'antes': viejo, 'ahora': nuevo, 'motivo': 'encabezado'}); r.update(resultado='cambio_por_verificar', pendiente=True)
    else:
        r.update(resultado='sin_cambio', pendiente=False)

# ---------- 2. listados oficiales: archivos renombrados ----------
filas, lst_err = [], []
for f in sorted(glob.glob(K + '/tmp/cab/LST*.json')):
    j = json.loads(open(f).read()); filas += j.get('filas', []); lst_err += j.get('err', [])
for lid, e in lst_err: evento(lid, 'falla_listado', e)
LIS = {l['id']: l for l in D.get('listados', [])}
leidos = {l for l, *_ in filas}
por_ambito = {}
for fl in filas:
    l = LIS.get(fl[0])
    if l: por_ambito.setdefault((l.get('ambito') or ('estatal' if l.get('estado') else 'federal'), l.get('estado') or ''), []).append(fl)
renombrados, no_listadas = [], []
for x in D['fuentes']:
    if x.get('archivado'): continue
    rows = por_ambito.get((x['ambito'], x.get('estado') or ''))
    if not rows: continue
    if any(url_norm(u) == url_norm(x['url']) for _, _, u, _ in rows): continue          # sigue publicada en la misma dirección
    fam = familia(x['url'])
    cands = [(t, u, fila) for _, t, u, fila in rows if familia(u) == fam]
    if not cands and x.get('nombre'):                                                  # mismo título y misma extensión
        ext = fam.split('|')[-1]
        cands = [(t, u, fila) for _, t, u, fila in rows if familia(u).split('|')[-1] == ext and parecido(titulo_norm(t or fila), x['nombre']) >= 0.9
                 and titulo_norm(t or fila).split() and abs(len(titulo_norm(t or fila).split()) - len(titulo_norm(x['nombre']).split())) <= 2
                 and anios(titulo_norm(t or fila)) <= anios(x['nombre'])]                    # otro ejercicio no es un renombre
    if not cands: no_listadas.append(x['clave']); continue
    cands.sort(key=lambda c: fecha_en_nombre(c[1]), reverse=True)                        # la publicación más reciente primero
    t, u, fila = cands[0]
    if not es_oficial(u, EXTRA) or url_norm(u) == url_norm(x.get('url_en_revision') or ''): continue   # ya leído y en espera de validación
    if len(cands) > 1: evento(x['clave'], 'duplicados_en_listado', ' | '.join(c[1] for c in cands[:4]))
    ya = next((c for c in cambios if c['clave'] == x['clave']), None)
    if ya: ya.update(url_nueva=u, motivo='renombrado')
    else: cambios.append({'clave': x['clave'], 'motivo': 'renombrado', 'url_nueva': u, 'fila': (fila or t)[:200]})
    renombrados.append(dict(clave=x['clave'], antes=x['url'], ahora=u)); evento(x['clave'], 'archivo_renombrado', f"{x['url']} → {u}")
    REG['fuentes'].setdefault(x['clave'], {}).update(resultado='cambio_por_verificar', pendiente=True)
if no_listadas: evento('', 'no_localizadas_en_listado', ', '.join(no_listadas[:40]))

# ---------- 3. leyes anuales del ejercicio siguiente ----------
anuales_nuevos = anuales.procesar(D, ANU, sondeos, filas, HOY, EXTRA)
for n in anuales_nuevos: evento(n['clave'], 'ley_anual_detectada', f"{n['ejercicio']}: {n['url']} ({n['via']})")

# ---------- 4. compilaciones nuevas de la RMF y otros documentos que cambian de dirección ----------
nuevos_docs = []
for i, d in enumerate(D.get('descubrir', []) + anuales.descubrir_siguiente(D, HOY)):
    fs = glob.glob(K + '/tmp/cab/DESC' + re.sub(r'[^A-Za-z0-9]', '', d['clave']).upper() + (f'P{i}' if d.get('derivado') else '') + '_*.json')
    if not fs: continue
    for e in json.load(open(sorted(fs)[-1])):
        if not e['u'].lower().split('?')[0].endswith('.pdf') or e['u'] in d['conocidos']: continue
        if d.get('derivado'):          # documento del ejercicio siguiente (p. ej. RMF 2027): es una ley anual nueva
            if re.search(d['patron'], e['t'] + ' ' + e['u'], re.I) and not re.search(r'anexo|modificaci|compilad|proyecto|versi[oó]n anticipada', e['t'] + ' ' + e['u'], re.I) \
               and es_oficial(e['u'], EXTRA) and not any(n['clave'] == d['clave'] for n in anuales_nuevos):
                anuales_nuevos.append(dict(clave=d['clave'], base=d['base'], ejercicio=d['ejercicio'], url=e['u'], titulo=e['t'], modo='pdf', origen=origen(e['u']), via='descubrir ' + d['pagina']))
                ANU.setdefault(anuales.base(d['base']), {}).update(estado='detectada', ejercicio=d['ejercicio'], url=e['u'], detectada=HOY, via='descubrir')
            continue
        if re.search(d['patron'], e['u'], re.I): nuevos_docs.append({'clave': d['clave'], 'url': e['u'], 'titulo': e['t']})

# ---------- 5. validación gradual: huellas por disposición de las fuentes que aún no las tienen ----------
PRIOR = {'cf': 0, 'lh': 1, 'li': 1, 'lcf': 2, 'lhm': 2, 'cpe': 3, 'cc': 9}
en_lectura = {c['clave'] for c in cambios} | {n['clave'] for n in nuevos_docs}
validar = sorted([k for k, r in REG['fuentes'].items() if r.get('resultado') == 'sin_cambio' and k in F and k not in en_lectura
                  and not os.path.exists(f'{K}/huellas/{k}.json')], key=lambda k: (PRIOR.get(k.split('_')[-1], 5), k))[:int(os.environ.get('AUREO_VALIDAR', '4'))]

# ---------- salida ----------
D['generado'] = HOY
json.dump(D, open(K + '/fuentes.json', 'w'), ensure_ascii=False, indent=1)
json.dump(REG, open(K + '/registro.json', 'w'), ensure_ascii=False, indent=1)
json.dump(ANU, open(K + '/anuales.json', 'w'), ensure_ascii=False, indent=1)
json.dump({'cambios': cambios, 'nuevos_docs': nuevos_docs, 'anuales_nuevos': anuales_nuevos, 'validar': validar, 'base': base, 'fallas': fallas,
           'dominios': dominios, 'renombrados': renombrados, 'listados_leidos': sorted(leidos), 'sitios': sitios},
          open(K + '/tmp/cambios.json', 'w'), ensure_ascii=False, indent=1)
CARGA = ('window.CORRIDA = "' + corrida + '"; await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\\n})()"))();\n')
lotes = {}
def poner(clave, url, modo, enc=''):
    o = origen(url); lotes.setdefault(o, []).append([clave, url, modo, enc])
for c in cambios:
    x = F[c['clave']]; poner(x['clave'], c.get('url_nueva') or x['url'], x['modo'], x.get('enc', ''))
for n in nuevos_docs: poner(n['clave'], n['url'], 'pdf')
for n in anuales_nuevos: poner(n['clave'], n['url'], n['modo'])
for k in validar: x = F[k]; poner(k, x['url'], x['modo'], x.get('enc', ''))
abrir = D.get('abrir', {})
json.dump([{'abrir': abrir.get(o, o + '/'), 'js': CARGA + 'lote(' + json.dumps(L, ensure_ascii=False) + '); await esperar()', 'despues': 'paq(etiquetaAqui("TXT"), i) para cada trozo'}
           for o, L in lotes.items()], open(K + '/tmp/extraer.json', 'w'), ensure_ascii=False, indent=1)
print('cambios:', [(c['clave'], c['motivo']) for c in cambios]); print('documentos nuevos:', [n['url'] for n in nuevos_docs])
print('leyes anuales nuevas:', [(n['clave'], n['url']) for n in anuales_nuevos])
print('renombrados:', [r['clave'] for r in renombrados], '| cambios de dominio:', [d['clave'] for d in dominios])
print('línea base registrada:', len(base), '| validación gradual:', validar)
print('fallas:', [(f['clave'], f['motivo'][:60]) for f in fallas])
print('sitios por leer:', len(lotes), '(kit/tmp/extraer.json)')
