"""Consolida los resultados en bruto en reutilizaciones limpias.

Lee data/raw/<fuente>/<portal>.jsonl y escribe:
  - data/processed/reutilizaciones.jsonl  una fila por reutilización (repositorio,
                                          publicación o artículo de Wikipedia)
  - data/processed/excluidos.jsonl        autorreferencias y copias, con el motivo
  - data/processed/resumen_portales.json  recuento por portal, fuente y clasificación

Limpieza:
  1. GitHub se agrupa por repositorio, no por fichero.
  2. Se excluyen los repositorios del propio organismo (columna github_propios).
  3. Se excluyen las copias: repositorios que contienen el mismo fichero con el mismo
     fragmento que otro repositorio con más estrellas.
  4. Cada reutilización se clasifica con reglas explícitas:
       uso      el código, los datos o el enlace apuntan a datos concretos del portal
       estudio  (OpenAlex) la publicación trata sobre datos abiertos o gobierno abierto
       mencion  solo se cita el portal (portada, noticias, listados de APIs...)
       dudoso   las reglas no bastan; se revisa después
"""

import collections
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

CODE_EXT = set("py ipynb js mjs cjs ts tsx jsx vue svelte r rmd qmd java kt go rb php cs swift scala "
               "jl sh bash zsh ps1 sql m dart rs c cc cpp h hpp ex exs pl lua groovy gradle".split())
DATA_EXT = set("csv tsv json jsonl ndjson geojson topojson xml ttl rdf nt nq jsonld yaml yml sparql "
               "owl n3 kml gpx xlsx xls parquet".split())
DOC_EXT = set("md markdown txt rst html htm tex adoc org bib".split())

IDIOMAS = {"es", "en", "ca", "eu", "gl", "va", "val", "cas", "eus", "cat"}
PORTADAS = {"", "portal", "inicio", "portada", "hasiera", "home", "index.html", "index.htm", "web",
            "centrodedescargas/inicio", "centrodescargas/home", "portal/site/egob", "portal.html",
            "opendata", "datos-abiertos", "dadesobertes", "sede"}
SECCIONES_NO_DATOS = {"noticia", "noticias", "blog", "empresas", "aplicaciones", "evento", "eventos",
                      "documentacion", "tecnologia", "sobre-nosotros", "about", "contacto", "aviso-legal",
                      "entrevistas", "informes", "iniciativas", "desafios", "sectores", "encuentros-aporta",
                      "faq", "ayuda", "help", "legal", "privacidad", "accesibilidad", "user", "usuario",
                      "newsletter", "boletin", "que-hacemos", "conocimiento", "actualidad"}
LISTADO = re.compile(r"awesome|public[-_ ]?apis|apis?[-_ ](list|collection|directory)|free[-_ ]?apis|"
                     r"bookmarks|curated|lista[-_ ]de|recursos|resources", re.I)
# En el título basta con que hable de datos abiertos; en el resumen se exige que sea el
# objeto de estudio, porque los trabajos que usan datos también escriben "open data".
ESTUDIO_TITULO = re.compile(r"open (government )?data|datos abiertos|dades obertes|datu irekiak|open government|"
                            r"gobierno abierto|transparen|reutiliza|data reuse|data portal|portal de datos|"
                            r"data governance|gobernanza del dato|interoperab|\bdcat\b|linked data|datos enlazados", re.I)
ESTUDIO_RESUMEN = re.compile(r"open government|gobierno abierto|transparency portal|portal de transparencia|"
                             r"data governance|gobernanza del dato|open data (portals?|polic\w+|initiatives?|ecosystems?|"
                             r"impact|maturity|reuse|quality|publication)|(portales?|polític\w+|iniciativas?|"
                             r"ecosistemas?|impacto|madurez|reutilización|calidad|publicación) de (los )?datos abiertos", re.I)


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def read_jsonl(path):
    return [json.loads(l) for l in path.open()] if path.exists() else []


def tipo_enlace(url, term):
    """Devuelve 'dato', 'portada' o 'seccion' según a qué parte del portal apunta el enlace."""
    i = url.find(term)
    if i < 0:
        return "portada"
    resto = url[i + len(term):]
    partes = urlsplit("http://x" + (resto if resto.startswith("/") else "/" + resto))
    segs = [s for s in partes.path.split("/") if s]
    while segs and segs[0].lower() in IDIOMAS:
        segs = segs[1:]
    if not segs and not partes.query:
        return "portada"
    if segs and segs[0].lower() in SECCIONES_NO_DATOS:
        return "seccion"
    if "/".join(segs).lower() in PORTADAS and not partes.query:
        return "portada"
    return "dato"


def urls_con(texto, term):
    return re.findall(r"[\w.:/-]*" + re.escape(term) + r"[^\s\"'<>)\]},`|]*", texto or "")


