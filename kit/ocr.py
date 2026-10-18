"""OCR de PDF escaneados: ocr.py archivo.bin salida.json"""
import sys, os, subprocess, tempfile, glob, json, shutil
src, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp(); shutil.copy(src, tmp + '/x.pdf')
subprocess.run(['pdftoppm', '-r', '200', '-gray', tmp + '/x.pdf', tmp + '/p'], check=True)
env = dict(os.environ, TESSDATA_PREFIX='/home/claude/tessdata', OMP_THREAD_LIMIT='1')
imgs = sorted(glob.glob(tmp + '/p-*.pgm'))
from concurrent.futures import ThreadPoolExecutor
def uno(im): return subprocess.run(['tesseract', im, '-', '-l', 'spa', '--psm', '6'], capture_output=True, text=True, env=env).stdout
with ThreadPoolExecutor(8) as ex: pags = list(ex.map(uno, imgs))
shutil.rmtree(tmp); json.dump(pags, open(out, 'w')); print(out, len(pags), 'pág', sum(map(len, pags)), 'car')
