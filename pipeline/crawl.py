"""Rastreo de reutilizaciones de portales de datos abiertos.

Busca los términos de cada portal (data/portales.csv) en tres fuentes y guarda
los resultados en bruto en data/raw/<fuente>/<portal>.jsonl:

  - openalex:  publicaciones científicas que mencionan el término en su texto completo
  - wikipedia: artículos que enlazan al término (es, ca, gl, eu, en)
  - github:    ficheros de código que contienen el término (requiere GITHUB_TOKEN en .env)

Uso:
  python3 pipeline/crawl.py                     # todos los portales
  python3 pipeline/crawl.py datosgob aemet      # solo esos portales
  python3 pipeline/crawl.py --fuentes github,wikipedia aemet
"""

import argparse
import csv
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PORTALES = ROOT / "data" / "portales.csv"
RAW = ROOT / "data" / "raw"
UA = "HuellaDelDato/0.1 (proyecto Premio ASEDIE 2026)"
WIKI_LANGS = ["es", "ca", "gl", "eu", "en"]

session = requests.Session()
session.headers["User-Agent"] = UA
MAX_ESPERA = 300  # segundos


def load_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get(url, params=None, headers=None, retries=8):
    for intento in range(retries):
        try:
            r = session.get(url, params=params, headers=headers, timeout=60)
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"    error de red ({type(e).__name__}), reintento en {10 * (intento + 1)}s")
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429, 502, 503):
            espera = int(r.headers.get("Retry-After", 0)) or 20 * (intento + 1)
            reset = r.headers.get("X-RateLimit-Reset")
            if r.headers.get("X-RateLimit-Remaining") == "0" and reset:
                espera = max(espera, int(reset) - int(time.time()) + 2)
            espera = min(espera, MAX_ESPERA)  # nunca esperar horas por una cabecera
            print(f"    {r.status_code}, reintento en {espera}s")
            time.sleep(espera)
            continue
        r.raise_for_status()
    raise RuntimeError(f"Sin respuesta tras {retries} intentos: {url}")


# --- OpenAlex ---------------------------------------------------------------

def abstract(inverted):
    if not inverted:
        return None
    pos = {i: palabra for palabra, idx in inverted.items() for i in idx}
    return " ".join(pos[i] for i in sorted(pos))

CONTACTO = load_env().get("CONTACTO_EMAIL")  # OpenAlex da prioridad a quien se identifica


def openalex(term):
    campos = ("id,doi,display_name,publication_year,type,cited_by_count,authorships,"
              "primary_location,primary_topic,abstract_inverted_index")
    cursor, out = "*", []
    while cursor:
        params = {"filter": f'fulltext.search:"{term}"', "per-page": 200,
                  "cursor": cursor, "select": campos}
        if CONTACTO:
            params["mailto"] = CONTACTO
        d = get("https://api.openalex.org/works", params)
        for w in d["results"]:
            src = (w.get("primary_location") or {}).get("source") or {}
            out.append({
                "id": w["id"], "doi": w.get("doi"), "titulo": w.get("display_name"),
                "anio": w.get("publication_year"), "tipo": w.get("type"),
                "citas": w.get("cited_by_count"), "revista": src.get("display_name"),
                "tema": (w.get("primary_topic") or {}).get("display_name"),
                "campo": ((w.get("primary_topic") or {}).get("field") or {}).get("display_name"),
                "instituciones": sorted({i["display_name"] for a in w.get("authorships", [])
                                         for i in a.get("institutions", [])}),
                "paises": sorted({c for a in w.get("authorships", []) for c in a.get("countries", [])}),
                "resumen": abstract(w.get("abstract_inverted_index")),
            })
        cursor = d["meta"].get("next_cursor") if d["results"] else None
    return out


# --- Wikipedia --------------------------------------------------------------

MAX_WIKI = 40_000  # tope por término (el INE aparece en decenas de miles de artículos)


def wikipedia(term):
    out = []
    for lang in WIKI_LANGS:
        params = {"action": "query", "list": "exturlusage", "euquery": term,
                  "eunamespace": 0, "eulimit": 500, "format": "json"}
        while True:
            d = get(f"https://{lang}.wikipedia.org/w/api.php", params)
            for p in d["query"]["exturlusage"]:
                out.append({"idioma": lang, "articulo": p["title"], "pageid": p["pageid"], "url_citada": p["url"]})
            if "continue" not in d or len(out) >= MAX_WIKI:
                break
            params.update(d["continue"])
    return out


# --- GitHub -----------------------------------------------------------------

GITHUB_MAX_SIZE = 400_000  # GitHub solo indexa ficheros de menos de 384 KB