# --- GitHub -----------------------------------------------------------------

GQL_CAMPOS = """nameWithOwner stargazerCount forkCount description createdAt pushedAt isFork isMirror
isArchived homepageUrl primaryLanguage { name } owner { __typename login }
repositoryTopics(first: 10) { nodes { topic { name } } }"""


CACHE_META = ROOT / "data" / "cache" / "github_meta.json"


def metadatos_repos(nombres, token):
    cache = json.loads(CACHE_META.read_text()) if CACHE_META.exists() else {}
    meta = {n: cache[n] for n in nombres if n in cache}
    nombres = sorted(n for n in nombres if n not in cache)
    for i in range(0, len(nombres), 50):
        lote = nombres[i:i + 50]
        partes = []
        for j, n in enumerate(lote):
            owner, name = n.split("/", 1)
            partes.append(f'r{j}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {GQL_CAMPOS} }}')
        q = "query { " + " ".join(partes) + " }"
        r = requests.post("https://api.github.com/graphql", json={"query": q},
                          headers={"Authorization": f"Bearer {token}"}, timeout=90)
        r.raise_for_status()
        data = r.json().get("data") or {}
        for j, n in enumerate(lote):
            d = data.get(f"r{j}")
            if d:
                meta[n] = {
                    "estrellas": d["stargazerCount"], "forks": d["forkCount"], "descripcion": d["description"],
                    "creado": d["createdAt"], "actualizado": d["pushedAt"], "es_fork": d["isFork"],
                    "es_espejo": d["isMirror"], "archivado": d["isArchived"], "web": d["homepageUrl"],
                    "lenguaje": (d["primaryLanguage"] or {}).get("name"),
                    "tipo_propietario": d["owner"]["__typename"],
                    "temas": [t["topic"]["name"] for t in d["repositoryTopics"]["nodes"]],
                }
        print(f"    metadatos {min(i + 50, len(nombres))}/{len(nombres)}")
    if nombres:
        CACHE_META.parent.mkdir(parents=True, exist_ok=True)
        cache.update({n: meta[n] for n in nombres if n in meta})
        CACHE_META.write_text(json.dumps(cache, ensure_ascii=False))
    return meta


def clasificar_fichero(f):
    nombre = f["fichero"].rsplit("/", 1)[-1].lower()
    ext = nombre.rsplit(".", 1)[-1] if "." in nombre else ""
    enlaces = [tipo_enlace(u, f["termino"]) for frag in f["fragmentos"] for u in urls_con(frag, f["termino"])]
    if ext in CODE_EXT:
        return "uso", f"código ({ext})"
    if ext in DATA_EXT:
        return "uso", f"datos o metadatos ({ext})"
    if ext in DOC_EXT or nombre in {"readme", "license", "notice"}:
        if "dato" in enlaces:
            return "uso", "documentación con enlace a datos concretos"
        return "mencion", "documentación que solo cita el portal"
    return "dudoso", f"tipo de fichero no reconocido ({ext or nombre})"


def consolidar_github(portal, propios, token):
    ficheros = read_jsonl(RAW / "github" / f"{portal}.jsonl")
    excluidos, repos = [], collections.defaultdict(list)
    for f in ficheros:
        if f["propietario"].lower() in propios:
            continue
        repos[f["repo"]].append(f)
    for r in {f["repo"] for f in ficheros if f["propietario"].lower() in propios}:
        excluidos.append({"portal": portal, "fuente": "github", "id": r, "motivo": "repositorio del propio organismo"})

    meta = metadatos_repos(repos.keys(), token) if repos else {}

    # Copias: mismo fichero y mismo fragmento en repositorios de distintos propietarios.
    # Se compara el final de la ruta porque las copias suelen ir dentro de otra carpeta.
    firmas = collections.defaultdict(set)
    for repo, fs in repos.items():
        for f in fs:
            frag = re.sub(r"\s+", " ", (f["fragmentos"] or [""])[0]).strip()
            if frag:
                firmas[("/".join(f["fichero"].split("/")[-3:]), frag)].add(repo)
    original_de = {}
    for (_, _), grupo in firmas.items():
        if len({g.split("/")[0] for g in grupo}) < 2:
            continue
        orden = sorted(grupo, key=lambda g: (-(meta.get(g) or {}).get("estrellas", 0),
                                             (meta.get(g) or {}).get("creado") or "9999"))
        for g in orden[1:]:
            original_de.setdefault(g, collections.Counter())[orden[0]] += 1

    salida = []
    for repo, fs in repos.items():
        m = meta.get(repo) or {}
        copiados = sum(original_de.get(repo, {}).values())
        if copiados and copiados >= len(fs):
            orig = original_de[repo].most_common(1)[0][0]
            excluidos.append({"portal": portal, "fuente": "github", "id": repo, "motivo": f"copia de {orig}"})
            continue
        if m.get("es_fork") or m.get("es_espejo"):
            excluidos.append({"portal": portal, "fuente": "github", "id": repo, "motivo": "fork o espejo"})
            continue
        clases = [clasificar_fichero(f) for f in fs]
        texto_repo = f"{repo} {m.get('descripcion') or ''} {' '.join(m.get('temas', []))}"
        if LISTADO.search(texto_repo) and not any(c[1].startswith("código") for c in clases):
            clasif, motivo = "mencion", "listado o recopilatorio de recursos"
        elif any(c[0] == "uso" for c in clases):
            clasif, motivo = "uso", next(c[1] for c in clases if c[0] == "uso")
        elif any(c[0] == "dudoso" for c in clases):
            clasif, motivo = "dudoso", next(c[1] for c in clases if c[0] == "dudoso")
        else:
            clasif, motivo = "mencion", clases[0][1]
        salida.append({
            "portal": portal, "fuente": "github", "id": repo, "nombre": repo,
            "url": f"https://github.com/{repo}", "clasificacion": clasif, "motivo": motivo,
            "propietario": fs[0]["propietario"],
            "tipo_propietario": m.get("tipo_propietario") or fs[0]["tipo_propietario"],
            "n_ficheros": len(fs), "ficheros": [f["fichero"] for f in fs][:20], **m,
        })
    return salida, excluidos


