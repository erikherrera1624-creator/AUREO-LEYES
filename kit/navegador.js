/* Áureo Leyes — funciones para el navegador integrado (se pegan con javascript_tool en una pestaña del sitio oficial).
   Ninguna guarda archivos en la computadora: leen el texto y lo regresan al espacio de trabajo en trozos.
   Uso: pegar este archivo completo una vez por pestaña (después de cada navegación) y luego llamar a las funciones. */
// pdf.js se carga solo cuando hace falta leer un PDF (funciona también en páginas XML, donde no se ejecutan etiquetas <script>)
window.cargarPdfjs = async () => { if (window.pdfjsLib) return; const base = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/";
  try { const code = await (await fetch(base + "pdf.min.js")).text(); (new Function(code)).call(window); }
  catch (e) { // el sitio no permite conexiones a otros dominios: se intenta con etiqueta <script>
    await new Promise((ok, mal) => { const s = document.createElementNS("http://www.w3.org/1999/xhtml", "script"); s.src = base + "pdf.min.js"; s.onload = ok; s.onerror = () => mal(new Error("no carga pdf.js")); (document.head || document.documentElement).appendChild(s); setTimeout(() => mal(new Error("pdf.js tardó demasiado")), 20000); }); }
  pdfjsLib.GlobalWorkerOptions.workerSrc = base + "pdf.worker.min.js"; };
