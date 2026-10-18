"""Funciones compartidas: limpieza de textos estatales, fechas de reforma y última reforma (las mismas con que se armó la aplicación)."""
import re, unicodedata
MAC = 'Û·Ì˙ÈÒÕ∫∞¡…⁄‡ÎÏ¯ËÁ'
def limpiar(t):
    if sum(t.count(c) for c in 'ÛÌ·') > 20:   # texto MacRoman leído como Latin-1
        t = ''.join(c.encode('mac_roman').decode('latin-1') if c in MAC else c for c in t)
    t = re.sub(r'[-]', lambda m: chr(ord(m.group()) - 0xf000), t)   # fuentes Symbol
    t = t.replace('­', '').replace('﻿', '')
    t = re.sub('[‐‑‒–—―−]', '-', t)
    t = re.sub(r'\b(?:[A-ZÁÉÍÓÚÑ] ){3,}[A-ZÁÉÍÓÚÑ]\b', lambda m: m.group().replace(' ', ''), t)   # «T I T U L O» → «TITULO»
    # Morelos marca con asterisco los artículos reformados («Artículo *7 BIS-1.-»)
    t = re.sub(r'(?m)^(\s*(?:Art[ií]culo|ART[IÍ]CULO)\s+)\*\s*', r'\1', t)
    t = re.sub(r'(?m)^(\s*(?:Art[ií]culo|ART[IÍ]CULO)\s+\d+\s*(?:BIS|Bis|bis|TER|Ter|QUATER|Quater))-(\d+)', lambda m: m.group(1) + ' ' + str(int(m.group(2))), t)
    # letras triplicadas por negritas simuladas: «LLLEEEYYY» → «LEY»
    t = re.sub(r'\b(?:([A-ZÁÉÍÓÚÑÜ0-9])\1\1)+\b', lambda m: m.group()[::3], t)
    t = re.sub(r'\b(?:([A-ZÁÉÍÓÚÑÜ])\1){3,}\b', lambda m: m.group()[::2], t)   # «CCOODDIIGGOO» → «CODIGO»
    return unicodedata.normalize('NFC', t)
MES = dict(ene=1, feb=2, mar=3, abr=4, may=5, jun=6, jul=7, ago=8, sep=9, set=9, oct=10, nov=11, dic=12)
RM = r'(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)[a-zé]*\.?'
def iso(a, m, d):
    a, m, d = int(a), int(m), int(d)
    return f'{a:04d}-{m:02d}-{d:02d}' if 1917 <= a <= 2026 and 1 <= m <= 12 and 1 <= d <= 31 else None
def fechas_en(x):
    out = []
    s = x.lower()
    for m in re.finditer(r'(\d{1,2})\s*(?:º|°|o\.)?\s*(?:de\s+)?' + RM + r'\s*(?:de|del)?\s*(\d{4})', s): out.append(iso(m.group(3), MES[m.group(2)[:3]], m.group(1)))
    for m in re.finditer(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', s): out.append(iso(m.group(3), m.group(2), m.group(1)))
    for m in re.finditer(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s): out.append(iso(m.group(1), m.group(2), m.group(3)))
    for m in re.finditer(r'(\d{1,2})-' + RM + r'-(\d{4})', s): out.append(iso(m.group(3), MES[m.group(2)[:3]], m.group(1)))
    for m in re.finditer(RM + r'\s+(\d{1,2})\s+de\s+(\d{4})', s): out.append(iso(m.group(3), MES[m.group(1)[:3]], m.group(2)))
    return [f for f in out if f]
RE_NOTA = re.compile(r'(reformad|adicionad|derogad|modificad|reforma|adiciona|deroga|fe de erratas)', re.I)
RE_PUB = re.compile(r'(P\.?\s?O\.?|POE|POGG|BOGE|B\.?O\.?|G\.?O\.?|Gaceta|Peri[oó]dico|Bolet[ií]n|Decreto|DEC\.|Dto\.)', re.I)
def fechas_unidad(texto):
    fs = []
    for linea in re.split(r'\n|(?<=\))\s+(?=\()', texto):
        if len(linea) > 400 or not RE_NOTA.search(linea) or not RE_PUB.search(linea) or re.search(r'[ÚU]ltima\s+reforma', linea, re.I): continue
        fs += fechas_en(linea)
    return ','.join(sorted(set(fs)))
def ultima_reforma(pags, reg):
    cab = '\n'.join(pags[:2])[:6000]
    for m in re.finditer(r'[ÚU]LTIMAS?\s+(?:REFORMAS?|ACTUALIZACI[ÓO]N|MODIFICACI[ÓO]N(?:ES)?)[^\n]*(?:\n[^\n]*){0,2}', cab, re.I):
        fs = fechas_en(m.group())
        if fs: return max(fs), re.sub(r'\s+', ' ', m.group()).strip()[:160]
    fs = fechas_en(reg.get('ultima') or '')
    return (fs[0], '') if fs else (None, '')

def limpiar_estatal(arch, pags):
    pags = [limpiar(p) for p in pags]
    if arch.startswith(('VER_', 'ZAC_')):   # Veracruz y Zacatecas ponen «ARTICULO 127» solo en su renglón, sin punto ni guion
        pags = [re.sub(r'(?m)^(\s*(?:ART[IÍ]CULO|Art[ií]culo)\s+\d+(?:\s*(?:BIS|TER|QUATER|Bis|Ter|Quater|Quinquies|Sexies)(?:\s*\d+)?)?)\s*$', r'\1.-', p) for p in pags]
    if arch == 'BCS_cpe':   # la Constitución de BCS numera sus artículos sin la palabra «Artículo»
        pags = [re.sub(r'(?m)^(\s*)(\d{1,3}\s*(?:o\.|°|º)?(?:\s+(?:BIS|Bis))?)\s*\.?-\s*(?=[A-ZÁÉÍÓÚÑ¿“"])', r'\1Artículo \2.- ', p) for p in pags]
    return pags
