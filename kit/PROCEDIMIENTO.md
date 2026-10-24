# Revisión programada de Áureo Leyes

Se ejecuta dos veces al día (después de la edición matutina y de la vespertina del DOF). Objetivo: que la aplicación de Erik
(`Aureo_Investigacion.html`) reciba sola, al abrirse, las reformas y textos nuevos. Todo se lee con el **navegador integrado**
de la computadora de Erik (los sitios oficiales no responden desde el espacio de trabajo en la nube).

Reglas firmes
- Solo se **lee**. Nunca se guardan archivos en la computadora de Erik, nunca se abre en el navegador la dirección de un
  documento (varios sitios fuerzan la descarga): se abre la página del sitio (`abrir` del plan) y el documento se lee con `fetch`.
- No se hace clic en nada, no se llenan formularios, no se inicia sesión.
- Si la computadora no responde (no hay herramientas del navegador o fallan dos veces), terminar sin insistir. No avisar a Erik por eso.
- Si un sitio falla, seguir con los demás y anotarlo al final.

## 0. Preparación
1. Cargar las herramientas del navegador: ToolSearch `mcp__remote-devices__Claude_Browser__` (max_results 64). Si solo aparece
   `enable__mcp__remote-devices__Claude_Browser`, llamarla primero.
2. Repositorio: `add_repo` (owner `erikherrera1624-creator`, repo `AUREO-LEYES`, access `push`) y
   `git clone --depth 1 https://github.com/erikherrera1624-creator/AUREO-LEYES /home/claude/aureo-leyes` (timeout amplio).
3. Variables: `CORRIDA=$(TZ=America/Mexico_City date +%Y%m%d%H%M)`, `HOY=$(TZ=America/Mexico_City date +%F)`.
   La hora (mañana/noche) define el alcance: mañana = DOF + leyes federales; noche = DOF + federales + estatales.

Cómo se ejecuta una instrucción en un sitio: `navigate` (o `preview_start` si no hay pestañas) a la página indicada y luego
`javascript_tool` con la instrucción. Conviene agrupar 4 sitios por `browser_batch` (navigate, javascript_tool, navigate, …).
Cada respuesta grande se guarda sola como resultado de herramienta; `kit/reunir.py` la recupera por su etiqueta.
Si una instrucción responde «trabajando…», volver a ejecutar en la misma pestaña `await terminarAqui()` (encabezados) o
`await esperar()` (lectura de textos).

## 1. Diario Oficial de la Federación
Fechas a revisar: `python3 kit/dof.py pendientes` (mañana) o `python3 kit/dof.py pendientes noche` (noche). Son todos los días
desde el siguiente a `dof_revisado` de `indice.json` hasta HOY, **sin tope**: si hubo una interrupción se recuperan todos
(de noche se incluye HOY otra vez por la edición vespertina). Procesarlas en orden; los decretos ya publicados no se repiten.
Para cada FECHA (aaaa-mm-dd), en una pestaña abierta en `https://dof.gob.mx/`:
1. Ejecutar (sustituir FECHA, F8 = fecha sin guiones, CORRIDA):
   ```
   window.CORRIDA = "CORRIDA"; await (new Function("return (async()=>{" + await (await fetch("https://raw.githubusercontent.com/erikherrera1624-creator/AUREO-LEYES/main/kit/navegador.js?t=" + Date.now(), { cache: "no-store" })).text() + "\n})()"))();
   preparar(await sumarioDOF("FECHA")); paq("DOFF8_CORRIDA", 0)
   ```
2. `python3 kit/reunir.py DOFF8_CORRIDA kit/tmp/dof --texto` y `python3 kit/dof.py seleccionar FECHA CORRIDA`.
3. Si hay notas relevantes: ejecutar en la misma pestaña el contenido de `kit/tmp/dof/seleccion_FECHA.js`
   (si dice «trozos 2» o más, pedir también `paq("DOFTXF8_CORRIDA", 1)`, etc.), luego
   `python3 kit/reunir.py DOFTXF8_CORRIDA kit/tmp/dof --texto` y `python3 kit/dof.py procesar FECHA CORRIDA`.

## 2. Textos vigentes de las leyes
1. `python3 kit/plan.py CORRIDA federal` (mañana) o `python3 kit/plan.py CORRIDA todo` (noche). Lee `kit/tmp/plan.json`.
   El plan incluye solo: las fuentes del ámbito, **las que fallaron o quedaron pendientes en revisiones anteriores**
   (`kit/registro.json`, también en la corrida de la mañana), los listados oficiales (`tipo: listado`) y los sondeos de
   leyes de ingresos del ejercicio siguiente.
2. Para cada paso: abrir `abrir` y ejecutar `js`. (La instrucción ya trae la carga del kit.) Si un sitio no abre o responde
   error, seguir con los demás: `revisar.py` lo anota como falla y lo deja pendiente.
3. `python3 kit/reunir.py "_CORRIDA$" kit/tmp/cab --texto --patron` y `python3 kit/revisar.py CORRIDA`.
   (Los listados regresan con etiqueta `LST…`; si dicen «trozos 2» o más, pedir `paq(etiquetaAqui("LST"), i)` en la misma pestaña.)