// algunos sitios (el DOF usa Prototype.js) alteran JSON.stringify de los arreglos
if (Array.prototype.toJSON) delete Array.prototype.toJSON;
window.__B = {}; window.__R = null; window.__P = null;
window.b64 = u8 => { let b = ""; for (let k = 0; k < u8.length; k += 32768) b += String.fromCharCode.apply(null, u8.subarray(k, k + 32768)); return btoa(b); };
window.gz = async x => new Uint8Array(await new Response(new Blob([x]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
window.limpio = t => (t || "").replace(/\s+/g, " ").trim();
// ---- red robusta: tiempo de espera, reintentos escalonados (0 s, 2 s, 6 s, 12 s) y validación del contenido ----
window.pedir = async (url, opts, intentos) => { opts = opts || {}; intentos = intentos || 3; const pausas = [0, 2000, 6000, 12000]; let error = null;
  for (let i = 0; i < intentos; i++) { if (pausas[i]) await new Promise(r => setTimeout(r, pausas[i]));
    const c = new AbortController(); const reloj = setTimeout(() => c.abort(), opts.ms || 30000);
    try { const r = await fetch(url, Object.assign({}, opts, { signal: c.signal, redirect: "follow", cache: "no-store" })); clearTimeout(reloj);
      if (r.status === 429 || r.status >= 500) { error = new Error("HTTP " + r.status); continue; }
      r.intentos = i + 1; return r; }
    catch (e) { clearTimeout(reloj); error = e.name === "AbortError" ? new Error("tiempo de espera agotado") : e; } }
  throw error; };
// '' si el contenido es válido; si no, el motivo (página de error, HTML en lugar de PDF, documento incompleto…)
window.validar = (modo, b, ct) => { ct = (ct || "").toLowerCase(); if (!b || !b.length) return "respuesta vacía";
  const ini = new TextDecoder("latin1").decode(b.subarray(0, 20000)); const k = ini.indexOf("%PDF");
  if (modo === "html") { if (b.length < 800) return "página demasiado corta"; const t = ((ini.match(/<title[^>]*>([^<]*)/i) || [])[1] || "").trim();
    return /\b(404|403|500|not found|no encontrad[ao]|forbidden|prohibido)\b/i.test(t) ? "página de error: " + t.slice(0, 60) : ""; }
  // documentos (pdf o crudo): PDF completo, o Word/RTF (algunos congresos publican .doc); una página HTML es un error
  if (k >= 0) { if (b.length < 2000) return "PDF incompleto (" + b.length + " bytes)";
    const fin = new TextDecoder("latin1").decode(b.subarray(Math.max(0, b.length - 4096)));
    return fin.includes("%%EOF") || fin.includes("startxref") ? "" : "PDF incompleto (sin cierre)"; }
  const doc = (b[0] === 0xd0 && b[1] === 0xcf && b[2] === 0x11 && b[3] === 0xe0) || (b[0] === 0x50 && b[1] === 0x4b) || ini.startsWith("{\\rtf");
  if (doc) return b.length < 2000 ? "documento incompleto (" + b.length + " bytes)" : "";
  if (/<html|<!doctype|<body|<head/i.test(ini.slice(0, 3000)) || ct.includes("html")) return "página HTML en lugar del documento (página de error o cambio de dirección)";
  return "formato de archivo no reconocido"; };
const _modoVal = m => m === "html" ? "html" : "pdf";
window.mismoHost = (a, b) => { try { return new URL(a).host.replace(/^www\./, "") === new URL(b).host.replace(/^www\./, ""); } catch (e) { return false; } };
window.urlFinal = (pedida, r) => { try { return r.url && r.url !== new URL(pedida).href ? r.url : ""; } catch (e) { return r.url || ""; } };
// texto de un PDF por páginas (misma lectura que usa la aplicación)
window.paginasPdf = async buf => { await cargarPdfjs(); const pdf = await pdfjsLib.getDocument({ data: buf, isEvalSupported: false, verbosity: 0 }).promise; const paginas = [];
  for (let i = 1; i <= pdf.numPages; i++) { const pg = await pdf.getPage(i); const tc = await pg.getTextContent(); let linea = "", lineas = [], yAnt = null;
    for (const it of tc.items) { const y = it.transform ? Math.round(it.transform[5]) : null;
      if (yAnt !== null && y !== null && Math.abs(y - yAnt) > 2 && linea) { lineas.push(linea); linea = ""; }
      if (it.str) linea += it.str; if (it.hasEOL && linea.trim()) { lineas.push(linea); linea = ""; } if (it.str) yAnt = y; }
    if (linea) lineas.push(linea); paginas.push(lineas.map(l => l.replace(/\s+/g, " ").trimEnd()).join("\n")); pg.cleanup(); }
  return paginas; };
// páginas de un documento HTML (Zacatecas publica sus leyes como página web; enc = "iso-8859-1" o "utf-8")
window.paginasHtml = (html, raiz) => { const d = new DOMParser().parseFromString(html, "text/html"); const r = raiz ? (d.querySelector(raiz) || d.body) : d.body;
  r.querySelectorAll("style,script").forEach(e => e.remove());
  const lineas = [...r.querySelectorAll("p,h1,h2,h3,h4,li,td")].filter(e => !e.querySelector("p,li,td")).map(e => limpio(e.textContent)).filter(Boolean);
  const pags = []; for (let i = 0; i < lineas.length; i += 45) pags.push(lineas.slice(i, i + 45).join("\n")); return pags; };
// extrae un documento (pdf | html | crudo) y lo deja listo para mandarse
window.extraer = async (nombre, url, modo, enc) => { const r = await pedir(url, {}, 3); if (!r.ok) throw new Error("HTTP " + r.status); const buf = new Uint8Array(await r.arrayBuffer());
  const mal = validar(_modoVal(modo), buf, r.headers.get("content-type"));
  if (mal) throw new Error(mal + (urlFinal(url, r) ? " | final " + urlFinal(url, r) : ""));
  if (modo === "html") { const pags = paginasHtml(new TextDecoder(enc || "utf-8").decode(buf)); const j = JSON.stringify(pags); window.__B[nombre] = b64(await gz(j)); return nombre + " html " + pags.length + " pág, " + j.length + " car"; }
  if (buf[0] !== 0x25 || buf[1] !== 0x50) { window.__B["RAW_" + nombre] = b64(await gz(buf)); return nombre + " NO-PDF " + buf.length; }
  const pags = await paginasPdf(buf); const j = JSON.stringify(pags);
  if (j.length < pags.length * 300) { window.__B["RAW_" + nombre] = b64(await gz(buf)); return nombre + " ESCANEADO " + pags.length + " pág (crudo)"; }
  window.__B[nombre] = b64(await gz(j)); return nombre + " " + pags.length + " pág, " + j.length + " car | " + pags[0].slice(0, 80).replace(/\n/g, " / "); };
// L = [[nombre, url, modo?, enc?], ...]; se ejecuta en segundo plano: después llamar esperar()
window.lote = L => { window.__B = {}; window.__R = null; (async () => { const o = []; for (const [n, u, m, e] of L) { try { o.push(await extraer(n, u, m, e)); } catch (er) { o.push(n + " ERROR " + er.message); } }
  window.__P = JSON.stringify(window.__B); window.__R = o.join("\n") + "\nTOTAL " + window.__P.length + " trozos " + Math.ceil(window.__P.length / 300000); })(); return "trabajando"; };
window.esperar = async () => { for (let k = 0; k < 30 && !window.__R; k++) await new Promise(r => setTimeout(r, 1000)); return window.__R || ("trabajando: " + Object.keys(window.__B).join(",")); };
// cualquier objeto → texto para el espacio de trabajo (se reúne con reunir.py ETIQUETA)
window.preparar = obj => { window.__P = typeof obj === "string" ? obj : JSON.stringify(obj); return "TOTAL " + window.__P.length + " trozos " + Math.ceil(window.__P.length / 300000); };
window.paq = (e, i) => { const n = Math.ceil(window.__P.length / 300000); const s = window.__P.slice(i * 300000, (i + 1) * 300000); return "<<" + e + "|" + i + "|" + n + ">>" + s + "<<FIN>>" + " ".repeat(Math.max(0, 150000 - s.length)); };
// encabezados de control: fecha de modificación, tamaño y etiqueta; si el sitio no da ninguno (o responde algo dudoso), huella del contenido.
// Cada fuente regresa también: u (dirección pedida), f (dirección final si hubo redirección), ok (1 = respuesta válida), err (motivo), n (intentos), v (encabezado|contenido)
window.cabeceras = async L => { const o = {}; let k = 0; const ahora = new Date().toISOString();
  const uno = async ([clave, url, modo, enc]) => { const reg = { u: url, t: ahora };
    try { let r = null; try { r = await pedir(url, { method: "HEAD", ms: 20000 }, 2); } catch (e) { r = null; }
      let lm = r ? r.headers.get("last-modified") || "" : "", et = r ? r.headers.get("etag") || "" : "", cl = r ? r.headers.get("content-length") || "" : "", ct = r ? r.headers.get("content-type") || "" : "";
      let h = "", motivo = "", v = "encabezado";
      if (!r || !r.ok || (!lm && !et) || modo === "html" || (modo !== "html" && /text\/html/i.test(ct))) {
        r = await pedir(url, {}, 3); const b = new Uint8Array(await r.arrayBuffer()); v = "contenido"; ct = r.headers.get("content-type") || ct;
        lm = r.headers.get("last-modified") || lm; et = r.headers.get("etag") || et; cl = String(b.length);
        if (r.ok) motivo = validar(_modoVal(modo), b, ct);
        if (r.ok && !motivo) { let datos = b; if (modo === "html") datos = new TextEncoder().encode(paginasHtml(new TextDecoder(enc || "utf-8").decode(b)).join("\n"));
          h = [...new Uint8Array(await crypto.subtle.digest("SHA-256", datos))].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 24); } }
      Object.assign(reg, { s: r.status, lm, et, cl, h, ct: ct.slice(0, 60), f: urlFinal(url, r), n: r.intentos || 1, v, ok: r.ok && !motivo ? 1 : 0 });
      if (motivo) reg.err = motivo; else if (!r.ok) reg.err = "HTTP " + r.status;
    } catch (e) { Object.assign(reg, { s: 0, ok: 0, err: String(e && e.message || e).slice(0, 100) + (e instanceof TypeError ? " (sin respuesta legible: el sitio no responde o redirige a otro dominio)" : "") }); }
    o[clave] = reg; };
  const trab = async () => { while (k < L.length) await uno(L[k++]); }; await Promise.all([trab(), trab(), trab(), trab()]); return o; };
// sondeo de direcciones candidatas (p. ej. la ley de ingresos del ejercicio siguiente): L = [[id, url, modo]]
window.sondear = async L => { const o = {};
  for (const [id, url, modo] of L) { const reg = { u: url };
    try { let r = null; try { r = await pedir(url, { method: "HEAD", ms: 15000 }, 1); } catch (e) { r = null; }
      if (r && (r.status === 404 || r.status === 410)) { Object.assign(reg, { s: r.status, ok: 0, err: "no publicado (HTTP " + r.status + ")" }); }
      else { r = await pedir(url, {}, 2); const b = new Uint8Array(await r.arrayBuffer()); const m = r.ok ? validar(_modoVal(modo), b, r.headers.get("content-type")) : "HTTP " + r.status;
        Object.assign(reg, { s: r.status, ok: m ? 0 : 1, cl: b.length, f: urlFinal(url, r), lm: r.headers.get("last-modified") || "" }); if (m) reg.err = m; } }
    catch (e) { Object.assign(reg, { s: 0, ok: 0, err: String(e && e.message || e).slice(0, 100) }); }
    o[id] = reg; }
  return o; };
// sumario del DOF de una fecha (aaaa-mm-dd): ediciones matutina, vespertina y extraordinarias
window.sumarioDOF = async fecha => { const [y, m, d] = fecha.split("-"); const out = [], vistos = new Set();
  for (const ed of ["MAT", "VES", "EXT"]) { let h; try { h = await (await fetch(`/index.php?year=${y}&month=${+m}&day=${+d}&edicion=${ed}`)).text(); } catch (e) { continue; }
    const doc = new DOMParser().parseFromString(h, "text/html"); let seccion = "", poder = "", dep = "";
    for (const td of doc.querySelectorAll("td")) {
      if (td.classList.contains("txt_blanco")) { seccion = limpio(td.textContent); continue; }
      if (td.classList.contains("txt_blanco2")) { poder = limpio(td.textContent); continue; }
      if (td.classList.contains("subtitle_azul")) { dep = limpio(td.textContent); continue; }
      if (td.querySelector("td")) continue; const a = td.querySelector('a[href*="nota_detalle"]'); if (!a) continue;
      const href = a.getAttribute("href"), cod = (href.match(/codigo=(\d+)/) || [])[1], t = limpio(a.textContent); if (!t || !cod || vistos.has(cod)) continue; vistos.add(cod);
      out.push({ edicion: ed, seccion, poder, dependencia: dep, titulo: t, codigo: cod, url: new URL(href, location.origin).href }); } }
  return { fecha, notas: out }; };
// texto completo de notas del DOF (párrafos)
window.textosDOF = async notas => { const o = {}; for (const n of notas) { try { const h = await (await fetch(n.url)).text();
    let i = h.indexOf("DivDetalleNota"); i = i < 0 ? 0 : h.indexOf(">", i) + 1; let j = h.indexOf("table_menu_right", i); if (j < 0) j = h.length;
    let x = h.slice(i, j).replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<\/(p|div|td|tr|li|h\d)>|<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, " ");
    const ta = document.createElement("textarea"); ta.innerHTML = x; x = ta.value;
    const ps = x.split("\n").map(limpio).filter(p => p && !/^En el documento que usted está visualizando/.test(p));
    o[n.codigo] = ps.filter((p, k) => k === 0 || p !== ps[k - 1]); } catch (e) { o[n.codigo] = ["ERROR " + e.message]; } } return o; };
// enlaces de una página (para descubrir compilaciones nuevas de la RMF, por ejemplo)
window.enlaces = async (url, patron) => { const h = await (await fetch(url)).text(); const d = new DOMParser().parseFromString(h, "text/html"); const re = new RegExp(patron, "i");
  return [...d.querySelectorAll("a")].map(a => ({ t: limpio(a.textContent), u: new URL(a.getAttribute("href") || "", url).href })).filter(x => re.test(x.t + " " + x.u)); };
// ---- listados de leyes: todas las ligas a documentos de la página abierta y de otras páginas del mismo sitio ----
window.textoDe = async url => { const r = await fetch(url); const b = new Uint8Array(await r.arrayBuffer()); let cs = ((r.headers.get("content-type") || "").match(/charset=([\w-]+)/i) || [])[1];
  if (!cs) { const ini = new TextDecoder("latin1").decode(b.subarray(0, 3000)); cs = (ini.match(/charset=["']?([\w-]+)/i) || [])[1] || "utf-8"; }
  try { return new TextDecoder(cs).decode(b); } catch (e) { return new TextDecoder("utf-8").decode(b); } };
window.enlacesAqui = async (paginas) => { const res = new Map();
  const tomar = (doc, base) => doc.querySelectorAll("a[href], [onclick]").forEach(a => { let h = a.getAttribute("href") || "";
      const js = (h + " " + (a.getAttribute("onclick") || "")).match(/['"]([^'"]+\.(?:pdf|docx?))['"]/i); if (js && (!h || h.startsWith("javascript"))) h = js[1];
      if (!h || h.startsWith("javascript") || h.startsWith("#") || h.startsWith("mailto")) return; let u; try { u = new URL(h, base).href; } catch (e) { return; }
      const t = limpio(a.textContent || a.getAttribute("title") || ""); const fila = a.closest("tr,li,article,p") || a.parentElement; const r = fila ? limpio(fila.textContent).slice(0, 320) : "";
      if (!/\.(pdf|docx?)(\?|#|$)|descarg|download|\/file\b|archivo|ley&cual|uuid=|attachments|documento/i.test(u) && !/ley|c[oó]digo|constituci/i.test(t)) return;
      if (!res.has(u)) res.set(u, { t: t.slice(0, 220), r, u }); });
  tomar(document, location.href);
  for (const p of (paginas || [])) { try { tomar(new DOMParser().parseFromString(await textoDe(p), "text/html"), p); } catch (e) {} }
  return [...res.values()]; };
// ---- atajos con el registro de fuentes del repositorio ----
window.REPO = "https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/";
window.CORRIDA = window.CORRIDA || "";
const _host = h => h.replace(/^www\./, "");
window.fuentesRepo = async () => window.__F || (window.__F = await (await fetch(REPO + "kit/fuentes.json?t=" + Date.now(), { cache: "no-store" })).json());
window.etiquetaAqui = pre => pre + location.host.replace(/[^A-Za-z0-9]/g, "").slice(0, 20).toUpperCase() + "_" + CORRIDA.replace(/[^0-9A-Za-z]/g, "");
// encabezados de todas las fuentes del sitio esperado (window.ESPERADO, lo pone el plan) → un trozo listo para reunir.py
// Si la página de entrada redirigió a otro dominio, se intenta igual y cada falla queda anotada con la redirección.
window.revisarAqui = async () => { const D = await fuentesRepo(); const esp = window.ESPERADO || location.origin; const redir = mismoHost(esp, location.origin) ? "" : location.origin;
  const L = D.fuentes.filter(x => mismoHost(x.origen, esp)).map(x => [x.clave, x.url, x.modo, x.enc || ""]); const son = window.__SONDEO || [];
  if (!L.length && !son.length) return "sin fuentes para " + esp;
  window.__CAB = null;
  (async () => { const cab = await cabeceras(L); if (redir) for (const k in cab) if (!cab[k].ok) cab[k].err = "la página de entrada redirigió a " + redir + (cab[k].err ? "; " + cab[k].err : "");
    const so = son.length ? await sondear(son) : {};
    window.__CAB = { cab, son: so, sitio: { esperado: esp, abierto: location.origin, redirigido: redir, t: new Date().toISOString() } }; })();
  return await terminarAqui(); };
// listados oficiales de leyes (fuentes.json → listados): renglones con liga a documento, para detectar archivos renombrados y leyes nuevas
window.listadoAqui = async () => { const D = await fuentesRepo(); const ls = (D.listados || []).filter(l => mismoHost(l.pagina, location.origin));
  if (!ls.length) return "sin listados para " + location.host; const filas = [], err = [], vistos = new Set();
  for (const l of ls) { try { const r = await pedir(l.pagina, {}, 3); if (!r.ok) throw new Error("HTTP " + r.status); const b = new Uint8Array(await r.arrayBuffer());
      let cs = ((r.headers.get("content-type") || "").match(/charset=([\w-]+)/i) || [])[1]; if (!cs) cs = (new TextDecoder("latin1").decode(b.subarray(0, 3000)).match(/charset=["']?([\w-]+)/i) || [])[1] || "utf-8";
      let h; try { h = new TextDecoder(cs).decode(b); } catch (e) { h = new TextDecoder("utf-8").decode(b); }
      const d = new DOMParser().parseFromString(h, "text/html"); const base = r.url || l.pagina; let n = 0;
      d.querySelectorAll("a[href], [onclick]").forEach(a => { let hh = a.getAttribute("href") || ""; const js = (hh + " " + (a.getAttribute("onclick") || "")).match(/['"]([^'"]+\.(?:pdf|docx?))['"]/i);
        if (js && (!hh || hh.startsWith("javascript"))) hh = js[1]; if (!hh || /^(javascript|#|mailto)/i.test(hh)) return; let u; try { u = new URL(hh, base).href; } catch (e) { return; }
        if (!/\.(pdf|docx?)(\?|#|$)|descarg|download|\/archivos?\/|uuid=|attachments|ley&cual/i.test(u) || vistos.has(u)) return; vistos.add(u);
        const fila = a.closest("tr,li,article") || a.parentElement; filas.push([l.id, limpio(a.textContent || a.getAttribute("title") || "").slice(0, 160), u, fila ? limpio(fila.textContent).slice(0, 220) : ""]); n++; });
      if (!n) err.push([l.id, "el listado no trae ligas a documentos (¿cambió la página?)"]); }
    catch (e) { err.push([l.id, String(e && e.message || e).slice(0, 100)]); } }
  const info = preparar({ filas, err, sitio: location.origin, t: new Date().toISOString() }); return info + "\n" + paq(etiquetaAqui("LST"), 0); };
// si revisarAqui respondió «trabajando», llamar de nuevo a terminarAqui() (sin volver a cargar la página)
window.terminarAqui = async () => { for (let k = 0; k < 25 && !window.__CAB; k++) await new Promise(r => setTimeout(r, 1000));
  if (!window.__CAB) return "trabajando: vuelva a llamar await terminarAqui()"; preparar(window.__CAB); return paq(etiquetaAqui("CAB"), 0); };
// texto completo de las fuentes indicadas (claves) de este sitio; después mandar con paq(etiquetaAqui("TXT"), i)
window.leerAqui = async claves => { const D = await fuentesRepo(); const L = claves.map(k => D.fuentes.find(x => x.clave === k)).filter(Boolean).map(x => [x.clave, x.url, x.modo, x.enc || ""]);
  lote(L); const r = await esperar(); return r + "\nETIQUETA " + etiquetaAqui("TXT"); };
"navegador listo";
