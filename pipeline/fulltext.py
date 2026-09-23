"""Extrae de los PDF de acceso abierto la frase donde cada publicación cita el portal.

Para cada publicación de data/raw/openalex/*.jsonl busca en OpenAlex sus PDF de acceso
abierto, los descarga en memoria y guarda solo los fragmentos de texto alrededor de
cada término del portal (no se conservan los PDF).

Resultado en data/cache/pdf_contexto/<id OpenAlex>.json:
  {"estado": "ok" | "sin_pdf" | "no_encontrado", "fragmentos": {termino: [texto, ...]}}

Uso:
  python3 pipeline/fulltext.py                  # todos los portales
  python3 pipeline/fulltext.py datosgob aemet   # solo esos portales
"""

import argparse
import csv
import io
import json
import logging
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pypdf
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crawl import CONTACTO, get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache" / "pdf_contexto"
MAX_BYTES = 40_000_000
MAX_PAGINAS = 400

logging.getLogger("pypdf").setLevel(logging.ERROR)
http = requests.Session()
http.headers["User-Agent"] = "Mozilla/5.0 (Macintosh) HuellaDelDato/0.1 (proyecto Premio ASEDIE 2026)"


def pdfs_de(ids):
    urls = {}
    for i in range(0, len(ids), 50):
        lote = [x.rsplit("/", 1)[-1] for x in ids[i:i + 50]]
        params = {"filter": "openalex_id:" + "|".join(lote), "per-page": 50, "select": "id,locations"}
        if CONTACTO:
            params["mailto"] = CONTACTO
        d = get("https://api.openalex.org/works", params)
        for w in d["results"]:
            vistos = []
            for loc in w.get("locations") or []:
                u = loc.get("pdf_url")
                if u and u not in vistos:
                    vistos.append(u)
            urls[w["id"]] = vistos
    return urls


def texto_pdf(url):
    r = http.get(url, timeout=45, stream=True, allow_redirects=True)
    if r.status_code != 200:
        return None
    datos = b""
    for trozo in r.iter_content(1 << 16):
        datos += trozo
        if len(datos) > MAX_BYTES:
            return None
    if not datos.startswith(b"%PDF"):
        return None
    lector = pypdf.PdfReader(io.BytesIO(datos))
    return "\n".join((p.extract_text() or "") for p in lector.pages[:MAX_PAGINAS])


def fragmentos(texto, terminos):
    # Los PDF parten las URL en varias líneas, así que se busca sin espacios y se
    # recupera la posición original para recortar el fragmento legible.
    compacto, pos = [], []
    for i, ch in enumerate(texto):
        if not ch.isspace():
            compacto.append(ch.lower())
            pos.append(i)
    compacto = "".join(compacto)
    out = {}
    for t in terminos:
        encontrados, desde = [], 0
        while len(encontrados) < 2:
            j = compacto.find(t.lower(), desde)
            if j < 0:
                break
            a, b = pos[j], pos[min(j + len(t) - 1, len(pos) - 1)]
            encontrados.append(re.sub(r"\s+", " ", texto[max(0, a - 350):b + 250]).strip())
            desde = j + len(t) + 400
        if encontrados:
            out[t] = encontrados
    return out


def procesar(args):
    wid, urls, terminos = args
    destino = CACHE / f"{wid.rsplit('/', 1)[-1]}.json"
    if destino.exists():
        return json.loads(destino.read_text())["estado"]
    estado, frags = ("sin_pdf" if not urls else "no_encontrado"), {}
    for u in urls[:3]:
        try:
            texto = texto_pdf(u)
        except Exception:
            texto = None
        if texto and len(texto) > 2000:
            frags = fragmentos(texto, terminos)
            if frags:
                estado = "ok"
                break
    destino.write_text(json.dumps({"estado": estado, "fragmentos": frags}, ensure_ascii=False))
    return estado


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("portales", nargs="*")
    ap.add_argument("--max-por-portal", type=int, default=400,
                    help="muestra aleatoria por portal; en los portales enormes (INE) bajar "
                         "todos los PDF costaría horas y agotaría la cuota de OpenAlex")
    args = ap.parse_args()

    portales = {p["id"]: p for p in csv.DictReader((ROOT / "data" / "portales.csv").open())}
    elegidos = args.portales or list(portales)
    terminos, rnd = {}, random.Random(2026)
    for pid in elegidos:
        f = RAW / "openalex" / f"{pid}.jsonl"
        if not f.exists():
            continue
        ids = sorted({json.loads(l)["id"] for l in f.open()})
        if len(ids) > args.max_por_portal:
            ids = rnd.sample(ids, args.max_por_portal)
            print(f"{pid}: muestra de {args.max_por_portal}")
        for w in ids:
            terminos.setdefault(w, set()).update(portales[pid]["terminos_busqueda"].split("|"))

    CACHE.mkdir(parents=True, exist_ok=True)
    pendientes = [w for w in terminos if not (CACHE / f"{w.rsplit('/', 1)[-1]}.json").exists()]
    print(f"{len(terminos)} publicaciones, {len(pendientes)} pendientes")
    urls = pdfs_de(pendientes)
    tareas = [(w, urls.get(w, []), sorted(terminos[w])) for w in pendientes]
    conteo = {}
    with ThreadPoolExecutor(8) as ex:
        for n, estado in enumerate(ex.map(procesar, tareas), 1):
            conteo[estado] = conteo.get(estado, 0) + 1
            if n % 50 == 0:
                print(f"  {n}/{len(tareas)} {conteo}")
    print("terminado:", conteo)


if __name__ == "__main__":
    main()
