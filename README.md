# Áureo Leyes

Actualizaciones automáticas de **Áureo Investigación**: reformas publicadas en el Diario Oficial de la Federación, textos vigentes nuevos de las leyes federales y estatales, noticias fiscales e indicadores (tipo de cambio, INPC).

Al abrirse con internet, la aplicación (archivo `Aureo_Investigacion.html`, con `Aureo_Investigacion_estados.js` en la misma carpeta):
1. lee el **Diario Oficial de la Federación** directamente del servicio oficial SIDOF (`sidof.segob.gob.mx`): publicaciones fiscales,
   decretos de reforma e indicadores (tipo de cambio, UDI, TIIE, INPC) de todos los días pendientes; el día de hoy se vuelve a
   revisar en cada apertura y cada 30 minutos mientras siga abierta;
2. consulta `indice.json` de este repositorio y aplica las actualizaciones que aún no tiene (textos vigentes nuevos de las leyes).
No hay que descargar nada. Sin internet, usa lo guardado y lo indica en el encabezado.

- `indice.json`: lista de actualizaciones publicadas.
- `actualizaciones/`: cada actualización (textos divididos en artículos, decretos, noticias).
- `kit/`: herramientas con que se revisan las fuentes oficiales dos veces al día (ver `kit/PROCEDIMIENTO.md`).

Los textos provienen de fuentes oficiales (DOF, Cámara de Diputados, SAT, Congresos y consejerías jurídicas de los estados). Son documentos de consulta: el texto con validez oficial es el publicado en el Diario Oficial o en el periódico oficial de cada estado.
