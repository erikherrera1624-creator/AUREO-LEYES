// Versiones históricas de leyes federales: copias archivadas (Internet Archive) de los PDF de la Cámara de Diputados.
// Se ejecuta en una pestaña de web.archive.org. Corre en segundo plano; avance en window.H.
if (!window.H || window.H.reiniciar) window.H = { log: [], res: {}, estado: "inicio", t0: Date.now() };
(() => {
const H = window.H; if (H.corriendo) return; H.corriendo = true;
const ENTRADA = window.ENTRADA_HIST;
const log = m => { H.log.push(new Date().toISOString().slice(11, 19) + " " + m); if (H.log.length > 300) H.log.shift(); };
const espera = ms => new Promise(r => setTimeout(r, ms));
async function pedir(url, opts, n) { n = n || 4; let e; for (let i = 0; i < n; i++) { if (i) await espera(4000 * i * i);
  try { const c = new AbortController(); const t = setTimeout(() => c.abort(), 180000); const r = await fetch(url, Object.assign({ signal: c.signal }, opts || {})); clearTimeout(t);
    if (r.status === 429 || r.status >= 500) { e = new Error("HTTP " + r.status); continue; } return r; } catch (x) { e = x; } } throw e; }
async function cargar() {
  if (!window.pdfjsLib) { const base = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/"; const code = await (await fetch(base + "pdf.min.js")).text(); (new Function(code)).call(window); pdfjsLib.GlobalWorkerOptions.workerSrc = base + "pdf.worker.min.js"; }
  if (!window.LECTOR) { const code = await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/lector.js?t=" + Date.now())).text(); const module = {}; (new Function("module", code))(module); window.LECTOR = module.exports; }
}
// misma lectura de páginas que el kit (navegador.js → paginasPdf)
async function paginasDe(pdf) { const paginas = [];
  for (let i = 1; i <= pdf.numPages; i++) { const pg = await pdf.getPage(i); const tc = await pg.getTextContent(); let linea = "", lineas = [], yAnt = null;
    for (const it of tc.items) { const y = it.transform ? Math.round(it.transform[5]) : null;
      if (yAnt !== null && y !== null && Math.abs(y - yAnt) > 2 && linea) { lineas.push(linea); linea = ""; }
      if (it.str) linea += it.str; if (it.hasEOL && linea.trim()) { lineas.push(linea); linea = ""; } if (it.str) yAnt = y; }
    if (linea) lineas.push(linea); paginas.push(lineas.map(l => l.replace(/\s+/g, " ").trimEnd()).join("\n")); pg.cleanup(); }
  return paginas; }
const MES = { ene: 1, feb: 2, mar: 3, abr: 4, may: 5, jun: 6, jul: 7, ago: 8, sep: 9, set: 9, oct: 10, nov: 11, dic: 12 };
const iso = (a, m, d) => { a = +a; if (a < 100) a += 2000; return `${a}-${String(+m).padStart(2, "0")}-${String(+d).padStart(2, "0")}`; };
function fechaPortada(t) { // «Última Reforma DOF 01-04-2024» o «Nueva Ley publicada en el DOF el 11 de diciembre de 2013»
  const s = t.replace(/\s+/g, " ");
  let m = /[ÚU]ltima\s+reforma\s+(?:publicada\s+)?(?:en\s+el\s+)?DOF\s+(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{2,4})/i.exec(s); if (m) return { f: iso(m[3], m[2], m[1]), tipo: "reforma" };
  m = /[ÚU]ltima\s+reforma[^.]{0,40}?(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})/i.exec(s); if (m && MES[m[2].slice(0, 3).toLowerCase()]) return { f: iso(m[3], MES[m[2].slice(0, 3).toLowerCase()], m[1]), tipo: "reforma" };
  m = /(?:Nueva\s+Ley|Nuevo\s+C[oó]digo|Ley)\s+publicad[ao]\s+en\s+el\s+(?:Diario\s+Oficial\s+de\s+la\s+Federaci[oó]n|DOF)\s+el\s+(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})/i.exec(s);
  if (m && MES[m[2].slice(0, 3).toLowerCase()]) return { f: iso(m[3], MES[m[2].slice(0, 3).toLowerCase()], m[1]), tipo: "original" };
  return null; }
const fnv = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return (h >>> 0).toString(16).padStart(8, "0").slice(0, 6); };
const canon = u => [u.tipo, u.nn, u.titulo, u.ubicacion, u.texto].map(x => String(x || "").replace(/\s+/g, " ").trim()).join("|");
function claves(us) { const c = {}; return us.map(u => { const n = c[u.nn] || 0; c[u.nn] = n + 1; return u.nn + "#" + n; }); }
function delta(us, ref) {
  const ks = claves(us); let rmap = null; if (ref.units) { rmap = {}; claves(ref.units).forEach((k, i) => rmap[k] = ref.units[i]); }
  return us.map((u, i) => { const k = ks[i]; const h = fnv(canon(u)); const rh = rmap ? (rmap[k] ? fnv(canon(rmap[k])) : null) : ref.h[k];
    if (rh && h === rh) return [k, u.pagina, u.orden];
    const ps = String(u.texto || "").split("\n\n"); let ops = ps; const ru = rmap && rmap[k];
    if (ru) { const idx = new Map(); String(ru.texto || "").split("\n\n").forEach((p, j) => { if (!idx.has(p)) idx.set(p, j); }); ops = ps.map(p => idx.has(p) ? idx.get(p) : p); }
    return { k, f: { tipo: u.tipo, numero: u.numero, nn: u.nn, titulo: u.titulo, ubicacion: u.ubicacion, fechas: u.fechas, pagina: u.pagina, orden: u.orden }, p: ops }; }); }
async function cdx(q) { const r = await pedir("/cdx/search/cdx?" + q + "&fl=original,timestamp,length,digest,mimetype&collapse=digest&filter=statuscode:200&output=json"); const j = await r.json(); return j.slice(1); }
async function portada(ts, original) { // solo las primeras páginas (pedidos parciales cuando el servidor los acepta); fecha con el mismo lector del kit
  const pdf = await pdfjsLib.getDocument({ url: `/web/${ts}id_/${original}`, disableAutoFetch: true, disableStream: true, rangeChunkSize: 131072, isEvalSupported: false, verbosity: 0 }).promise;
  const pags = []; for (let i = 1; i <= Math.min(3, pdf.numPages); i++) { const pg = await pdf.getPage(i); const tc = await pg.getTextContent(); let linea = "", lineas = [], yAnt = null;
    for (const it of tc.items) { const y = it.transform ? Math.round(it.transform[5]) : null; if (yAnt !== null && y !== null && Math.abs(y - yAnt) > 2 && linea) { lineas.push(linea); linea = ""; }
      if (it.str) linea += it.str; if (it.hasEOL && linea.trim()) { lineas.push(linea); linea = ""; } if (it.str) yAnt = y; }
    if (linea) lineas.push(linea); pags.push(lineas.map(l => l.replace(/\s+/g, " ").trimEnd()).join("\n")); }
  const n = pdf.numPages; await pdf.destroy();
  let meta = {}; try { meta = LECTOR.documento(pags, "articulos").meta || {}; } catch (e) {}
  return { t: pags.join("\n"), n, f: meta.fecha_ultima_reforma || null }; }
async function ley(E) {
  const R = { clave: E.clave, versiones: [], err: [], candidatos: [] }; H.res[E.clave] = R; H.estado = E.clave + ": buscando copias";
  let filas = [];
  for (const q of [`url=diputados.gob.mx/LeyesBiblio/pdf/${E.arch}.pdf`, `url=diputados.gob.mx/LeyesBiblio/pdf/${E.arch}_*`]) { try { filas = filas.concat(await cdx(q)); } catch (e) { R.err.push("cdx " + q + ": " + e.message); } await espera(2500); }
  filas = filas.filter(([o, ts, len, dg, mt]) => /pdf/i.test(mt || "") && +len > 200000 && new RegExp("/pdf/" + E.arch + "(_\\d{6,8})?\\.pdf$", "i").test(o.split("?")[0]));
  const vistos = new Set(); const cand = [];
  for (const [o, ts, len, dg] of filas) { if (vistos.has(dg)) continue; vistos.add(dg);
    const md = /_(\d{2})(\d{2})(\d{2,4})\.pdf$/i.exec(o); cand.push({ o, ts, len: +len, dg, fNombre: md ? iso(md[3], md[2], md[1]) : null }); }
  for (const c of cand) { H.estado = E.clave + ": portada " + c.ts; try { const p = await portada(c.ts, c.o); if (p.f) { c.f = p.f; c.tipo = "reforma"; } else { const f = fechaPortada(p.t); c.f = f ? f.f : c.fNombre; c.tipo = f ? f.tipo : "reforma"; } c.n = p.n; } catch (e) { c.err = String(e.message || e).slice(0, 80); c.f = c.fNombre; } await espera(800); }
  R.candidatos = cand.map(c => [c.o.split("/").pop(), c.ts, c.len, c.f, c.tipo, c.n, c.err || ""]);
  // una copia por fecha de reforma (la más reciente de cada una), sin la versión que ya tiene la aplicación
  const porF = {}; cand.filter(c => c.f && !c.err && c.n && c.f < E.actual).forEach(c => { if (!porF[c.f] || c.ts > porF[c.f].ts) porF[c.f] = c; });
  const elegidos = Object.values(porF).sort((a, b) => b.f.localeCompare(a.f));
  let ref = { h: E.h }; const listos = new Set();
  for (const c of elegidos) { H.estado = E.clave + ": leyendo " + c.f;
    try { const r = await pedir(`/web/${c.ts}id_/${c.o}`); const buf = new Uint8Array(await r.arrayBuffer());
      if (buf[0] !== 0x25 || buf[1] !== 0x50) throw new Error("no es PDF");
      const pdf = await pdfjsLib.getDocument({ data: buf, isEvalSupported: false, verbosity: 0 }).promise; const pags = await paginasDe(pdf); await pdf.destroy();
      const doc = LECTOR.documento(pags, "articulos"); const fm = (doc.meta || {}).fecha_ultima_reforma || c.f;
      if (listos.has(fm)) { R.err.push(c.f + ": repetida (" + fm + ")"); continue; } listos.add(fm);
      const us = doc.unidades; const d = delta(us, ref);
      R.versiones.push({ f: fm, fPortada: c.f, tipo: c.tipo, meta: doc.meta, archivo: c.o, ts: c.ts, paginas: pags.length, num: us.length, cambios: d.filter(x => !Array.isArray(x)).length, u: d });
      ref = { units: us }; log(E.clave + " " + fm + ": " + us.length + " disposiciones, " + R.versiones[R.versiones.length - 1].cambios + " distintas");
    } catch (e) { R.err.push(c.f + ": " + String(e.message || e).slice(0, 100)); log(E.clave + " " + c.f + " ERROR " + e.message); }
    await espera(1500); }
  R.fin = true; }
(async () => { try { await cargar(); log("listo pdf.js y lector");
  for (const E of ENTRADA) { if (H.res[E.clave] && H.res[E.clave].fin) continue; try { await ley(E); } catch (e) { log(E.clave + " FALLA " + e.message); } }
  H.estado = "empaquetando"; const j = JSON.stringify(H.res);
  const gz = new Uint8Array(await new Response(new Blob([j]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
  let b = ""; for (let k = 0; k < gz.length; k += 32768) b += String.fromCharCode.apply(null, gz.subarray(k, k + 32768));
  H.paquete = btoa(b); H.trozos = Math.ceil(H.paquete.length / 240000); H.estado = "fin"; log("paquete " + H.paquete.length + " car, " + H.trozos + " trozos");
} catch (e) { H.estado = "error: " + e.message; log("ERROR " + e.stack); } finally { H.corriendo = false; } })();
})();
window.trozo = i => "<<HIST|" + i + "|" + window.H.trozos + ">>" + window.H.paquete.slice(i * 240000, (i + 1) * 240000) + "<<FIN>>";
window.avance = async s => { for (let k = 0; k < (s || 38) && window.H.estado !== "fin" && !/^error/.test(window.H.estado); k++) await new Promise(r => setTimeout(r, 1000));
  const H = window.H; return JSON.stringify({ estado: H.estado, min: Math.round((Date.now() - H.t0) / 60000), log: H.log.slice(-25), leyes: Object.values(H.res).map(r => [r.clave, r.fin ? "fin" : "…", r.versiones.length, r.versiones.map(v => v.f + "(" + v.cambios + ")").join(" "), r.err.slice(0, 6)]), trozos: H.trozos || 0 }); };
"iniciado";
