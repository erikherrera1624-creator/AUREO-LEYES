"""Lecturas que esperan validación (construir.py no las publicó porque no había evidencia suficiente).
uso: python3 kit/validar.py listar
     python3 kit/validar.py ver CLAVE          → motivo, versión propuesta y primeras disposiciones
     python3 kit/validar.py aprobar CLAVE      → la publica como nueva versión (la anterior se conserva en la aplicación)
     python3 kit/validar.py descartar CLAVE    → se queda la versión actual; el archivo leído se toma como conocido
Después de aprobar o descartar: commit y push como en la revisión programada."""
import json, os, sys, glob, gzip, base64
from datetime import datetime, timezone, timedelta
K = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(K); sys.path.insert(0, K)
from identidad import huellas_unidades
import anuales
ahora = datetime.now(timezone(timedelta(hours=-6))); hoy = ahora.strftime('%Y-%m-%d')
orden, clave = (sys.argv[1] if len(sys.argv) > 1 else 'listar'), (sys.argv[2] if len(sys.argv) > 2 else '')
if orden == 'listar':
    for f in sorted(glob.glob(K + '/pendientes/*.json')):
        p = json.load(open(f)); print(f"{p['clave']:24} {p['fecha']}  {p['clase']:22} {p['detalle'][:90]}")
    sys.exit()
P = json.load(open(f'{K}/pendientes/{clave}.json')); cuerpo = gzip.decompress(open(f'{K}/pendientes/{clave}.gz', 'rb').read()).decode()
D = json.load(open(K + '/fuentes.json')); F = {x['clave']: x for x in D['fuentes']}
REG = json.load(open(K + '/registro.json')) if os.path.exists(K + '/registro.json') else {'fuentes': {}, 'eventos': []}
def evento(tipo, detalle): REG.setdefault('eventos', []).append(dict(t=ahora.isoformat(timespec='minutes'), clave=clave, tipo=tipo, detalle=detalle))
def cerrar():
    os.remove(f'{K}/pendientes/{clave}.json'); os.remove(f'{K}/pendientes/{clave}.gz')
    json.dump(D, open(K + '/fuentes.json', 'w'), ensure_ascii=False, indent=1); json.dump(REG, open(K + '/registro.json', 'w'), ensure_ascii=False, indent=1)
if orden == 'ver':
    j = json.loads(cuerpo); print(json.dumps({k: P[k] for k in ('clave', 'clase', 'detalle', 'fecha', 'url')}, ensure_ascii=False, indent=1))
    print('versión propuesta:', (P.get('version') or {}).get('etiqueta'), '|', len(j['unidades']), 'disposiciones')
    for u in j['unidades'][:5]: print('-', u.get('titulo'), '|', (u.get('texto') or '')[:160].replace('\n', ' '))
    sys.exit()
x = F.get(clave)
if orden == 'descartar':
    if x:
        if P.get('control'): x['control'] = P['control']
        x.pop('control_en_revision', None); x.pop('url_en_revision', None)
    REG['fuentes'].setdefault(clave, {}).update(resultado='descartada', motivo='lectura descartada en la validación', pendiente=False); evento('descartada', P['detalle'])
    cerrar(); print('descartada', clave); sys.exit()
if orden != 'aprobar' or not P.get('version'): sys.exit('nada que aprobar (¿documento diferente? use descartar)')
v = dict(P['version'], tipo_cambio=P['version'].get('tipo_cambio', 'validada'), motivo_cambio='aprobada en validación: ' + P['detalle'])
ent = {'clave': clave, 'version': v, 'b64': base64.b64encode(gzip.compress(cuerpo.encode(), 9)).decode()}
if not x:                                                        # ley anual nueva
    fi = P.get('ficha') or {}; base_x = F.get(fi.get('anterior')) or {}
    x = dict({k: w for k, w in base_x.items() if k not in ('control', 'version', 'huella', 'etiqueta', 'fecha_reforma')}, clave=clave, url=P['url'], **{k: w for k, w in fi.items() if w is not None})
    x['control'] = {}; D['fuentes'].append(x)
    ent['catalogo'] = dict(clave=clave, nombre=x.get('nombre'), ambito=x.get('ambito'), estado=x.get('estado', ''), ejercicio=x.get('ejercicio'), anterior=x.get('anterior'), tipo='ley', materia='fiscal', formato=x.get('formato'))
us = json.loads(cuerpo)['unidades']
os.makedirs(K + '/huellas', exist_ok=True); json.dump({'clave': clave, 'fecha': hoy, 'url': P['url'], 'u': huellas_unidades(us)}, open(f'{K}/huellas/{clave}.json', 'w'), separators=(',', ':'))
x.update(version=v['id'], unidades=v['num'], etiqueta=v['etiqueta'], fecha_reforma=v.get('fecha_reforma') or x.get('fecha_reforma', ''))
import hashlib
x['huella'] = hashlib.sha256('\n'.join((u.get('numero') or '') + '|' + (u.get('texto') or '') for u in us).encode()).hexdigest()[:24]
if P.get('control'): x['control'] = P['control']
if P['url'] != x.get('url'): x.setdefault('urls_anteriores', []).append(x.get('url')); x['url'] = P['url']; x['control'] = {}
x.pop('control_en_revision', None); x.pop('url_en_revision', None)
I = json.load(open(R + '/indice.json')); pid = ahora.strftime('%Y%m%d-%H%M') + 'v'
paquete = dict(id=pid, fecha=hoy, titulo=f"{x.get('nombre') or clave}: {v['etiqueta']}", leyes=[ent], reformas={}, decretos=[], noticias={}, indicadores={})
if ent.get('catalogo'): paquete['catalogo'] = [ent['catalogo']]
s = json.dumps(paquete, ensure_ascii=False, separators=(',', ':')); open(f'{R}/actualizaciones/{pid}.json', 'w').write(s)
I['paquetes'].append(dict(id=pid, fecha=hoy, archivo=f'actualizaciones/{pid}.json', titulo=paquete['titulo'], leyes=[clave], bytes=len(s), claves_dof=[]))
I.setdefault('revision', {}).setdefault('pendientes_de_validacion', [])
I['revision']['pendientes_de_validacion'] = [c for c in I['revision']['pendientes_de_validacion'] if c != clave]
json.dump(I, open(R + '/indice.json', 'w'), ensure_ascii=False, indent=1)
REG['fuentes'].setdefault(clave, {}).update(resultado='publicada', motivo='aprobada en validación', pendiente=False); evento('aprobada', P['detalle'])
if x.get('anterior'):
    A = json.load(open(K + '/anuales.json')) if os.path.exists(K + '/anuales.json') else {}
    A.setdefault(anuales.base(x['anterior']), {}).update(estado='incorporada', ejercicio=x.get('ejercicio'), clave_nueva=clave, fecha=hoy)
    json.dump(A, open(K + '/anuales.json', 'w'), ensure_ascii=False, indent=1)
cerrar(); print('publicada', pid, '|', paquete['titulo'])
