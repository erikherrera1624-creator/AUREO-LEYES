"""Convierte textos_est/*.bin (doc, docx, rtf, html) a páginas de texto .json con LibreOffice."""
import os, sys, json, subprocess, tempfile, shutil, glob
D = '/tmp/claude-0/-home-claude/17669c10-85a0-53f4-b02f-ea832f8cfbd4/scratchpad/textos_est'
for b in sorted(glob.glob(D + '/*.bin')):
    nombre = os.path.basename(b)[:-4]
    if os.path.exists(f'{D}/{nombre}.json') and os.path.getmtime(f'{D}/{nombre}.json') > os.path.getmtime(b): continue
    datos = open(b, 'rb').read(); cab = datos[:8]; k = datos.find(b'%PDF')
    if 0 <= k < 20000:   # PDF (a veces precedido de una página HTML): pdftotext o, si está escaneado, OCR
        import tempfile as tf
        d = tf.mkdtemp(); open(d + '/x.pdf', 'wb').write(datos[k:]); subprocess.run(['pdftotext', d + '/x.pdf', d + '/x.txt'])
        pags = open(d + '/x.txt', encoding='utf-8', errors='replace').read().split('\f')
        if sum(map(len, pags)) < 300 * len(pags):
            subprocess.run(['python3', '/home/claude/captura/ocr.py', d + '/x.pdf', f'{D}/{nombre}.json']); print(nombre, 'OCR'); continue
        json.dump(pags, open(f'{D}/{nombre}.json', 'w')); print(nombre, 'pdf', sum(map(len, pags)), 'car', len(pags), 'pág'); continue
    ext = '.doc' if cab.startswith(b'\xd0\xcf\x11\xe0') else '.docx' if cab.startswith(b'PK') else '.rtf' if cab.startswith(b'{\\rtf') else '.html'
    tmp = tempfile.mkdtemp(); src = f'{tmp}/x{ext}'; shutil.copy(b, src)
    subprocess.run(['soffice', '--headless', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', tmp, src], capture_output=True, timeout=600)
    txt = open(f'{tmp}/x.txt', encoding='utf-8', errors='replace').read() if os.path.exists(f'{tmp}/x.txt') else ''
    shutil.rmtree(tmp)
    paras = [l.rstrip() for l in txt.replace('\r', '').split('\n')]
    pags, cur = [], ''
    for l in paras:
        if len(cur) > 3500: pags.append(cur); cur = ''
        cur += l + '\n'
    pags.append(cur)
    json.dump(pags, open(f'{D}/{nombre}.json', 'w')); print(nombre, ext, len(txt), 'car', len(pags), 'pág |', txt[:120].replace('\n', ' / '))
