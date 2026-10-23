"""Diario Oficial de la Federación → noticias, indicadores y decretos de reforma para la aplicación.
1) python3 kit/dof.py seleccionar AAAA-MM-DD CORRIDA   lee kit/tmp/dof/DOFAAAAMMDD_*.json (sumarioDOF) y escribe la instrucción textosDOF(...) para las notas relevantes
2) python3 kit/dof.py procesar AAAA-MM-DD CORRIDA      lee además kit/tmp/dof/DOFTXAAAAMMDD_*.json (textosDOF) y escribe kit/tmp/dof_AAAAMMDD.json"""
import json, os, re, sys, gzip, base64, unicodedata
K = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, K)
from decretos_comun import NOMBRES, procesar
NOMBRES = dict(NOMBRES, rmf_2026=r'resolucion miscelanea fiscal para 2026', rlisr=r'reglamento de la ley del impuesto sobre la renta', rliva=r'reglamento de la ley del impuesto al valor agregado',
               rcff=r'reglamento del codigo fiscal de la federacion', rladua=r'reglamento de la ley aduanera', rlss_macerf=r'reglamento de la ley del seguro social en materia de afiliacion',
               cpeum=r'constitucion politica de los estados unidos mexicanos')
ABREV = {'cff': 'CFF', 'lisr': 'LISR', 'liva': 'LIVA', 'lieps': 'LIEPS', 'lfd': 'LFD', 'lcf': 'LCF', 'lss': 'LSS', 'lifnvt': 'LINFONAVIT', 'lsar': 'LSAR', 'ccom': 'CCom', 'lgsm': 'LGSM', 'lgtoc': 'LGTOC',
         'lcm': 'LCM', 'lfpiorpi': 'LFPIORPI', 'lic': 'LIC', 'lmv': 'LMV', 'lft': 'LFT', 'lfpca': 'LFPCA', 'lamp': 'Ley de Amparo', 'lfpa': 'LFPA', 'ladua': 'LA', 'lce': 'LCE', 'lie': 'LIE',
         'lif_2026': 'LIF 2026', 'lfdc': 'LFDC', 'rmf_2026': 'RMF 2026', 'rlisr': 'RLISR', 'rliva': 'RLIVA', 'rcff': 'RCFF', 'rladua': 'RLA', 'rlss_macerf': 'RACERF', 'cpeum': 'CPEUM'}
def norm(t): return unicodedata.normalize('NFD', t or '').encode('ascii', 'ignore').decode().lower()
DEP_FISCAL = r'hacienda y credito publico|administracion tributaria|seguro social|fondo nacional de la vivienda|trabajo y prevision social|banco de mexico|estadistica y geografia|procuraduria de la defensa del contribuyente|ahorro para el retiro'
TEMA = r'fiscal|impuest|tributari|miscelanea|aduan|comercio exterior|arancel|seguro social|infonavit|vivienda para los trabajadores|salari|unidad de medida|indice nacional de precios|recargo|estimulo|cfdi|comprobante|contribu|derecho|retencion|deduc|devoluc|factura|inpc|udis|valor de la unidad|ley federal del trabajo|ahorro para el retiro'
EXCLUIR = r'tasas? de interes interbancari|^tasa de interes|convocatoria|licitacion|edicto|sentencia|cartel|aviso de deslinde|norma oficial mexicana|resolucion por la que se modifica.*(estatuto|organico)'
def relevante(n):
    t, d = norm(n['titulo']), norm(n['dependencia'] + ' ' + n['poder'])
    if re.search(r'^tipo de cambio para solventar|^indice nacional de precios|^valor de la unidad de medida|unidades de inversion', t): return 'indicador'
    if re.search(EXCLUIR, t): return ''
    if re.match(r'(ley de ingresos|presupuesto de egresos de la federacion)', t): return 'nota'
    if re.match(r'(decreto|acuerdo|resolucion|reglas|lineamientos|aviso)', t) and (re.search(DEP_FISCAL, d) or re.search(TEMA, t)): return 'nota'
    if re.match(r'decreto por el que se (reforma|adiciona|deroga|expide|abroga)', t) and any(re.search(p, t) for p in NOMBRES.values()): return 'nota'
    return ''
