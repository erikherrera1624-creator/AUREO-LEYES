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
window.extraer = async (nombre, url, modo, enc) => { const r = await fetch(url); if (!r.ok) throw new Error("HTTP " + r.status); const buf = new Uint8Array(await r.arrayBuffer());
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
// encabezados de control: fecha de modificación, tamaño y etiqueta; si el sitio no da ninguno, huella del contenido
window.cabeceras = async L => { const o = {}; let k = 0;
  const uno = async ([clave, url, modo, enc]) => { try { let r; try { r = await fetch(url, { method: "HEAD" }); } catch (e) { r = { ok: false, status: 0, headers: new Headers() }; } let lm = r.headers.get("last-modified") || "", et = r.headers.get("etag") || "", cl = r.headers.get("content-length") || "";
      let h = ""; if (!r.ok || (!lm && !et) || modo === "html") { r = await fetch(url); const b = new Uint8Array(await r.arrayBuffer()); lm = r.headers.get("last-modified") || lm; et = r.headers.get("etag") || et;
        let datos = b; if (modo === "html") { datos = new TextEncoder().encode(paginasHtml(new TextDecoder(enc || "utf-8").decode(b)).join("\n")); }
        h = [...new Uint8Array(await crypto.subtle.digest("SHA-256", datos))].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 24); cl = String(b.length); }
      o[clave] = { s: r.status, lm, et, cl, h }; } catch (e) { o[clave] = { s: 0, err: e.message.slice(0, 80) }; } };
  const trab = async () => { while (k < L.length) await uno(L[k++]); }; await Promise.all([trab(), trab(), trab(), trab()]); return o; };
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
// ---- atajos con el registro de fuentes del repositorio ----
window.REPO = "https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/";
window.CORRIDA = window.CORRIDA || "";
const _host = h => h.replace(/^www\./, "");
window.fuentesRepo = async () => window.__F || (window.__F = await (await fetch(REPO + "kit/fuentes.json?t=" + Date.now(), { cache: "no-store" })).json());
window.etiquetaAqui = pre => pre + location.host.replace(/[^A-Za-z0-9]/g, "").slice(0, 20).toUpperCase() + "_" + CORRIDA.replace(/[^0-9A-Za-z]/g, "");
// encabezados de todas las fuentes de este sitio → un trozo listo para reunir.py
window.revisarAqui = async () => { const D = await fuentesRepo(); const L = D.fuentes.filter(x => _host(new URL(x.origen).host) === _host(location.host)).map(x => [x.clave, x.url, x.modo, x.enc || ""]);
  if (!L.length) return "sin fuentes para " + location.host; window.__CAB = null; cabeceras(L).then(o => { window.__CAB = o; }); return await terminarAqui(); };
// si revisarAqui respondió «trabajando», llamar de nuevo a terminarAqui() (sin volver a cargar la página)
window.terminarAqui = async () => { for (let k = 0; k < 25 && !window.__CAB; k++) await new Promise(r => setTimeout(r, 1000));
  if (!window.__CAB) return "trabajando: vuelva a llamar await terminarAqui()"; preparar(window.__CAB); return paq(etiquetaAqui("CAB"), 0); };
// texto completo de las fuentes indicadas (claves) de este sitio; después mandar con paq(etiquetaAqui("TXT"), i)
window.leerAqui = async claves => { const D = await fuentesRepo(); const L = claves.map(k => D.fuentes.find(x => x.clave === k)).filter(Boolean).map(x => [x.clave, x.url, x.modo, x.enc || ""]);
  lote(L); const r = await esperar(); return r + "\nETIQUETA " + etiquetaAqui("TXT"); };
"navegador listo";