# --- OpenAlex ---------------------------------------------------------------

CACHE_PDF = ROOT / "data" / "cache" / "pdf_contexto"


def contexto_pdf(wid, terminos):
    """Frases del PDF donde se cita el portal (ver pipeline/fulltext.py)."""
    f = CACHE_PDF / f"{wid.rsplit('/', 1)[-1]}.json"
    if not f.exists():
        return "pendiente", []
    d = json.loads(f.read_text())
    return d["estado"], [fr for t in terminos for fr in d["fragmentos"].get(t, [])][:3]


def consolidar_openalex(portal, terminos):
    por_id = {}
    for w in read_jsonl(RAW / "openalex" / f"{portal}.jsonl"):
        por_id.setdefault(w["id"], w)
    salida = []
    for w in por_id.values():
        estado_pdf, citas = contexto_pdf(w["id"], terminos)
        if ESTUDIO_TITULO.search(w.get("titulo") or "") or ESTUDIO_RESUMEN.search(w.get("resumen") or ""):
            clasif, motivo = "estudio", "trata sobre datos abiertos, transparencia o gobierno del dato"
        elif w.get("resumen"):
            clasif, motivo = "uso", "cita el portal en el texto y no trata sobre datos abiertos"
        else:
            clasif, motivo = "dudoso", "sin resumen para distinguir uso de estudio"
        salida.append({
            "portal": portal, "fuente": "openalex", "id": w["id"], "nombre": w.get("titulo"),
            "url": w.get("doi") or w["id"], "clasificacion": clasif, "motivo": motivo,
            **{k: w.get(k) for k in ("anio", "tipo", "citas", "revista", "tema", "campo", "instituciones", "paises")},
            "estado_pdf": estado_pdf, "citas_en_texto": citas,
        })
    return salida


# --- Wikipedia --------------------------------------------------------------

CACHE_WIKI = ROOT / "data" / "cache" / "wikitext"
ENLACES_EXTERNOS = re.compile(r"enlaces externos|external links|enllaços externs|ligazóns externas|kanpo estekak", re.I)
# Plantillas y palabras que indican que el enlace es la fuente de unos datos concretos
CONTEXTO_DATOS = re.compile(r"weather ?box|climate chart|tabla clim|clima|climat|temperatur|precipitaci|"
                            r"poblaci|population|habitantes|inhabitants|censo|census|padr[óo]n|estad[íi]stic|"
                            r"statistic|meteorol|superficie|\barea\b|coordenadas|coordinates|barrio|distrito|neighbou?rhood", re.I)
# Parámetros típicos de tablas de clima o población (Weather box, Tabla clima…)
TABLA_DATOS = re.compile(r"precipitation mm|percentsun|_hum\s*=|_prec\s*=|_tmax\s*=|record high|"
                         r"\|\s*(source|fuente|font|iturria)\s*\d?\s*=", re.I)


