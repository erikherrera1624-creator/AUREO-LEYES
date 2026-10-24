"""Arma las versiones de años anteriores (historicos/) a partir de lo que leyó job.js en web.archive.org.
job.js manda, por ley, cada versión como diferencias por disposición contra la versión siguiente (la más reciente
contra la vigente de la aplicación). Aquí se reconstruye cada texto completo con el mismo formato de la biblioteca
y se publica en historicos/<clave>.json (lista con el formato de la precarga) e historicos/indice.json.

uso: python3 kit/historicos/armar.py paquete.b64 carpeta_actuales reformas.json
  paquete.b64      texto base64 (gzip de JSON) que regresó job.js (trozos <<HIST|i|n>> unidos)
  carpeta_actuales actual_<clave>.json: {clave, meta, unidades} de la versión vigente de cada ley (la de la aplicación)
  reformas.json    historial de reformas de la aplicación ({clave: [{f: aaaa-mm-dd, ...}]})"""
import base64, gzip, hashlib, json, os, sys, datetime
K = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(os.path.dirname(K))
paquete, actuales, reformas = sys.argv[1], sys.argv[2], sys.argv[3]
D = json.loads(gzip.decompress(base64.b64decode(open(paquete).read().strip())))
REF = json.load(open(reformas))
HOY = datetime.date.today().isoformat()
CAMPOS = ('tipo', 'numero', 'nn', 'titulo', 'ubicacion', 'texto', 'fechas', 'pagina', 'orden')
dmy = lambda f: f'{f[8:10]}/{f[5:7]}/{f[:4]}'
menos1 = lambda f: (datetime.date.fromisoformat(f) - datetime.timedelta(days=1)).isoformat()
def claves(us):
    c, out = {}, []
    for u in us: n = c.get(u['nn'], 0); c[u['nn']] = n + 1; out.append(f"{u['nn']}#{n}")
    return out
def fnv8(st):
    h = 0x811c9dc5; b = st.encode('utf-16-le')
    for q in range(0, len(b), 2): h ^= b[q] | (b[q + 1] << 8); h = (h * 0x01000193) & 0xffffffff
    return format(h, '08x')
canon = lambda u: '|'.join(str(u.get(f) or '') for f in ('tipo', 'nn', 'titulo', 'ubicacion', 'texto'))
def reconstruir(delta, ref):
    rk = dict(zip(claves(ref), ref)); us = []
    for e in delta:
        if isinstance(e, list):
            k, pag, orden = e; u = dict(rk[k]); u['pagina'] = pag; u['orden'] = orden; us.append(u); continue
        base = rk.get(e['k']); bp = (base or {}).get('texto', '').split('\n\n')
        ps = [bp[x] if isinstance(x, int) else x for x in e['p']]
        u = dict(e['f']); u['texto'] = '\n\n'.join(ps); us.append(u)
    return [{k: u.get(k) for k in CAMPOS} for u in us]
