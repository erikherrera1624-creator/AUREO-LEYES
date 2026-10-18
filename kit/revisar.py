"""uso: python3 kit/revisar.py CORRIDA
Compara los encabezados obtenidos (kit/tmp/cab/CAB*.json) con el último control y lista lo que cambió.
uso: python3 kit/revisar.py   → escribe kit/tmp/cambios.json y kit/tmp/extraer.json (lotes por sitio para lote([...]))
Una fuente sin control previo solo registra su línea base (no se considera cambio)."""
import json, os, glob, re
K = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(K + '/fuentes.json')); F = {x['clave']: x for x in D['fuentes']}
obt = {}
for f in glob.glob(K + '/tmp/cab/CAB*.json'): obt.update(json.loads(open(f).read()))
cambios, base, fallas = [], [], []
for k, c in obt.items():
    x = F.get(k)
    if not x: continue
    if not c.get('s') or c.get('s', 0) >= 400: fallas.append((k, c)); continue
    nuevo = {'lm': c.get('lm', ''), 'et': c.get('et', ''), 'cl': c.get('cl', ''), 'h': c.get('h', '')}
    viejo = x.get('control')
    if not viejo: x['control'] = nuevo; base.append(k); continue
    distinto = (nuevo['h'] and nuevo['h'] != viejo.get('h')) or (nuevo['lm'] and nuevo['lm'] != viejo.get('lm')) or (nuevo['et'] and nuevo['et'] != viejo.get('et')) \
        or (not nuevo['lm'] and not nuevo['et'] and not nuevo['h'] and nuevo['cl'] and nuevo['cl'] != viejo.get('cl'))
    if distinto: cambios.append({'clave': k, 'antes': viejo, 'ahora': nuevo})
# compilaciones nuevas de la RMF y otros documentos que cambian de dirección
nuevos_docs = []
for d in D.get('descubrir', []):
    fs = glob.glob(K + '/tmp/cab/DESC' + re.sub(r'[^A-Za-z0-9]', '', d['clave']).upper() + '_*.json')
    if not fs: continue
    for e in json.load(open(sorted(fs)[-1])):
        if e['u'].lower().endswith('.pdf') and e['u'] not in d['conocidos']: nuevos_docs.append({'clave': d['clave'], 'url': e['u'], 'titulo': e['t']})
json.dump(D, open(K + '/fuentes.json', 'w'), ensure_ascii=False, indent=1)
lotes = {}
for c in cambios:
    x = F[c['clave']]; lotes.setdefault(x['origen'], []).append([x['clave'], x['url'], x['modo'], x.get('enc', '')])
for n in nuevos_docs:
    org = re.match(r'https?://[^/]+', n['url']).group(0); lotes.setdefault(org, []).append([n['clave'], n['url'], 'pdf', ''])
json.dump({'cambios': cambios, 'nuevos_docs': nuevos_docs, 'base': base, 'fallas': fallas}, open(K + '/tmp/cambios.json', 'w'), ensure_ascii=False, indent=1)
import sys as _s; corrida = _s.argv[1] if len(_s.argv) > 1 else ''
CARGA = ('window.CORRIDA = "' + corrida + '"; await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\\n})()"))();\n')
json.dump([{'abrir': o + '/', 'js': CARGA + 'lote(' + json.dumps(L, ensure_ascii=False) + '); await esperar()', 'despues': 'paq(etiquetaAqui("TXT"), i) para cada trozo'} for o, L in lotes.items()],
          open(K + '/tmp/extraer.json', 'w'), ensure_ascii=False, indent=1)
print('cambios:', [c['clave'] for c in cambios]); print('documentos nuevos:', [n['url'] for n in nuevos_docs])
print('línea base registrada:', len(base), '| sin respuesta:', [k for k, _ in fallas])
print('sitios por leer:', len(lotes), '(kit/tmp/extraer.json)')