def wikitextos(lang, pageids):
    CACHE_WIKI.mkdir(parents=True, exist_ok=True)
    textos, faltan = {}, []
    for pid in pageids:
        f = CACHE_WIKI / f"{lang}_{pid}.txt"
        if f.exists():
            textos[pid] = f.read_text()
        else:
            faltan.append(pid)
    for i in range(0, len(faltan), 20):
        lote = faltan[i:i + 20]
        for intento in range(5):
            r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", timeout=90,
                             headers={"User-Agent": "HuellaDelDato/0.1 (proyecto Premio ASEDIE 2026)"},
                             params={"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                                     "pageids": "|".join(map(str, lote)), "format": "json", "formatversion": 2,
                                     "maxlag": 5})
            if r.status_code != 429:
                break
            time.sleep(int(r.headers.get("Retry-After", 0)) or 15 * (intento + 1))
        r.raise_for_status()
        time.sleep(1)
        for page in r.json()["query"]["pages"]:
            revs = page.get("revisions") or []
            texto = revs[0]["slots"]["main"]["content"] if revs else ""
            textos[page["pageid"]] = texto
            (CACHE_WIKI / f"{lang}_{page['pageid']}.txt").write_text(texto)
    return textos


def contexto_enlace(texto, url, term):
    """Sección y fragmento de wikitexto alrededor del enlace (sin la propia URL)."""
    sin_protocolo = re.sub(r"^https?://", "", url)
    i = texto.find(sin_protocolo)
    if i < 0:
        i = texto.find(term)
    if i < 0:
        return "", ""
    secciones = list(re.finditer(r"^==+\s*(.*?)\s*==+\s*$", texto[:i], re.M))
    seccion = secciones[-1].group(1) if secciones else ""
    # Lo que va detrás de la URL (título de la referencia) es lo que más informa.
    frag = texto[max(0, i - 200):i + len(sin_protocolo) + 300]
    frag = re.sub(r"https?://[^\s|\]}<]+", " ", frag)
    return seccion, frag


def consolidar_wikipedia(portal):
    articulos = collections.defaultdict(list)
    for e in read_jsonl(RAW / "wikipedia" / f"{portal}.jsonl"):
        articulos[(e["idioma"], e["articulo"])].append(e)
    textos = {}
    for lang in {k[0] for k in articulos}:
        pids = {e["pageid"] for (l, _), es in articulos.items() if l == lang for e in es}
        textos[lang] = wikitextos(lang, pids)

    salida = []
    for (lang, titulo), es in articulos.items():
        texto = textos[lang].get(es[0]["pageid"], "")
        clasif, motivo, contexto = "mencion", "enlaza a la portada o a secciones informativas", ""
        for e in es:
            tipo = tipo_enlace(e["url_citada"], e["termino"])
            seccion, frag = contexto_enlace(texto, e["url_citada"], e["termino"])
            contexto = contexto or frag
            if ENLACES_EXTERNOS.search(seccion) and tipo != "dato":
                continue
            if tipo == "dato":
                clasif, motivo, contexto = "uso", "enlaza a datos concretos del portal como fuente", frag
                break
            if TABLA_DATOS.search(frag):
                clasif, motivo, contexto = "uso", "fuente de una tabla de datos del artículo", frag
                break
            if "<ref" in frag.lower() or "{{cita" in frag.lower() or "{{cite" in frag.lower():
                if CONTEXTO_DATOS.search(frag):
                    clasif, motivo, contexto = "uso", "cita el portal como fuente de datos del artículo", frag
                    break
        salida.append({
            "portal": portal, "fuente": "wikipedia", "id": f"{lang}:{titulo}", "nombre": titulo,
            "url": f"https://{lang}.wikipedia.org/wiki/{titulo.replace(' ', '_')}",
            "clasificacion": clasif, "motivo": motivo, "idioma": lang,
            "enlaces": sorted({e["url_citada"] for e in es})[:10],
            "contexto": re.sub(r"\s+", " ", contexto)[:500],
        })
    return salida


def main():
    token = load_env()["GITHUB_TOKEN"]
    portales = list(csv.DictReader((ROOT / "data" / "portales.csv").open()))
    if len(sys.argv) > 1:
        portales = [p for p in portales if p["id"] in sys.argv[1:]]

    OUT.mkdir(parents=True, exist_ok=True)
    todas, excluidos, resumen = [], [], {}
    for p in portales:
        print(p["id"])
        propios = {x.lower() for x in p["github_propios"].split("|") if x}
        gh, exc = consolidar_github(p["id"], propios, token)
        filas = gh + consolidar_openalex(p["id"], p["terminos_busqueda"].split("|")) + consolidar_wikipedia(p["id"])
        todas += filas
        excluidos += exc
        resumen[p["id"]] = {
            "nombre": p["nombre"],
            "fuentes": {f: dict(collections.Counter(x["clasificacion"] for x in filas if x["fuente"] == f))
                        for f in ("github", "openalex", "wikipedia")},
            "excluidos": dict(collections.Counter(e["motivo"].split(" de ")[0] for e in exc)),
        }

    with (OUT / "reutilizaciones.jsonl").open("w") as f:
        for x in todas:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with (OUT / "excluidos.jsonl").open("w") as f:
        for x in excluidos:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "resumen_portales.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
