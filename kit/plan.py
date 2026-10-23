"""Plan de revisión: sitios oficiales que hay que abrir y la instrucción que se ejecuta en cada uno.
uso: python3 kit/plan.py CORRIDA [federal|estatal|todo]     (CORRIDA = aaaammddhhmm de esta revisión, p. ej. 202610190810)
Para cada paso: abrir `abrir` en el navegador integrado y ejecutar `js` con javascript_tool (una sola llamada por sitio).
Al terminar todos: python3 kit/reunir.py "_CORRIDA$" kit/tmp/cab --texto --patron
Incluye además:
- las fuentes que fallaron o quedaron pendientes en revisiones anteriores (kit/registro.json), aunque no sean de este ámbito;
- los listados oficiales (fuentes.json → listados) para detectar archivos renombrados y leyes nuevas (estatales: solo de noche);
- los sondeos de leyes de ingresos del ejercicio siguiente (kit/anuales.py)."""
import json, os, sys
from datetime import datetime, timezone, timedelta
K = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, K); os.makedirs(K + '/tmp', exist_ok=True)
import anuales
from identidad import origen, host
corrida = sys.argv[1]; amb = sys.argv[2] if len(sys.argv) > 2 else 'todo'
HOY = datetime.now(timezone(timedelta(hours=-6))).strftime('%Y-%m-%d')
D = json.load(open(K + '/fuentes.json'))
REG = json.load(open(K + '/registro.json')) if os.path.exists(K + '/registro.json') else {'fuentes': {}}
pend = {k for k, r in REG.get('fuentes', {}).items() if r.get('pendiente')}
CARGA = ('window.CORRIDA = "' + corrida + '"; await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\\n})()"))();\n')
dentro = lambda a: amb == 'todo' or a == amb
claves, abrir = {}, {}
for x in D['fuentes']:
    if x.get('archivado') or (not dentro(x['ambito']) and x['clave'] not in pend): continue
    claves.setdefault(x['origen'], []).append(x['clave'])
    # página del sitio que abre sin descargar nada y sin redirigir a otro dominio (nunca un documento: algunos sitios fuerzan la descarga)
    abrir[x['origen']] = D.get('abrir', {}).get(x['origen'], x['origen'] + '/')
# sondeos de leyes anuales: las federales en todas las corridas; las estatales, de noche
son = {}
for c in anuales.candidatos(D, HOY):
    amb_c = 'federal' if c['base'].startswith(('lif', 'pef')) or not c['base'].startswith('est_') else 'estatal'
    if not dentro(amb_c): continue
    o = next((x['origen'] for x in D['fuentes'] if x['clave'] == c['base']), c['origen'])
    son.setdefault(o, []).append([c['id'], c['url'], c['modo']]); claves.setdefault(o, []); abrir.setdefault(o, D.get('abrir', {}).get(o, o + '/'))
# sitios cuya política de seguridad no deja leer el kit desde GitHub: se incrusta el kit completo en la instrucción
NAV = open(K + '/navegador.js').read()
def INCR(o):
    F = [{k: x[k] for k in ('clave', 'url', 'modo', 'enc', 'origen') if k in x} for x in D['fuentes'] if x['origen'] == o]
    return 'window.CORRIDA = "' + corrida + '"; window.__F = ' + json.dumps({'fuentes': F}, ensure_ascii=False) + '; await (async () => {\n' + NAV + '\n})();\n'
carga = lambda o: INCR(o) if o in D.get('incrustar', []) else CARGA
def js_sitio(o):
    pre = 'window.ESPERADO = ' + json.dumps(o) + '; window.__SONDEO = ' + json.dumps(son.get(o, []), ensure_ascii=False) + ';\n'
    return carga(o) + pre + 'await revisarAqui()'
plan = [dict(tipo='encabezados', abrir=abrir[o], n=len(claves[o]), claves=claves[o], sondeos=len(son.get(o, [])), js=js_sitio(o))
        for o in sorted(claves, key=lambda o: (-len(claves[o]), o))]
# listados oficiales (uno por dominio; listadoAqui lee todos los del mismo dominio)
vistos = set()
for l in D.get('listados', []):
    a = l.get('ambito') or ('estatal' if l.get('estado') else 'federal')
    if not dentro(a) or host(l['pagina']) in vistos: continue
    vistos.add(host(l['pagina']))
    plan.append(dict(tipo='listado', abrir=l.get('abrir') or l['pagina'], n=sum(1 for m in D['listados'] if host(m['pagina']) == host(l['pagina'])), claves=[], js=CARGA + 'await listadoAqui()'))
for i, d in enumerate(D.get('descubrir', []) + anuales.descubrir_siguiente(D, HOY)):
    etq = 'DESC' + ''.join(c for c in d['clave'].upper() if c.isalnum()) + (f'P{i}' if d.get('derivado') else '') + '_' + corrida
    plan.append(dict(tipo='descubrir', abrir=d['pagina'], n=1, claves=[], js=CARGA + f'preparar(await enlaces({json.dumps(d["pagina"])}, {json.dumps(d["patron"])})); paq("{etq}", 0)'))
json.dump(plan, open(K + '/tmp/plan.json', 'w'), ensure_ascii=False, indent=1)
for i, p in enumerate(plan): print(f"{i:2} {p['tipo']:11} {p['n']:3}  {p['abrir']}" + (f"  (+{p['sondeos']} sondeos)" if p.get('sondeos') else ''))
print(len(plan), 'pasos;', len(pend), 'fuentes pendientes de revisiones anteriores incluidas.')
print('Si una instrucción responde «trabajando…», volver a ejecutar en la misma pestaña: await terminarAqui()')
