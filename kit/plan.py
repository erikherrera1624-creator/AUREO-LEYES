"""Plan de revisión: sitios oficiales que hay que abrir y la instrucción que se ejecuta en cada uno.
uso: python3 kit/plan.py CORRIDA [federal|estatal|todo]     (CORRIDA = aaaammddhhmm de esta revisión, p. ej. 202610190810)
Para cada paso: abrir `abrir` en el navegador integrado y ejecutar `js` con javascript_tool (una sola llamada por sitio).
Al terminar todos: python3 kit/reunir.py "_CORRIDA$" kit/tmp/cab --texto --patron"""
import json, os, sys
K = os.path.dirname(os.path.abspath(__file__)); os.makedirs(K + '/tmp', exist_ok=True)
corrida = sys.argv[1]; amb = sys.argv[2] if len(sys.argv) > 2 else 'todo'
D = json.load(open(K + '/fuentes.json'))
CARGA = ('window.CORRIDA = "' + corrida + '"; await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\\n})()"))();\n')
origenes, abrir = {}, {}
for x in D['fuentes']:
    if amb != 'todo' and x['ambito'] != amb: continue
    origenes[x['origen']] = origenes.get(x['origen'], 0) + 1
    # página del sitio que abre sin descargar nada (nunca un documento: algunos sitios fuerzan la descarga)
    abrir[x['origen']] = D.get('abrir', {}).get(x['origen'], x['origen'] + '/')
plan = [dict(abrir=abrir[o], n=n, js=CARGA + 'await revisarAqui()') for o, n in sorted(origenes.items(), key=lambda t: (-t[1], t[0]))]
for d in D.get('descubrir', []):
    etq = 'DESC' + ''.join(c for c in d['clave'].upper() if c.isalnum()) + '_' + corrida
    plan.append(dict(abrir=d['pagina'], n=1, js=CARGA + f'preparar(await enlaces({json.dumps(d["pagina"])}, {json.dumps(d["patron"])})); paq("{etq}", 0)'))
json.dump(plan, open(K + '/tmp/plan.json', 'w'), ensure_ascii=False, indent=1)
for i, p in enumerate(plan): print(f"{i:2} {p['n']:3} fuentes  {p['abrir']}")
print(len(plan), 'sitios. Instrucción (igual en todos los sitios de leyes):'); print(plan[0]['js'])
