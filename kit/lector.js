const sinAcentos = s => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const P = (() => {
  const MES_N = { enero:1,febrero:2,marzo:3,abril:4,mayo:5,junio:6,julio:7,agosto:8,septiembre:9,setiembre:9,octubre:10,noviembre:11,diciembre:12 };
  function fechaDMY(d, m, a) { d = +d; m = +m; a = +a; if (a < 100) a += a > 50 ? 1900 : 2000; if (m >= 1 && m <= 12 && d >= 1 && d <= 31) return `${String(a).padStart(4,"0")}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`; return null; }
  function normalizarNumero(num) {
    let t = sinAcentos(num || "").toLowerCase().trim();
    t = t.replace(/(\d+)\s*(?:o\.|o\b|°|º)/g, "$1").replace(/[.\-–]/g, " ").replace(/\s+/g, " ").trim();
    return t.replace(/ /g, "-");
  }
  function claveOrden(nn) {
    const m = /^(\d+)(?:-([a-z]{1,2})(?![a-z]))?(?:-(bis|ter|quater|quintus|quinquies|sexies))?(?:-(\d+))?/.exec(nn || "");
    if (!m) return [0, 0, 0, 0];
    let l = 0; if (m[2]) [...m[2]].reverse().forEach((c, i) => { l += (c.charCodeAt(0) - 96) * Math.pow(27, i); });
    const suf = { bis: 1, ter: 2, quater: 3, quintus: 4, quinquies: 4, sexies: 5 }[m[3] || ""] || 0;
    return [+m[1], l, suf, +(m[4] || 0)];
  }
  const mayor = (a, b) => { for (let i = 0; i < 4; i++) { if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0); } return false; };
  function fechasDof(texto) {
    const vistas = [];
    for (const m of String(texto || "").matchAll(/DOF\s+((?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}(?:\s*(?:,|y|e)\s*)?)+)/g))
      for (const x of m[1].matchAll(/(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})/g)) { const f = fechaDMY(x[1], x[2], x[3]); if (f && !vistas.includes(f)) vistas.push(f); }
    // notas de periódicos oficiales estatales: «publicado en el P.O. No. 0190 ... de fecha 16 de mayo de 2016»
    for (const m of String(texto || "").matchAll(/P\.\s?O\.[\s\S]{0,120}?de\s+fecha\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})/gi)) { const mes = MES_N[sinAcentos(m[2]).toLowerCase()]; const f = mes && fechaDMY(m[1], mes, m[3]); if (f && !vistas.includes(f)) vistas.push(f); }
    return vistas;
  }
  function fechaLarga(t) { const m = /(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})/i.exec(t || ""); if (!m) return null; const mes = MES_N[sinAcentos(m[2]).toLowerCase()]; return mes ? fechaDMY(m[1], mes, m[3]) : null; }
  const PIE = [/^\s*\d+\s+de\s+\d+\s*$/i, /^\s*P[aá]gina\s+\d+(\s+de\s+\d+)?\s*$/i, /^\s*-?\s*\d{1,4}\s*-?\s*$/, /^\s*C[AÁ]MARA DE DIPUTADOS DEL H\. CONGRESO DE LA UNI[OÓ]N\s*$/i,
    /^\s*Secretar[ií]a (General|de Servicios Parlamentarios)\s*$/i, /^\s*[ÚU]ltima [Rr]eforma (publicada )?DOF\s+[\d\-/]+\s*$/,
    /^\s*(Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s+DIARIO OFICIAL.*$/i,
    /^\s*DIARIO OFICIAL\s+(\(.*\)\s*)?(Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}.*$/i];
  function limpiar(paginas) {
    const n = Math.max(1, paginas.length), conteo = new Map();
    paginas.forEach(t => new Set(t.split("\n").map(l => l.trim()).filter(Boolean)).forEach(l => conteo.set(l, (conteo.get(l) || 0) + 1)));
    const umbral = Math.max(3, Math.floor(n * 0.3)), rep = new Set();
    if (n >= 4) conteo.forEach((c, l) => { if (c >= umbral && l.length < 240) rep.add(l); });
    const out = [];
    paginas.forEach((t, i) => t.split("\n").forEach(ln => { const s = ln.replace(/\s+$/, ""), st = s.trim();
      if (!st) { out.push([i + 1, ""]); return; } if (rep.has(st) || PIE.some(r => r.test(st))) return; out.push([i + 1, s]); }));
    return out;
  }
  function encabezado(paginas) { const t = paginas.slice(0, 2).join("\n"); const m = /[ÚU]ltima [Rr]eforma (?:publicada )?DOF\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})/.exec(t);
    return m ? { ultima_reforma: `DOF ${m[1]}-${m[2]}-${m[3]}`, fecha_ultima_reforma: fechaDMY(m[1], m[2], m[3]) } : { ultima_reforma: null, fecha_ultima_reforma: null }; }
  const RE_ART = /^\s*(?:Art[ií]culo\.?|ART[IÍ]CULO\.?|Art\.|ART\.)\s+(\d{1,4}(?:\.\d{1,4})?\s*(?:o\.?|°|º)?(?:\s*\.?\s*-\s*[A-Z]{1,2}\b)?(?:\s+(?:[Bb]is|BIS|[Tt]er|TER|Qu[aá]ter|Quintus|Quinquies|Sexies)(?:\s*\d+)?)?)\s*(\.\s*-|\.-|\.|-)\s*(.*)$/;
  const RE_TRANS_ART = /^\s*(?:Art[ií]culo|ART[IÍ]CULO)\s+([ÚU]nico|UNICO|[ÚU]NICO|Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|S[eé]ptimo|Octavo|Noveno|D[eé]cimo[\w\s]*?|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)\s*[.\-]/;
  const RE_TRANSITORIOS = /^\s*(ART[IÍ]CULOS?\s+)?TRANSITORIOS?\s*$|^\s*Transitorios?\s*$/;
  const RE_DECRETO = /^\s*DECRETO\s+(por el que|que|mediante|por medio)/i;
  const RE_UBIC = /^\s*(T[IÍ]TULO|CAP[IÍ]TULO|SECCI[OÓ]N|LIBRO|Libro|T[ií]tulo|Cap[ií]tulo|Secci[oó]n)\s+([IVXLCDM]+|[ÚU]NICO|[ÚU]nico|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO|D[EÉ]CIMO\w*|Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|S[eé]ptimo|Octavo|Noveno|\d+)\b\s*(.*)$/;
  const RE_NOTA = /^\s*(Art[ií]culo|P[aá]rrafo|Fracci[oó]n|Inciso|Apartado|Secci[oó]n|Cap[ií]tulo|T[ií]tulo|Denominaci[oó]n|Libro|[ÚU]ltimo|Pen[uú]ltimo|Primer|Segundo|Tercer|Cuarto|Quinto|Sexto|Fe de erratas|Reforma|Numeral|Subinciso|Tabla|Tarifa|Cantidad|Cantidades|P[aá]rrafos)[^\n]{0,160}?(reformad|adicionad|derogad|recorrid|actualizad|corregid|modificad)[oa]s?\b[^\n]*DOF\s+\d/i;
  const RE_NOTA_RMF = /^\s*-\s*(Reformad|Adicionad|Derogad|Modificad)[oa]s?\b[^\n]*(DOF|RMRMF)/i;
  const RE_NOTA_EST = /^\s*Nota:\s*(Se\s+)?(reform|adicion|derog|recorr|modific|actualiz)/i;
  const esNota = l => RE_NOTA.test(l || "") || RE_NOTA_RMF.test(l || "") || RE_NOTA_EST.test(l || "");
  function unir(lineas) {
    const pars = []; let act = [];
    for (const ln of lineas) { const st = ln.trim();
      if (!st) { if (act.length) { pars.push(act.join(" ")); act = []; } continue; }
      if (esNota(st)) { if (act.length) { pars.push(act.join(" ")); act = []; } pars.push(st); continue; }
      const nuevo = /^([IVXLC]+\.|[a-z]\)|\d+\.|[A-Z]\.|“|")\s/.test(st);
      if (act.length && (nuevo || /[.;:]$/.test(act[act.length - 1]))) { pars.push(act.join(" ")); act = []; }
      act.push(st); }
    if (act.length) pars.push(act.join(" "));
    return pars.filter(Boolean).join("\n\n").replace(/(\w)- (\w)/g, "$1$2")
      .replace(/\s*NOTA: Este documento constituye una compilación[^\n]*?(Diario Oficial de la Federación\.|con la finalidad)/g, " ")
      .replace(/\s*de dar a conocer el texto actualizado de la Resolución Miscelánea Fiscal[^\n]*?Derechos/g, " ")
      .replace(/\s*del Contribuyente\. Para sustentar legalmente actos o resoluciones se deberá utilizar la publicación del Diario Oficial de la Federación\./g, " ").trim();
  }
  function articulos(lp) {
    const us = [], ubic = { libro: "", titulo: "", capitulo: "", seccion: "" };
    let act = null, ult = [0, 0, 0], enT = false, bt = null, pend = null, nT = 0;
    const cerrar = () => { if (act) { act.texto = unir(act.lineas); act.fechas = fechasDof(act.texto).sort().join(","); delete act.lineas; us.push(act); act = null; } };
    const cerrarT = () => { if (bt && bt.lineas.some(l => l.trim())) { bt.texto = unir(bt.lineas); bt.fechas = bt.fecha || ""; delete bt.lineas; delete bt.fecha; us.push(bt); } bt = null; };
    for (const [pag, ln] of lp) { const st = ln.trim();
      if (!enT && RE_TRANSITORIOS.test(st) && (us.length || act)) { cerrar(); enT = true; nT++; bt = { tipo: "transitorio", numero: "T" + nT, nn: "t" + nT, titulo: "Transitorios de la publicación original", ubicacion: "Disposiciones transitorias", pagina: pag, lineas: [], fecha: null }; continue; }
      if (enT) {
        if (RE_DECRETO.test(st)) { cerrarT(); nT++; bt = { tipo: "transitorio", numero: "T" + nT, nn: "t" + nT, titulo: st.slice(0, 300), ubicacion: "Transitorios de decretos de reforma", pagina: pag, lineas: [], fecha: null }; continue; }
        if (bt) {
          if (!bt.fecha && /(Diario Oficial de la Federaci[oó]n|D\.O\.F\.)/i.test(st)) { const f = fechaLarga(st) || fechasDof(st)[0]; if (f) bt.fecha = f; }
          const abierto = bt.titulo.startsWith("DECRETO") && !bt.lineas.length && bt.titulo.length < 400;
          if (abierto && st && !/^\s*(Publicado|D\.O\.F|Diario|DOF)/.test(st) && !RE_TRANSITORIOS.test(st) && !RE_TRANS_ART.test(st) && !/\.\s*$/.test(bt.titulo)) { bt.titulo += " " + st; continue; }
          bt.lineas.push(ln);
        }
        continue;
      }
      const mu = RE_UBIC.exec(st);
      if (mu && st.length < 160 && !/,$/.test(st) && !/\b(de esta|del presente|de la presente)\b/i.test(st)) {
        const nivel = sinAcentos(mu[1]).toLowerCase(), et = mu[1].charAt(0).toUpperCase() + mu[1].slice(1).toLowerCase() + " " + mu[2], resto = mu[3].replace(/^[\s.\-]+|[\s.\-]+$/g, "");
        const k = nivel.startsWith("libro") ? "libro" : nivel.startsWith("titulo") ? "titulo" : nivel.startsWith("capitulo") ? "capitulo" : "seccion";
        ubic[k] = et + (resto ? " — " + resto : "");
        if (k === "libro" || k === "titulo") { ubic.capitulo = ""; ubic.seccion = ""; } else if (k === "capitulo") ubic.seccion = "";
        pend = resto ? null : k; continue;
      }
      if (pend && st && st.length < 160 && !RE_ART.test(st)) { if (st === st.toUpperCase() || (/^[A-ZÁÉÍÓÚÑ]/.test(st) && !/\.$/.test(st))) { ubic[pend] += " — " + st; pend = null; continue; } }
      if (st) pend = null;
      const m = RE_ART.exec(st);
      if (m) { const num = m[1].replace(/\s+/g, " ").trim(), sep = m[2].replace(/\s/g, ""), resto = m[3].replace(/^[.\-–\s]+/, ""), nn = normalizarNumero(num), orden = claveOrden(nn);
        const valido = (!resto || /^[A-ZÁÉÍÓÚÑ¿“"(\[]/.test(resto)) && !/^[A-Z]\s+(de|del|y|o|en|a|al)\b/.test(resto);
        if (valido && ((!us.length && !act) || mayor(orden, ult))) { cerrar(); ult = orden;
          act = { tipo: "articulo", numero: num, nn, titulo: "Artículo " + num, ubicacion: [ubic.libro, ubic.titulo, ubic.capitulo, ubic.seccion].filter(Boolean).join(" / "), pagina: pag, lineas: resto ? [resto] : [] }; continue; } }
      if (act) act.lineas.push(ln);
    }
    cerrar(); cerrarT(); us.forEach((u, i) => u.orden = i); return us;
  }
  const RE_REGLA = /^\s*(?:Regla\s+)?(\d{1,2}(?:\.\d{1,3}){1,4})\.\s+([A-ZÁÉÍÓÚÑ¿“"].{2,220})$/;
  const RE_UBIC_RMF = /^\s*(T[ií]tulo|Cap[ií]tulo|Secci[oó]n|Subsecci[oó]n)\s+(\d{1,2}(?:\.\d{1,3}){0,4})\.?\s+(.*)$/;
  const RE_REF_LINEA = /^(?:[A-Z]{2,7}|Ley|Decreto|DECRETO|Reglamento|Anexo|Circular|Acuerdo)\b[^\n]{0,40}?\s\d/;
  const esTituloRegla = t => !!t && t.length < 220 && !/[.;:,]$/.test(t) && !RE_REF_LINEA.test(t) && !RE_REGLA.test(t) && !/^[IVXLC]+\.\s/.test(t) && !/^[a-z]\)\s/.test(t) && !RE_UBIC_RMF.test(t) && !/^-\s/.test(t) && !/\b[A-Z]{2,6}\s\d+(-[A-Z])?\b/.test(t) && !/^[A-Z](-[A-Z])?,\s/.test(t) && !/\d+(-[A-Z])?,\s*\d/.test(t);
  function reglas(lp) {
    const cand = [], ubic = {}; let act = null, enT = false, tr = null, previo = [];
    const ORDEN = ["titulo", "capitulo", "seccion", "subseccion"];
    const cerrar = () => { if (act) { act.texto = unir(act.lineas); delete act.lineas; act.fechas = fechasDof(act.texto).sort().join(","); cand.push(act); act = null; } };
    for (const [pag, ln] of lp) { const st = ln.trim();
      if (cand.length && RE_TRANSITORIOS.test(st)) { cerrar(); enT = true; if (tr) { tr.texto = unir(tr.lineas); delete tr.lineas; cand.push(tr); }
        tr = { tipo: "transitorio", numero: "Transitorios", nn: "transitorios", titulo: "Disposiciones transitorias", ubicacion: "Transitorios", pagina: pag, lineas: [] }; continue; }
      if (enT) { if (RE_REGLA.test(st) || RE_UBIC_RMF.test(st)) enT = false; else { tr.lineas.push(ln); continue; } }
      const mu = RE_UBIC_RMF.exec(st);
      if (mu && st.length < 200) { const nv = sinAcentos(mu[1]).toLowerCase(); ubic[nv] = `${mu[1].charAt(0).toUpperCase() + mu[1].slice(1)} ${mu[2]} ${mu[3].trim()}`.trim();
        ORDEN.slice(ORDEN.indexOf(nv) + 1).forEach(k => delete ubic[k]); cerrar(); previo = []; continue; }
      const m = RE_REGLA.exec(st);
      if (m) {
        let titulo = "";
        const fuente = act ? act : { lineas: previo };
        { const ls = fuente.lineas; let i = ls.length - 1; while (i >= 0 && !ls[i].trim()) i--;
          const tomados = []; while (i >= 0 && tomados.length < 3 && esTituloRegla(ls[i].trim())) { tomados.unshift(ls[i].trim()); i--; while (i >= 0 && !ls[i].trim()) i--; }
          const anterior = i >= 0 ? ls[i].trim() : "";
          if (tomados.length && /^[A-ZÁÉÍÓÚÑ¿“"(]/.test(tomados[0]) && (i < 0 || /[.;:)]$/.test(anterior) || RE_REF_LINEA.test(anterior))) { titulo = tomados.join(" "); fuente.lineas = ls.slice(0, i + 1); } }
        cerrar(); previo = [];
        const resto = m[2].trim(), soloTitulo = !titulo && /^[A-ZÁÉÍÓÚÑ¿“"][^.]{3,140}$/.test(resto) && !/^Para (los )?(efectos|fines)\b/.test(resto) && !/\s(se|de|del|la|las|los|el|y|o|que|en|a|al|por|con|para)$/.test(resto);
        act = { tipo: "regla", numero: m[1], nn: m[1], titulo: `Regla ${m[1]}. ${titulo || (soloTitulo ? resto : resto.slice(0, 100).replace(/\s+\S*$/, "") + "…")}`, propio: !!titulo || soloTitulo,
          ubicacion: ORDEN.filter(k => ubic[k]).map(k => ubic[k]).join(" / "), pagina: pag, lineas: soloTitulo ? [] : [resto] };
        continue; }
      if (act) act.lineas.push(ln); else previo.push(ln);
    }
    cerrar(); if (tr) { tr.texto = unir(tr.lineas); delete tr.lineas; cand.push(tr); }
    const val = u => (u.texto || "").length;
    const mej = new Map(); cand.forEach(u => { const k = u.tipo + "|" + u.nn, prev = mej.get(k); if (!prev || val(u) > val(prev)) { if (prev && prev.propio && !u.propio) { u.titulo = prev.titulo; u.propio = true; } mej.set(k, u); } else if (u.propio && !prev.propio) { prev.titulo = u.titulo; prev.propio = true; } });
    const us = [...mej.values()].filter(u => u.tipo === "transitorio" || val(u) > 20);
    us.forEach(u => delete u.propio);
    const tup = n => n.split(".").map(Number);
    us.sort((a, b) => { if (a.tipo !== b.tipo) return a.tipo === "regla" ? -1 : 1; const x = tup(a.numero), y = tup(b.numero); for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (x[i] ?? -1) - (y[i] ?? -1); if (d) return d; } return 0; });
    us.forEach((u, i) => u.orden = i); return us;
  }
  const RE_CRIT = /^\s*(\d{1,3}\/[A-Z]{2,8}(?:\/[A-Z]{1,3})?\/(?:NV|N|PI))\s+(.{3,250})$/;
  function criterios(lp) {
    const cand = []; let act = null, sec = "";
    for (const [pag, ln] of lp) { const st = ln.trim();
      if (/^\s*(A|B|C)\.\s+(Vigentes|Hist[oó]ricos|Criterios)/.test(st)) sec = st;
      const m = RE_CRIT.exec(st);
      if (m) { if (act) { act.texto = unir(act.lineas); delete act.lineas; cand.push(act); } act = { tipo: "criterio", numero: m[1], nn: m[1].toLowerCase(), titulo: `${m[1]} ${m[2].trim()}`, ubicacion: sec, pagina: pag, lineas: [] }; continue; }
      if (act) act.lineas.push(ln); }
    if (act) { act.texto = unir(act.lineas); delete act.lineas; cand.push(act); }
    const mej = new Map(); cand.forEach(u => { if (!mej.has(u.nn) || u.texto.length > mej.get(u.nn).texto.length) mej.set(u.nn, u); });
    const us = [...mej.values()]; us.sort((a, b) => { const [na, la] = a.nn.split("/"), [nb, lb] = b.nn.split("/"); return la === lb ? (+na - +nb) : (la < lb ? -1 : 1); });
    us.forEach((u, i) => { u.orden = i; u.fechas = ""; }); return us;
  }
  function paginasU(paginas) {
    const por = new Map(); limpiar(paginas).forEach(([p, l]) => { if (!por.has(p)) por.set(p, []); por.get(p).push(l); });
    const us = []; [...por.keys()].sort((a, b) => a - b).forEach(p => { const tx = unir(por.get(p)); if (tx.length < 15) return;
      const pri = (por.get(p).find(l => l.trim().length > 4) || "Página " + p).trim();
      us.push({ tipo: "pagina", numero: String(p), nn: String(p), titulo: `Pág. ${p}: ${pri.slice(0, 110)}`, ubicacion: "", texto: tx, pagina: p, fechas: "" }); });
    us.forEach((u, i) => u.orden = i); return us;
  }
  function documento(paginas, formato) {
    const meta = Object.assign(encabezado(paginas), { paginas: paginas.length });
    if (formato === "paginas") return { unidades: paginasU(paginas), meta };
    const lp = limpiar(paginas);
    let us = formato === "reglas" ? reglas(lp) : formato === "criterios" ? criterios(lp) : articulos(lp);
    if (us.filter(u => u.tipo !== "transitorio").length < 3) { meta.aviso = "No se reconoció la estructura esperada; el documento se indexó por páginas."; us = paginasU(paginas); }
    return { unidades: us, meta };
  }
  return { documento, normalizarNumero, esNota, fechasDof };
})();

module.exports=P;