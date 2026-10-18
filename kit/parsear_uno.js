// node kit/parsear_uno.js paginas.json formato  → imprime {meta, unidades} (divide en artículos, reglas, criterios o páginas)
const P = require('./lector.js'); const fs = require('fs');
const pags = JSON.parse(fs.readFileSync(process.argv[2])); process.stdout.write(JSON.stringify(P.documento(pags, process.argv[3] || 'articulos')));
