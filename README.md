# La Huella del Dato

**¿Quién usa de verdad los datos públicos españoles?**
Web: **https://huella-del-dato.vercel.app**

La Huella del Dato rastrea de forma automática dónde aparecen 35 portales de datos abiertos españoles.
Busca en el código de GitHub, en el texto completo de publicaciones científicas (OpenAlex) y en
Wikipedia. Después una IA lee cada aparición y separa a quien **usa** los datos de quien solo los
**menciona**, dejando la prueba y el motivo de cada decisión.

| | |
|---|---|
| Portales analizados | 35 (estatales, las 17 comunidades autónomas, 8 ayuntamientos y UniversiDATA) |
| Apariciones encontradas | 72.197 (69.942 tras quitar copias y autorreferencias) |
| Leídas una a una por la IA | 9.954 |
| Usos reales verificados | 5.814 |
| Usos reales estimados | 55.457, con intervalo de confianza del 95% |

## Cómo funciona

```
crawl.py        Rastrea GitHub, OpenAlex y Wikipedia                 → data/raw/
fulltext.py     Extrae de los PDF abiertos la frase donde se cita    → data/cache/
consolidate.py  Agrupa, quita copias y repositorios del organismo    → data/processed/reutilizaciones.jsonl
classify.py     Una IA clasifica cada caso (uso, mención…)           → data/processed/ia/sonnet.jsonl
analyze.py      Extrapola las muestras con intervalos de Wilson      → data/processed/resultados.json
build_site.py   Genera la web estática                               → web/
mapa_geo.py     (una vez) Siluetas de las comunidades autónomas      → data/geo/ccaa.json
```

### La IA

La clasificación la hace **Claude Sonnet** (Anthropic), invocado desde Claude Code. Las instrucciones
exactas están en [`pipeline/classify.py`](pipeline/classify.py) (`SISTEMA` e `INSTRUCCIONES`) y también se
publican en la [metodología de la web](https://huella-del-dato.vercel.app/metodologia.html#instrucciones).
La IA solo puede elegir entre cinco veredictos y debe justificar cada uno en una frase.

La IA trabaja **una vez, antes de publicar**. La web es estática y no llama a ningún servicio: las
cifras son fijas, cada decisión se puede revisar y mantenerla cuesta 0 €.

### Muestreo

En los portales con muchas apariciones se clasifica una muestra aleatoria (semilla 2026) de hasta 250
casos por portal y fuente. La proporción de usos se extrapola al total con un intervalo de confianza
del 95% (método de Wilson). En las publicaciones científicas solo se juzgan las que tienen PDF
accesible con la frase de la cita; el resto queda como «cita sin verificar».

## Reproducir

Requiere Python 3.11 o superior.

```bash
pip install requests pypdf         # shapely solo para mapa_geo.py
gunzip -k data/processed/reutilizaciones.jsonl.gz

# Con los datos incluidos se puede rehacer el análisis y la web:
python3 pipeline/analyze.py
python3 pipeline/build_site.py

# Para repetir el rastreo completo hace falta un token de GitHub de solo lectura en .env:
#   GITHUB_TOKEN=...
#   CONTACTO_EMAIL=...   (opcional, se envía a OpenAlex para identificarse)
python3 pipeline/crawl.py
```

La clasificación (`classify.py`) necesita Claude Code instalado y con sesión iniciada.

## Datos incluidos

- `data/portales.csv`: los 35 portales, sus dominios y términos de búsqueda.
- `data/processed/reutilizaciones.jsonl.gz`: las 69.942 apariciones consolidadas.
- `data/processed/excluidos.jsonl`: lo que se descartó y por qué.
- `data/processed/ia/sonnet.jsonl`: el veredicto de la IA para cada caso, con su motivo.
- `data/processed/ia/muestreo.json`: qué se muestreó en cada portal y fuente.
- `data/processed/resultados.json`: las cifras finales con sus márgenes.
- `data/geo/`: provincias de Natural Earth (dominio público) y las siluetas derivadas.

No se incluyen los datos en bruto ni la caché (unos 530 MB); se regeneran con `crawl.py` y `fulltext.py`.

## Limitaciones

Solo se ve la reutilización que deja **rastro público**. Una empresa que usa datos dentro de su producto
es invisible aquí. La búsqueda de código de GitHub tiene un tope de 1.000 resultados por consulta; se
sortea partiendo por tamaño de fichero, con un máximo de 4.000 ficheros por término. Un portal con más
huella no es necesariamente mejor: influyen su antigüedad, su tamaño y el tipo de datos que publica.

## Licencias

- Código: [MIT](LICENSE).
- Datos generados por el proyecto: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).
- Tipografía Bricolage Grotesque: [SIL Open Font License](assets/fuentes/OFL.txt).
- Mapa: [Natural Earth](https://www.naturalearthdata.com/), dominio público.

## Autor

Guillermo Molero Jiménez, estudiante del Grado en Ciencia de Datos e Inteligencia Artificial de la
Universidad Miguel Hernández de Elche. Proyecto presentado al Premio ASEDIE 2026.
