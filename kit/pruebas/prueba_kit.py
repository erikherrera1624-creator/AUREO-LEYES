"""Pruebas del kit con datos simulados (no toca el repositorio: trabaja en una copia temporal).
uso: python3 kit/pruebas/prueba_kit.py"""
import json, os, shutil, subprocess, sys, tempfile, glob
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(prefix='aureo_prueba_'); shutil.copytree(RAIZ, T + '/r', ignore=shutil.ignore_patterns('.git', 'tmp', '__pycache__', 'pruebas'))
R = T + '/r'; K = R + '/kit'; os.makedirs(K + '/tmp/cab', exist_ok=True); os.makedirs(K + '/tmp/textos', exist_ok=True)
for d in ('huellas', 'pendientes'): shutil.rmtree(K + '/' + d, ignore_errors=True)
for f in ('registro.json', 'anuales.json'):
    if os.path.exists(K + '/' + f): os.remove(K + '/' + f)
ok, mal = 0, 0
def prueba(nombre, cond, extra=''):
    global ok, mal
    if cond: ok += 1; print('  ✓', nombre)
    else: mal += 1; print('  ✗', nombre, extra)
def corre(*a, env=None):
    r = subprocess.run([sys.executable, *a], cwd=R, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    if r.returncode: print(r.stdout[-2000:], r.stderr[-3000:]); raise SystemExit('falló ' + ' '.join(a))
    return r.stdout
J = lambda p: json.load(open(K + '/' + p))
def F(): return {x['clave']: x for x in J('fuentes.json')['fuentes']}
def ley(nombre, n, cab='', extra=None, cambia=None):
    """Páginas simuladas: n artículos; cambia = {numero: texto nuevo}."""
    arts = [f'Artículo {i}.- Disposición {i} del ordenamiento sobre contribuciones y obligaciones número {i}.' for i in range(1, n + 1)]
    for k, v in (cambia or {}).items(): arts[k - 1] = f'Artículo {k}.- {v}'
    arts += extra or []
    pags = [nombre.upper() + '\n' + cab + '\n' + '\n'.join(arts[:40])] + ['\n'.join(arts[i:i + 40]) for i in range(40, len(arts), 40)]
    return pags
def textos(d):
    shutil.rmtree(K + '/tmp/textos', ignore_errors=True); os.makedirs(K + '/tmp/textos')
    for k, p in d.items(): json.dump(p, open(f'{K}/tmp/textos/{k}.json', 'w'))
def limpiar_tmp():
    for p in glob.glob(K + '/tmp/cab/*') + glob.glob(K + '/tmp/dof_*.json'): os.remove(p)
    if os.path.exists(K + '/tmp/cambios.json'): os.remove(K + '/tmp/cambios.json')

f0 = F()
print('1. Plan de revisión')
reg = {'fuentes': {'est_hgo_cf': {'pendiente': True, 'resultado': 'falla'}}, 'eventos': []}; json.dump(reg, open(K + '/registro.json', 'w'))
corre('kit/plan.py', '202610230810', 'federal'); plan = J('tmp/plan.json')
hgo = [p for p in plan if 'congreso-hidalgo' in p['abrir']]
prueba('la corrida matutina incluye la fuente estatal que quedó pendiente (Hidalgo, Código Fiscal)', hgo and hgo[0]['claves'] == ['est_hgo_cf'], str(hgo[:1]))
prueba('cada sitio declara el dominio esperado (detecta redirecciones)', all('window.ESPERADO' in p['js'] for p in plan if p['tipo'] == 'encabezados'))
dip = [p for p in plan if p['tipo'] == 'encabezados' and 'diputados' in p['abrir']]
prueba('se sondea la Ley de Ingresos de la Federación 2027', dip and 'LIF_2027.pdf' in dip[0]['js'], '')
prueba('de mañana solo se lee el listado federal', [p['abrir'] for p in plan if p['tipo'] == 'listado'] == ['https://www.diputados.gob.mx/LeyesBiblio/index.htm'])
corre('kit/plan.py', '202610232240', 'todo'); plan = J('tmp/plan.json')
prueba('de noche se leen los listados de Hidalgo, Chihuahua y Jalisco', len([p for p in plan if p['tipo'] == 'listado']) == 4, str([p['abrir'] for p in plan if p['tipo'] == 'listado']))
prueba('Hidalgo se revisa desde el dominio anterior (no redirige)', any(p['abrir'].startswith('https://www.congreso-hidalgo.gob.mx/biblioteca_legislativa') for p in plan))
prueba('Chihuahua se revisa desde congresochihuahua2', any(p['abrir'] == 'https://www.congresochihuahua2.gob.mx/favicon.ico' for p in plan))

print('2. Revisión de encabezados, listados y sondeos')
C = lambda k: dict(f0[k]['control'], s=200, ok=1, t='2026-10-23T22:40', u=f0[k]['url'])
cab = {'est_hgo_cf': C('est_hgo_cf'),
       'est_hgo_lh': {'s': 0, 'ok': 0, 'err': 'la página de entrada redirigió a https://congresohidalgo.gob.mx; Failed to fetch', 'u': f0['est_hgo_lh']['url']},
       'est_hgo_li': {'s': 200, 'ok': 0, 'err': 'página HTML en lugar del documento (página de error o cambio de dirección)', 'u': f0['est_hgo_li']['url']},
       'est_chih_cpe': dict(C('est_chih_cpe'), lm='Wed, 21 Oct 2026 16:38:13 GMT'),
       'est_chih_cf': dict(C('est_chih_cf'), f='https://www.congresochihuahua.gob.mx/biblioteca/codigos/archivosCodigos/65.pdf'),
       'est_chih_lh': dict(C('est_chih_lh'), f='https://pdfs-gratis.example.com/1442.pdf'),
       'est_jal_cf': C('est_jal_cf'), 'est_jal_li': C('est_jal_li'), 'est_jal_lh': C('est_jal_lh')}
plan_claves = [{'claves': list(cab) + ['est_chih_cc']}]
json.dump(plan_claves, open(K + '/tmp/plan.json', 'w'))
json.dump({'cab': cab, 'son': {}, 'sitio': {}}, open(K + '/tmp/cab/CABPRUEBA_1.json', 'w'))
json.dump({'cab': {}, 'son': {'lif_2026@2027@0': {'s': 200, 'ok': 1, 'u': 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LIF_2027.pdf', 'f': ''},
                              'est_cdmx_li@2027@0': {'s': 404, 'ok': 0, 'err': 'no publicado (HTTP 404)'}}, 'sitio': {}}, open(K + '/tmp/cab/CABPRUEBA_2.json', 'w'))
JAL = 'https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/legislacion/'
filas = [['jal_listado', '', JAL + 'Códigos/Documentos_PDF-Códigos/Código Fiscal del Estado de Jalisco-220726.pdf', 'Código Fiscal del Estado de Jalisco 14/05/2026 30147'],
         ['jal_listado', '', JAL + 'Leyes/Documentos_PDF-Leyes/Ley de Hacienda del Estado de Jalisco -151026.pdf', 'Ley de Hacienda del Estado de Jalisco 10/10/2026 30300'],
         ['jal_listado', '', JAL + 'Ingresos/Documentos_PDF-Ingresos/Ley de Ingresos del Estado de Jalisco-240926.pdf', 'Ley de Ingresos del Estado de Jalisco 09/09/2026 30223'],
         ['jal_listado', '', JAL + 'Ingresos/Ley de Ingresos del Estado de Jalisco-240926.doc', 'Ley de Ingresos del Estado de Jalisco 09/09/2026 30223'],
         ['hgo_leyes', '', 'https://www.congreso-hidalgo.gob.mx/biblioteca_legislativa/leyes_cintillo/Codigo%20Fiscal%20del%20Estado%20de%20Hidalgo.pdf', ''],
         ['hgo_leyes', '', 'https://www.congreso-hidalgo.gob.mx/biblioteca_legislativa/leyes_cintillo/Ley de Ingresos del Estado Libre y Soberano de Hidalgo para el Ejercicio Fiscal 2027.pdf', '']]
json.dump({'filas': filas, 'err': []}, open(K + '/tmp/cab/LSTPRUEBA_1.json', 'w'))
salida = corre('kit/revisar.py', '202610232240'); ch = J('tmp/cambios.json'); rg = J('registro.json')['fuentes']; f1 = F()
prueba('sin cambio: Hidalgo, Código Fiscal', rg['est_hgo_cf']['resultado'] == 'sin_cambio' and not rg['est_hgo_cf']['pendiente'])
prueba('falla por redirección registrada y pendiente; control intacto', rg['est_hgo_lh']['resultado'] == 'falla' and rg['est_hgo_lh']['pendiente'] and 'redirigió' in rg['est_hgo_lh']['motivo'] and f1['est_hgo_lh']['control'] == f0['est_hgo_lh']['control'])
prueba('página de error en lugar del PDF = falla, no actualización', rg['est_hgo_li']['resultado'] == 'falla' and f1['est_hgo_li']['control'] == f0['est_hgo_li']['control'])
prueba('sitio que no respondió nada = falla pendiente (Chihuahua, Código Civil)', rg['est_chih_cc']['resultado'] == 'falla' and rg['est_chih_cc']['pendiente'])
prueba('cambio por encabezado (Constitución de Chihuahua, 21/10/2026)', any(c['clave'] == 'est_chih_cpe' and c['motivo'] == 'encabezado' for c in ch['cambios']))
prueba('cambio de dominio a sitio oficial aceptado y registrado', f1['est_chih_cf']['url'].startswith('https://www.congresochihuahua.gob.mx/') and f1['est_chih_cf']['urls_anteriores'] == [f0['est_chih_cf']['url']])
prueba('redirección a dominio no oficial rechazada', rg['est_chih_lh']['resultado'] == 'falla' and f1['est_chih_lh']['url'] == f0['est_chih_lh']['url'])
prueba('archivo renombrado detectado (Jalisco, Ley de Hacienda -151026)', any(c['clave'] == 'est_jal_lh' and c['motivo'] == 'renombrado' and c['url_nueva'].endswith('-151026.pdf') for c in ch['cambios']))
prueba('sin falsos renombres (Jalisco CF y LI siguen en su dirección)', not any(c['clave'] in ('est_jal_cf', 'est_jal_li') for c in ch['cambios']))
an = {n['clave']: n for n in ch['anuales_nuevos']}
prueba('LIF 2027 detectada por sondeo', 'lif_2027' in an and an['lif_2027']['via'] == 'sondeo')
prueba('Ley de Ingresos de Hidalgo 2027 detectada en el listado oficial', 'est_hgo_li_2027' in an and an['est_hgo_li_2027']['via'] == 'listado hgo_leyes', str(an.keys()))
A = J('anuales.json')
prueba('ley de ingresos no publicada queda pendiente de publicación (CDMX)', A.get('est_cdmx_li', {}).get('estado') == 'pendiente_publicacion', str(A.get('est_cdmx_li')))
ext = J('tmp/extraer.json')
prueba('Hidalgo se lee desde la página que no redirige', all(not e['abrir'].startswith('https://www.congreso-hidalgo.gob.mx/') or 'leyes_cintillo' in e['abrir'] for e in ext))
prueba('validación gradual programada (máx. 4)', 0 < len(ch['validar']) <= 4, str(ch['validar']))

print('3. Clasificación y publicación')
x = f1
txt = {
  # reforma: la fecha de última reforma avanza
  'est_chih_cpe': ley('Constitución Política del Estado de Chihuahua', 230, cab='Última reforma P.O.E. 21 de octubre de 2026'),
  # renombrado con el mismo texto de fondo pero sin fechas: no hay evidencia → pendiente de validación
  'est_jal_lh': ley('Ley de Hacienda del Estado de Jalisco', 100),
  'lif_2027': ley('Ley de Ingresos de la Federación para el Ejercicio Fiscal de 2027', 30),
  'est_hgo_li_2027': ley('Ley de Ingresos del Estado de Hidalgo para el Ejercicio Fiscal 2026', 20),   # el texto dice 2026: no se publica
}
for k in ch['validar']: txt[k] = ley(x[k]['nombre'], max(10, x[k]['unidades']))
txt[ch['validar'][0]] = ley('Ley sobre otro asunto distinto', max(10, x[ch['validar'][0]]['unidades']))          # documento diferente
textos(txt)
salida = corre('kit/construir.py'); f2 = F(); I = json.load(open(R + '/indice.json')); rg = J('registro.json')['fuentes']
paq = json.load(open(R + '/' + I['paquetes'][-1]['archivo'])) if I['paquetes'][-1]['fecha'] == '2026-10-23' or True else {}
pub = {l['clave']: l for l in paq.get('leyes', []) if 'version' in l}
prueba('reforma publicada (Constitución de Chihuahua)', 'est_chih_cpe' in pub and pub['est_chih_cpe']['version']['tipo_cambio'] == 'reforma', salida[-600:])
prueba('control actualizado solo tras leer el texto', f2['est_chih_cpe']['control']['lm'] == 'Wed, 21 Oct 2026 16:38:13 GMT')
prueba('renombrado sin evidencia: NO se sobrescribe, queda pendiente', 'est_jal_lh' not in pub and os.path.exists(K + '/pendientes/est_jal_lh.json') and f2['est_jal_lh']['url'] == f0['est_jal_lh']['url'] and f2['est_jal_lh'].get('url_en_revision', '').endswith('-151026.pdf'))
prueba('LIF 2027 publicada como ley nueva, vigente desde 2027-01-01, con ficha de catálogo', 'lif_2027' in pub and pub['lif_2027']['version']['desde'] == '2027-01-01' and any(c['clave'] == 'lif_2027' for c in paq.get('catalogo', [])) and 'lif_2027' in f2)
prueba('la LIF 2026 se conserva', 'lif_2026' in f2 and f2['lif_2026']['version'] == f0['lif_2026']['version'])
prueba('ley anual cuyo texto no confirma el ejercicio: no se publica', 'est_hgo_li_2027' not in pub and 'est_hgo_li_2027' not in f2)
v0 = ch['validar'][0]
prueba('documento diferente apartado sin tocar la fuente', os.path.exists(f'{K}/pendientes/{v0}.json') and J(f'pendientes/{v0}.json')['clase'] == 'documento_diferente' and f2[v0].get('version') == f0[v0].get('version'))
otros = ch['validar'][1:]
prueba('validación gradual: huellas por disposición guardadas', all(os.path.exists(f'{K}/huellas/{k}.json') or os.path.exists(f'{K}/pendientes/{k}.json') for k in otros))
prueba('indice.json trae el resumen de la revisión', 'revision' in I and v0 in I['revision']['pendientes_de_validacion'] and 'est_hgo_lh' in I['revision']['fuentes_con_falla'])

print('4. Validación manual')
corre('kit/validar.py', 'descartar', v0); f3 = F()
prueba('descartar: se queda la versión actual y sale de pendientes', not os.path.exists(f'{K}/pendientes/{v0}.json') and f3[v0].get('version') == f0[v0].get('version'))
corre('kit/validar.py', 'aprobar', 'est_jal_lh'); f3 = F(); I = json.load(open(R + '/indice.json'))
prueba('aprobar: nueva versión publicada, dirección nueva, la anterior queda en el historial', f3['est_jal_lh']['url'].endswith('-151026.pdf') and f3['est_jal_lh']['urls_anteriores'] and I['paquetes'][-1]['leyes'] == ['est_jal_lh'])

print('5. Cambios posteriores con huellas por disposición (Constitución de Chihuahua)')
base_txt = txt['est_chih_cpe']
def ronda(pags, nuevo_lm):
    limpiar_tmp(); json.dump([{'claves': ['est_chih_cpe']}], open(K + '/tmp/plan.json', 'w'))
    c = dict(F()['est_chih_cpe']['control'], s=200, ok=1, lm=nuevo_lm, u=F()['est_chih_cpe']['url'])
    json.dump({'cab': {'est_chih_cpe': c}, 'son': {}, 'sitio': {}}, open(K + '/tmp/cab/CABR.json', 'w'))
    corre('kit/revisar.py', 'X', env={'AUREO_VALIDAR': '0'}); textos({'est_chih_cpe': pags}); s = corre('kit/construir.py')
    return J('registro.json')['fuentes']['est_chih_cpe'], s
r, s = ronda([p.replace('.', ' .') for p in base_txt], 'Thu, 22 Oct 2026 10:00:00 GMT')
prueba('solo puntuación/espacios → formato, no se publica', r['resultado'] == 'formato', str(r) + s[-400:])
r, s = ronda(ley('Constitución Política del Estado de Chihuahua', 230, cab='Última reforma P.O.E. 21 de octubre de 2026', cambia={7: 'Disposición siete corregida en su redacción sin cambiar su sentido.'}), 'Fri, 23 Oct 2026 10:00:00 GMT')
prueba('un artículo con cambio de redacción y sin fecha nueva → corrección editorial publicada', r['resultado'] == 'publicada' and 'correccion_editorial' in r['motivo'], str(r))
r, s = ronda(ley('Constitución Política del Estado de Chihuahua', 230, cab='Última reforma P.O.E. 21 de octubre de 2026', cambia={7: 'Disposición siete corregida en su redacción sin cambiar su sentido.'},
                 extra=['Artículo 231.- Artículo nuevo. Adicionado mediante Decreto publicado en el P.O.E. del 23 de octubre de 2026.']), 'Sat, 24 Oct 2026 10:00:00 GMT')
prueba('artículo agregado → reforma publicada', r['resultado'] == 'publicada' and r['motivo'].startswith('reforma'), str(r))
r, s = ronda(ley('Constitución Política del Estado de Chihuahua', 230, cab='Última reforma P.O.E. 21 de octubre de 2026', cambia={i: f'Texto distinto número {i} con otro contenido.' for i in range(10, 20)},
                 extra=['Artículo 231.- Artículo nuevo. Adicionado mediante Decreto publicado en el P.O.E. del 23 de octubre de 2026.']), 'Sun, 25 Oct 2026 10:00:00 GMT')
prueba('diez artículos cambian sin fecha nueva → pendiente de validación (no se sobrescribe)', r['resultado'] == 'pendiente_validacion', str(r))
r2 = J('registro.json')['fuentes']['est_chih_cpe']
limpiar_tmp(); json.dump([{'claves': ['est_chih_cpe']}], open(K + '/tmp/plan.json', 'w'))
c = dict(F()['est_chih_cpe']['control_en_revision'], s=200, ok=1, u=F()['est_chih_cpe']['url'])
json.dump({'cab': {'est_chih_cpe': c}, 'son': {}, 'sitio': {}}, open(K + '/tmp/cab/CABR.json', 'w')); corre('kit/revisar.py', 'X', env={'AUREO_VALIDAR': '0'})
prueba('el mismo archivo en espera no se vuelve a leer en cada corrida', not J('tmp/cambios.json')['cambios'])

print('6. Jalisco publica la Ley de Ingresos 2027 con el mismo nombre de archivo y otra fecha')
limpiar_tmp(); json.dump([{'claves': []}], open(K + '/tmp/plan.json', 'w'))
filas = [['jal_listado', '', JAL + 'Ingresos/Documentos_PDF-Ingresos/Ley de Ingresos del Estado de Jalisco-201226.pdf', 'Ley de Ingresos del Estado de Jalisco 19/12/2026 31000']]
json.dump({'filas': filas, 'err': []}, open(K + '/tmp/cab/LSTJ.json', 'w')); corre('kit/revisar.py', 'X', env={'AUREO_VALIDAR': '0'})
prueba('se detecta como renombrado', any(c['clave'] == 'est_jal_li' and c['motivo'] == 'renombrado' for c in J('tmp/cambios.json')['cambios']))
textos({'est_jal_li': ley('Ley de Ingresos del Estado de Jalisco para el Ejercicio Fiscal 2027', 60)}); s = corre('kit/construir.py'); f4 = F()
prueba('el texto dice 2027 → ley nueva est_jal_li_2027; la de 2026 se conserva y deja de revisarse', 'est_jal_li_2027' in f4 and f4['est_jal_li'].get('archivado') and f4['est_jal_li']['url'] == f0['est_jal_li']['url'], s[-500:])

print('7. DOF: días pendientes sin tope')
I = json.load(open(R + '/indice.json')); I['dof_revisado'] = '2026-10-01'; json.dump(I, open(R + '/indice.json', 'w'))
d = corre('kit/dof.py', 'pendientes').split()
prueba('recupera los 22 días desde la interrupción', len(d) == 22 and d[0] == '2026-10-02', str(d[:3]))
print(f'\n{ok} correctas, {mal} con error   (copia de prueba: {T})')
sys.exit(1 if mal else 0)