def leyes_de(t):
    n = norm(t); ks = [k for k, p in NOMBRES.items() if re.search(p, n)]
    # la Ley de Ingresos y la RMF son de cada ejercicio: se asocian a la clave de su año (lif_2027, rmf_2027), no a la de 2026
    m = re.search(r'ley de ingresos de la federacion para el ejercicio fiscal (?:de |del )?((?:19|20)\d{2})', n)
    if m: ks = [('lif_' + m.group(1)) if k == 'lif_2026' else k for k in ks]
    m = re.search(r'resolucion miscelanea fiscal para (?:el )?((?:19|20)\d{2})', n)
    if m and 'rmf_' + m.group(1) not in ks: ks = [k for k in ks if k != 'rmf_2026'] + ['rmf_' + m.group(1)]
    return list(dict.fromkeys(ks))
import glob as _g
def ruta(f, pre):
    fs = sorted(_g.glob(f'{K}/tmp/dof/{pre}{f.replace("-", "")}_*.json') + _g.glob(f'{K}/tmp/dof/{pre}{f.replace("-", "")}.json'), key=os.path.getmtime)
    return fs[-1] if fs else f'{K}/tmp/dof/{pre}{f.replace("-", "")}.json'
if len(sys.argv) > 1 and sys.argv[1] == 'pendientes':   # python3 kit/dof.py pendientes [noche] → fechas por revisar, sin tope de días
    from datetime import date, datetime, timedelta, timezone
    I = json.load(open(os.path.dirname(K) + '/indice.json')); hoy = datetime.now(timezone(timedelta(hours=-6))).date()
    desde = date.fromisoformat(I.get('dof_revisado') or str(hoy)) + timedelta(days=1)
    fechas = [desde + timedelta(days=i) for i in range((hoy - desde).days + 1)]
    if len(sys.argv) > 2 and sys.argv[2] == 'noche' and hoy not in fechas: fechas.append(hoy)   # edición vespertina del día
    print(' '.join(f.isoformat() for f in fechas) or '(al día)'); sys.exit()
modo, fecha = sys.argv[1], sys.argv[2]; corrida = sys.argv[3] if len(sys.argv) > 3 else ''
MINUS = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'para', 'en', 'el', 'a'}
def titulo_dep(t): return ' '.join(w.lower() if (w.lower() in MINUS and i) else w.capitalize() for i, w in enumerate((t or '').split()))
S = json.load(open(ruta(fecha, 'DOF')))
if isinstance(S.get('notas'), str): S['notas'] = json.loads(S['notas'])
sel = [n for n in S['notas'] if relevante(n)]
if modo == 'seleccionar':
    etq = 'DOFTX' + fecha.replace('-', '') + ('_' + corrida if corrida else '')
    js = ('if (typeof textosDOF !== "function") await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\\n})()"))();\n'
          + 'const t = preparar(await textosDOF(' + json.dumps([{'codigo': n['codigo'], 'url': n['url']} for n in sel], ensure_ascii=False) + ')); t + "\\n" + paq("' + etq + '", 0)')
    open(f'{K}/tmp/dof/seleccion_{fecha}.js', 'w').write(js)
    print(len(S['notas']), 'notas;', len(sel), 'relevantes'); [print(' -', relevante(n), n['dependencia'][:40], '|', n['titulo'][:110]) for n in sel]
    print('instrucción en kit/tmp/dof/seleccion_' + fecha + '.js (etiqueta sugerida DOFTX' + fecha.replace('-', '') + ')'); sys.exit()