os.makedirs(f'{R}/historicos', exist_ok=True)
indice = {'generado': HOY, 'fuente': 'Compilaciones de la Cámara de Diputados conservadas por Internet Archive (web.archive.org)', 'leyes': {}}
viejo = f'{R}/historicos/indice.json'
if os.path.exists(viejo): indice['leyes'] = json.load(open(viejo)).get('leyes', {})
for clave, L in D.items():
    if not L.get('versiones'): print(clave, 'sin versiones'); continue
    act = json.load(open(f'{actuales}/actual_{clave}.json'))
    fechas_ref = sorted({x.get('f') for x in REF.get(clave, []) if x.get('f')})
    desde_actual = (act.get('meta') or {}).get('fecha_ultima_reforma') or fechas_ref[-1]
    # 1) reconstrucción en el mismo orden en que job.js encadenó las diferencias
    ref, armadas = act['unidades'], []
    for v in L['versiones']:
        us = reconstruir(v['u'], ref)
        assert len(us) == v['num'], (clave, v['f'], len(us), v['num'])
        if v.get('chk') and fnv8('\n'.join(canon(u) for u in us)) != v['chk']:
            raise SystemExit(f'{clave} {v["f"]}: el texto reconstruido no coincide con el leído (huella distinta); no se publica')
        ref = us; armadas.append((v, us))
    # 2) fecha efectiva: la última reforma declarada en la portada; si las notas de reforma del propio texto traen
    #    fechas posteriores (portada sin «última reforma»), manda la nota más reciente
    porf = {}
    for v, us in armadas:
        # fechas de reforma conocidas que el propio texto cita: notas de los artículos y transitorios de cada decreto incorporado
        conocidas = set(fechas_ref)
        citadas = sorted({f for u in us for f in (u.get('fechas') or '').split(',') if f and f <= HOY and f in conocidas})
        f, deducida = v['f'], False
        sin_portada = v.get('tipo') == 'original' or not (v.get('meta') or {}).get('ultima_reforma')
        if citadas and citadas[-1] > f:
            # la compilación incluye un decreto posterior a la fecha de su portada (portada sin «última reforma» o desactualizada)
            f, deducida = citadas[-1], True
        if f >= desde_actual: print(f'  {clave}: se omite la copia de {v["ts"]} (corresponde a la versión vigente, {f})'); continue
        if f in porf and porf[f][0]['ts'] >= v['ts']: continue
        porf[f] = (v, us, deducida)
    salida, idx = [], []
    for f in sorted(porf, reverse=True):
        v, us, deducida = porf[f]
        sig = [x for x in fechas_ref if x > f]; hasta = sig[0] if sig else desde_actual
        meta = dict(v.get('meta') or {}, paginas=v['paginas'])
        if deducida: meta.update(ultima_reforma=f'DOF {f[8:10]}-{f[5:7]}-{f[:4]}', fecha_ultima_reforma=f, fecha_deducida_de_notas=True)
        cuerpo = json.dumps({'clave': clave, 'meta': meta, 'unidades': us}, ensure_ascii=False, separators=(',', ':'))
        sha = hashlib.sha256(cuerpo.encode()).hexdigest()
        original = not deducida and (v.get('tipo') == 'original' or not meta.get('ultima_reforma'))
        captura = f"{v['ts'][6:8]}/{v['ts'][4:6]}/{v['ts'][:4]}"
        etq = (f'Texto original (DOF {dmy(f)}), vigente hasta el {dmy(menos1(hasta))}' if original
               else f'Texto del {dmy(f)} al {dmy(menos1(hasta))} (última reforma DOF {dmy(f)})')
        archivada = f"https://web.archive.org/web/{v['ts']}/{v['archivo']}"
        ver = dict(id=f'hist_{clave}_{f}', etiqueta=etq, reforma=meta.get('ultima_reforma') or f'DOF {f[8:10]}-{f[5:7]}-{f[:4]}', fecha_reforma=f, desde=f, hasta=hasta,
                   ejercicio=None, vigente=False, num=len(us), paginas=v['paginas'], historico=True,
                   aviso=f'Versión anterior: compilación de la Cámara de Diputados tal como estaba publicada el {captura} (copia conservada por Internet Archive). '
                         + ('La fecha de la última reforma se tomó de las notas de reforma y de los transitorios que trae el propio texto (la portada de la copia no la indicaba o no estaba al día). ' if deducida else '')
                         + 'Para sustentar un acto, coteje con el decreto publicado en el Diario Oficial.',
                   archivo=v['archivo'].split('/')[-1], sha256=sha, fuente=archivada, fuente_original=v['archivo'].replace(':80/', '/'), capturado=f"{v['ts'][:4]}-{v['ts'][4:6]}-{v['ts'][6:8]}",
                   obtenido=HOY, verificacion='copia archivada de la compilación oficial', precargado=True)
        salida.append({'clave': clave, 'version': ver, 'b64': base64.b64encode(gzip.compress(cuerpo.encode(), 9)).decode()})
        idx.append({k: ver[k] for k in ('id', 'etiqueta', 'fecha_reforma', 'desde', 'hasta', 'historico', 'num', 'capturado')})
        print(f'  {clave} {f}{" (fecha tomada del texto)" if deducida else ""}: {len(us)} disposiciones, hasta {hasta}')
    texto = json.dumps(salida, ensure_ascii=False, separators=(',', ':'))
    open(f'{R}/historicos/{clave}.json', 'w').write(texto)
    con = {v['fecha_reforma'] for v in idx} | {desde_actual}
    faltan = [x for x in fechas_ref if x not in con and x >= min(con)]
    indice['leyes'][clave] = {'archivo': f'{clave}.json', 'v': hashlib.sha256(texto.encode()).hexdigest()[:12], 'bytes': len(texto),
                              'versiones': sorted(idx, key=lambda x: x['desde']), 'sin_copia': faltan}
    print(clave, len(idx), 'versiones,', len(texto) // 1024, 'KB; reformas sin copia archivada:', len(faltan))
json.dump(indice, open(viejo, 'w'), ensure_ascii=False, indent=1)
