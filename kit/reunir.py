"""Reúne los trozos <<ETIQUETA|i|n>>…<<FIN>> que regresó el navegador (quedan guardados como resultados de herramienta).
uso: python3 kit/reunir.py ETIQUETA carpeta_salida [--texto]
  - normal: el contenido es un objeto {nombre: base64-gzip de páginas JSON | RAW_nombre: base64-gzip de archivo}; escribe nombre.json / nombre.bin
  - --texto: el contenido es texto JSON libre; escribe carpeta_salida/ETIQUETA.json"""
import json, glob, os, re, sys, base64, gzip
etq, salida = sys.argv[1], sys.argv[2]; texto = '--texto' in sys.argv
if '--patron' in sys.argv:   # reúne todas las etiquetas que cumplan el patrón (p. ej. "^CAB.*_20261018-0810$")
    import subprocess
    pat = re.compile(etq); vistas = set()
    for f in glob.glob('/root/.claude/projects/*/*/tool-results/*') + glob.glob('/root/.claude/projects/*/tool-results/*'):
        try: t = open(f).read(400)
        except Exception: continue
        for m in re.finditer(r'<<([A-Za-z0-9_\-]+)\|\d+\|\d+>>', t):
            if pat.search(m.group(1)): vistas.add(m.group(1))
    for e in sorted(vistas): subprocess.run([sys.executable, __file__, e, salida] + (['--texto'] if texto else []), check=False)
    sys.exit()
tro, total = {}, None
for f in glob.glob('/root/.claude/projects/*/*/tool-results/*') + glob.glob('/root/.claude/projects/*/tool-results/*'):
    try: crudo = json.load(open(f))
    except Exception: continue
    t = crudo[0]['text'] if isinstance(crudo, list) and crudo and isinstance(crudo[0], dict) else ''
    k = t.find('<<' + etq + '|')
    if k < 0: continue
    try: t = json.loads(t[:t.rindex('"') + 1])
    except Exception: pass
    k = t.find('<<' + etq + '|'); m = re.match(r'<<([^|]+)\|(\d+)\|(\d+)>>', t[k:])
    if not m or m.group(1) != etq: continue
    i, n = int(m.group(2)), int(m.group(3)); total = n
    cuerpo = t[k + m.end():]; tro[i] = cuerpo[:cuerpo.index('<<FIN>>')]
assert total is not None, 'sin trozos para ' + etq
falta = [i for i in range(total) if i not in tro]; assert not falta, f'faltan trozos {falta}'
todo = ''.join(tro[i] for i in range(total)); os.makedirs(salida, exist_ok=True)
if texto:
    open(f'{salida}/{etq}.json', 'w').write(todo); print(etq, len(todo), 'car'); sys.exit()
B = json.loads(todo)
for k in [k for k in B if k.startswith('RAW_')]:
    open(f'{salida}/{k[4:]}.bin', 'wb').write(gzip.decompress(base64.b64decode(B.pop(k)))); print('crudo', k[4:])
for k, v in B.items():
    pags = json.loads(gzip.decompress(base64.b64decode(v))); json.dump(pags, open(f'{salida}/{k}.json', 'w')); print(k, len(pags), 'pág', sum(map(len, pags)), 'car')