TX = json.load(open(ruta(fecha, 'DOFTX'))) if os.path.exists(ruta(fecha, 'DOFTX')) else {}
out = dict(noticias={}, indicadores={}, reformas={}, decretos=[], leyes=[])
ED = {'MAT': 'edición matutina', 'VES': 'edición vespertina', 'EXT': 'edición extraordinaria'}
for n in sel:
    tipo = relevante(n); ps = TX.get(n['codigo']) or []; texto = ' '.join(ps)
    if tipo == 'indicador':
        t = norm(n['titulo']); m = None
        if t.startswith('tipo de cambio'):
            m = re.search(r'(?:fue de|es de)\s*\$?\s*([\d]{1,3}\.\d{2,6})', texto)
            if m: out['indicadores'][f'tipo_cambio_{fecha}'] = dict(clave='tipo_cambio', nombre='Tipo de cambio FIX (dólar)', valor=float(m.group(1)), unidad='MXN por dólar', desde=fecha, fuente=f'Banco de México, DOF {fecha}', url=n['url'], verificacion='oficial (DOF)')
        elif t.startswith('indice nacional de precios'):
            m = re.search(r'(\d{3}\.\d{3,4})\s*puntos', texto) or re.search(r'es de\s*(\d{3}\.\d{3,4})', texto)
            mes = re.search(r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})', norm(texto))
            if m: out['indicadores'][f'inpc_{fecha}'] = dict(clave='inpc', nombre='INPC' + (f' de {mes.group(1)} de {mes.group(2)}' if mes else ''), valor=float(m.group(1)), unidad='puntos (base 2a. quincena de julio 2018 = 100)', desde=fecha, fuente=f'INEGI, DOF {fecha}', url=n['url'], verificacion='oficial (DOF)')
        if m: continue
    ks = leyes_de(n['titulo'] + ' ' + ' '.join(ps[:6]))
    es_reforma = bool(re.match(r'(decreto por el que se (reforma|adiciona|deroga|expide|abroga))|(.*resolucion de modificaciones a la resolucion miscelanea)|(ley de ingresos de la federacion para)', norm(n['titulo'])))
    resumen = ' '.join(p for p in ps[1:8] if len(p) > 40 and not re.match(r'(Al margen|En el documento que usted)', p))[:420] or n['titulo']
    out['noticias']['dof_' + n['codigo']] = dict(titulo=n['titulo'][:300], fecha=fecha, fuente=f"DOF, {ED.get(n['edicion'], n['edicion'])}", autoridad=titulo_dep(n['dependencia'] or n['poder']),
        tipo='reforma' if es_reforma else 'resolucion' if norm(n['titulo']).startswith(('resolucion', 'reglas')) else 'acuerdo' if norm(n['titulo']).startswith('acuerdo') else 'noticia',
        tema='fiscal' if re.search(r'hacienda|tributaria|impuest|fiscal|aduan', norm(n['dependencia'] + n['titulo'])) else 'seguridad_social' if re.search(r'seguro social|vivienda|retiro', norm(n['dependencia'] + n['titulo'])) else 'laboral' if re.search(r'trabajo|salari', norm(n['dependencia'] + n['titulo'])) else 'fiscal',
        relevancia=1 if es_reforma else 2, resumen=resumen, relevancia_profesional='Texto publicado en el Diario Oficial; la aplicación lo incorporó en automático. Verifique la entrada en vigor en sus transitorios.' if es_reforma else '',
        url=n['url'], disposiciones=', '.join(ABREV.get(k) or k.upper().replace('_', ' ') for k in ks), oficial=True, destacada=es_reforma, origen='dof_automatico')
    if es_reforma and ks and ps:
        did = 'dof_' + n['codigo']; pars, secs = procesar(['\n'.join(ps)])
        cuerpo = json.dumps(dict(id=did, fecha=fecha, titulo=n['titulo'], pdf=n['url'], leyes=ks, p=pars, s=secs), ensure_ascii=False, separators=(',', ':'))
        out['leyes'].append({'tipo': 'decreto', 'id': did, 'b64': base64.b64encode(gzip.compress(cuerpo.encode(), 9)).decode()})
        out['decretos'].append(dict(id=did, leyes=ks, titulo=n['titulo'], fecha=fecha))
        for k in ks: out['reformas'].setdefault(k, []).append(dict(n='DOF', tipo='reforma', t=n['titulo'], f=fecha, u=n['url'], d=did, esc=False))
json.dump(out, open(f'{K}/tmp/dof_{fecha.replace("-", "")}.json', 'w'), ensure_ascii=False)
print(fecha, len(out['noticias']), 'noticias,', len(out['indicadores']), 'indicadores,', len(out['decretos']), 'decretos de reforma:', [d['leyes'] for d in out['decretos']])
