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
Fechas a revisar: desde el día siguiente a `dof_revisado` de `indice.json` hasta HOY (máximo 7 días; en la corrida de la noche
incluir HOY otra vez por la edición vespertina).
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
2. Para cada paso: abrir `abrir` y ejecutar `js`. (La instrucción ya trae la carga del kit.)
3. `python3 kit/reunir.py "_CORRIDA$" kit/tmp/cab --texto --patron` y `python3 kit/revisar.py CORRIDA`.
4. Si `kit/tmp/extraer.json` trae sitios: en cada uno abrir `abrir`, ejecutar `js`; la respuesta dice cuántos trozos hay
   y la ETIQUETA; pedir `paq(etiquetaAqui("TXT"), i)` para i = 0…n-1 y luego `python3 kit/reunir.py ETIQUETA kit/tmp/textos`.

## 3. Publicar
1. `python3 kit/construir.py` (arma `actualizaciones/<id>.json`, actualiza `indice.json` y `kit/fuentes.json`).
2. Siempre (aunque no haya actualización, para guardar controles y fecha de revisión):
   `cd /home/claude/aureo-leyes && git fetch origin main && git rebase origin/main && git add -A && git commit -m "Revisión CORRIDA" && git push origin main`
   (terminar el mensaje de commit con las líneas de atribución vigentes).
3. Si se publicaron **textos nuevos de leyes o decretos de reforma**, mandar a Erik un mensaje breve con SendUserMessage:
   qué leyes cambiaron y que la aplicación lo incorporará sola al abrirla con internet. Si solo hubo noticias o indicadores, no avisar.

## Notas
- `construir.py` no publica una lectura dudosa (menos de la mitad de disposiciones que la versión anterior): lo reporta como AVISO.
- Una fuente sin control previo solo registra su línea base en la primera revisión.
- Hidalgo (`congreso-hidalgo.gob.mx`) y Chihuahua (`congresochihuahua2.gob.mx`) redirigen a otro dominio; si no responden, anotarlo.
- Leyes de ingresos de un ejercicio nuevo (por ejemplo 2027) y sitios que publican con otro nombre de archivo no se detectan
  solos: se agregan a `kit/fuentes.json` cuando se identifiquen (clave, url, modo, origen, formato, arch, ámbito).
