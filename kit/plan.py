"""Arma el plan de revisión: qué pestaña abrir (sitio oficial) y qué instrucción ejecutar en ella.
uso: python3 kit/plan.py [federal|estatal|todo]   → escribe kit/tmp/plan.json y lo imprime resumido
Cada paso: abrir `abrir` en el navegador integrado, pegar kit/navegador.js y ejecutar `js`; luego mandar los trozos con
paq("ETIQUETA", i) para i = 0..n-1 y reunirlos con: python3 kit/reunir.py ETIQUETA kit/tmp/cab --texto"""
import json, os, sys, re
K = os.path.dirname(os.path.abspath(__file__)); os.makedirs(K + '/tmp', exist_ok=True)
amb = sys.argv[1] if len(sys.argv) > 1 else 'todo'
D = json.load(open(K + '/fuentes.json'))
grupos = {}
for x in D['fuentes']:
    if amb != 'todo' and x['ambito'] != amb: continue
    grupos.setdefault(x['origen'], []).append([x['clave'], x['url'], x['modo'], x.get('enc', '')])
plan = []
for i, (org, L) in enumerate(sorted(grupos.items())):
    etq = 'CAB' + re.sub(r'[^A-Za-z0-9]', '', org.split('//')[1])[:20].upper()
    plan.append(dict(etiqueta=etq, abrir=org + '/', n=len(L), js='preparar(await cabeceras(' + json.dumps(L, ensure_ascii=False) + ')); paq("' + etq + '", 0)'))
for d in D.get('descubrir', []):
    plan.append(dict(etiqueta='DESC' + re.sub(r'[^A-Za-z0-9]', '', d['clave']).upper(), abrir=d['pagina'], n=1, js='preparar(await enlaces(' + json.dumps(d['pagina']) + ', ' + json.dumps(d['patron']) + ')); paq("DESC' + re.sub(r'[^A-Za-z0-9]', '', d['clave']).upper() + '", 0)'))
json.dump(plan, open(K + '/tmp/plan.json', 'w'), ensure_ascii=False, indent=1)
for p in plan: print(f"{p['etiqueta']:28} {p['n']:3} fuentes  abrir {p['abrir']}")
print(len(plan), 'pasos; instrucciones completas en kit/tmp/plan.json')