def github_search(term, token, page, lo, hi):
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.text-match+json"}
    d = get("https://api.github.com/search/code",
            {"q": f'"{term}" size:{lo}..{hi}', "per_page": 100, "page": page}, h)
    time.sleep(8)  # límite de 10 búsquedas de código por minuto (con margen)
    return d


MAX_FICHEROS = 4000  # tope por término: hay términos con decenas de miles de ficheros


def github(term, token, lo=0, hi=GITHUB_MAX_SIZE, acumulado=None):
    # Cada consulta devuelve como máximo 1.000 resultados, así que se parte por
    # tamaño de fichero hasta que cada tramo quede por debajo de ese tope. Con
    # términos enormes se para al llegar al tope y se analiza esa muestra.
    acumulado = [0] if acumulado is None else acumulado
    d = github_search(term, token, 1, lo, hi)
    total = d["total_count"]
    if total > 1000 and hi - lo > 1:
        mid = (lo + hi) // 2
        a, _ = github(term, token, lo, mid, acumulado)
        if acumulado[0] >= MAX_FICHEROS:
            print(f"    tope de {MAX_FICHEROS} ficheros alcanzado (el término tiene {total})")
            return a, total
        b, _ = github(term, token, mid + 1, hi, acumulado)
        return a + b, total
    print(f"    tramo {lo}..{hi}: {total}")
    out, page = [], 1
    while True:
        for it in d["items"]:
            repo = it["repository"]
            out.append({
                "repo": repo["full_name"], "propietario": repo["owner"]["login"],
                "tipo_propietario": repo["owner"]["type"], "fork": repo["fork"],
                "descripcion": repo.get("description"), "fichero": it["path"], "url": it["html_url"],
                "fragmentos": [m["fragment"][:400] for m in it.get("text_matches", [])][:3],
                "incompleto": d.get("incomplete_results", False),
            })
        acumulado[0] += len(d["items"])
        if len(d["items"]) < 100 or page == 10 or acumulado[0] >= MAX_FICHEROS:
            break
        page += 1
        d = github_search(term, token, page, lo, hi)
    return out, total


def main():
    fuentes_validas = ["openalex", "wikipedia", "github"]
    ap = argparse.ArgumentParser()
    ap.add_argument("portales", nargs="*")
    ap.add_argument("--saltar-existentes", action="store_true",
                    help="no repite los portales cuyos ficheros ya existen")
    ap.add_argument("--fuentes", default=",".join(fuentes_validas),
                    help="separadas por comas, p. ej. --fuentes github,wikipedia")
    args = ap.parse_args()
    args.fuentes = args.fuentes.split(",")
    if set(args.fuentes) - set(fuentes_validas):
        ap.error(f"fuentes desconocidas: {set(args.fuentes) - set(fuentes_validas)}")

    token = load_env().get("GITHUB_TOKEN")
    filas = list(csv.DictReader(PORTALES.open()))
    if set(args.portales) - {f["id"] for f in filas}:
        ap.error(f"portales desconocidos: {set(args.portales) - {f['id'] for f in filas}}")
    if args.portales:
        filas = [f for f in filas if f["id"] in args.portales]
    if args.saltar_existentes:
        filas = [f for f in filas
                 if any(not (RAW / fu / f"{f['id']}.jsonl").exists() for fu in args.fuentes)]
        print(f"pendientes: {len(filas)} portales")

    resumen = []
    for f in filas:
        for fuente in args.fuentes:
            if args.saltar_existentes and (RAW / fuente / f"{f['id']}.jsonl").exists():
                continue
            registros, totales = [], {}
            try:
                for term in f["terminos_busqueda"].split("|"):
                    print(f"{f['id']:<14} {fuente:<10} {term}")
                    if fuente == "openalex":
                        res = openalex(term)
                    elif fuente == "wikipedia":
                        res = wikipedia(term)
                    else:
                        res, totales[term] = github(term, token)
                    for r in res:
                        r["termino"] = term
                    registros += res
            except Exception as e:
                # Un portal que falla no debe tumbar el rastreo completo.
                print(f"    FALLO en {f['id']}/{fuente}: {str(e)[:200]} (se reintentará en otra ejecución)")
                continue
            if fuente == "github":
                # un mismo fichero puede salir con dos términos del portal
                vistos = set()
                registros = [r for r in registros if r["url"] not in vistos and not vistos.add(r["url"])]
            destino = RAW / fuente / f"{f['id']}.jsonl"
            destino.parent.mkdir(parents=True, exist_ok=True)
            with destino.open("w") as out:
                for r in registros:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
            resumen.append({"portal": f["id"], "fuente": fuente, "registros": len(registros),
                            "total_github": totales or None})
            print(f"    -> {len(registros)} registros")

    (RAW / f"resumen_{'_'.join(args.fuentes)}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