4. Si `kit/tmp/extraer.json` trae sitios: en cada uno abrir `abrir`, ejecutar `js`; la respuesta dice cuántos trozos hay
   y la ETIQUETA; pedir `paq(etiquetaAqui("TXT"), i)` para i = 0…n-1 y luego `python3 kit/reunir.py ETIQUETA kit/tmp/textos`.
   Ahí van: cambios detectados, archivos renombrados, leyes anuales nuevas y hasta 4 fuentes para «validación gradual»
   (se les toma la huella por disposición para poder clasificar sus cambios futuros).

## 3. Publicar
1. `python3 kit/construir.py` (arma `actualizaciones/<id>.json`, actualiza `indice.json`, `kit/fuentes.json`, `kit/registro.json`,
   `kit/huellas/` y `kit/anuales.json`). Clasifica cada lectura (reforma, corrección editorial, formato, documento diferente,
   pendiente de validación); solo publica lo que tiene evidencia suficiente. Lo dudoso queda en `kit/pendientes/`.
2. Siempre (aunque no haya actualización, para guardar controles y fecha de revisión):
   `cd /home/claude/aureo-leyes && git fetch origin main && git rebase origin/main && git add -A && git commit -m "Revisión CORRIDA" && git push origin main`
   (terminar el mensaje de commit con las líneas de atribución vigentes).
3. Si se publicaron **textos nuevos de leyes o decretos de reforma**, mandar a Erik un mensaje breve con SendUserMessage:
   qué leyes cambiaron y que la aplicación lo incorporará sola al abrirla con internet. Si solo hubo noticias o indicadores, no avisar.
   Si `construir.py` imprimió «PENDIENTE DE VALIDACIÓN» o una fuente lleva 3 fallas seguidas (`kit/registro.json`), incluirlo
   en el mensaje en una línea.

## Validación de lecturas dudosas
`python3 kit/validar.py listar` · `ver CLAVE` · `aprobar CLAVE` (publica la versión; la anterior se conserva) · `descartar CLAVE`.
Luego commit y push. Nunca aprobar un «documento_diferente».

## Notas
- `construir.py` no publica una lectura dudosa (menos de la mitad de disposiciones que la versión anterior): lo reporta como AVISO.
- Una fuente sin control previo solo registra su línea base en la primera revisión.
- Cada consulta queda en `kit/registro.json`: dirección pedida y final, resultado, motivo, intentos y fallas seguidas.
  Una falla nunca cambia el control: se conserva la última versión válida y la fuente se reintenta en la siguiente corrida.
- Red: cada documento se pide con tiempo de espera y hasta 3 intentos (0, 2 y 6 s); se rechazan páginas HTML en lugar del
  documento, archivos incompletos y páginas de error. Un cambio de dominio solo se acepta si el destino es oficial (.gob.mx).
- Hidalgo: la portada `www.congreso-hidalgo.gob.mx` redirige a `congresohidalgo.gob.mx`, pero los PDF siguen en el dominio
  anterior. Se revisan desde `…/leyes_cintillo/` (no redirige); el listado oficial está en `congresohidalgo.gob.mx/acervo/public/leyes`.
- Chihuahua: las páginas `index.php` de `congresochihuahua2` mandan un formulario automático a `congresochihuahua.gob.mx`.
  Los PDF se revisan desde `…2.gob.mx/favicon.ico`; los listados, desde `http://www.congresochihuahua.gob.mx/biblioteca/`.
- Archivos renombrados (Jalisco agrega la fecha al nombre: «…-240926.pdf»): se detectan en los listados oficiales por
  familia de archivo y título normalizado; ya no hay que agregarlos a mano.
- Leyes de ingresos del ejercicio siguiente: se buscan solas desde septiembre (sondeo con el año cambiado y listados).
  Estado en `kit/anuales.json`: pendiente_publicacion, detectada, pendiente_validacion o incorporada.

## Versiones de años anteriores (solo cuando se pida)
No forma parte de la revisión programada. Para agregar versiones anteriores de una ley:
1. En una pestaña de `https://web.archive.org/` (el sitio pide permiso en cada acción) definir `window.ENTRADA_HIST` con
   `[{clave, arch, num, actual, h}]` (`arch`: nombre del archivo en Diputados, p. ej. `LISR`; `num`: número que usaba antes,
   p. ej. `8` para el CFF; `actual`: fecha de la última reforma de la versión vigente; `h`: huella de cada disposición vigente,
   ver `fnv`/`canon` en `job.js`) y ejecutar `kit/historicos/job.js`. Avance: `await avance()`.
2. Al terminar, pedir `trozo(i)` para i = 0…`H.trozos`-1, unir los trozos `<<HIST|i|n>>` en un archivo y ejecutar
   `python3 kit/historicos/armar.py paquete.b64 carpeta_actuales reformas.json`.
3. Publicar `historicos/` (la aplicación lo lee de `main`).
