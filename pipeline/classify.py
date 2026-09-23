"""Clasifica cada reutilización con Claude (vía Claude Code, usando la suscripción).

Lee data/processed/reutilizaciones.jsonl y, para cada elemento, pide al modelo:
  clase      uso | estudio | mencion | ruido | cita
  sector     ámbito temático de los datos
  actor      quién reutiliza
  confianza  alta | media | baja
  motivo     explicación breve

Los resultados se guardan en data/processed/ia/<modelo>.jsonl y el proceso se
puede interrumpir y reanudar: los elementos ya clasificados no se repiten.

Uso:
  python3 pipeline/classify.py --modelo haiku                  # todo
  python3 pipeline/classify.py --modelo sonnet --muestra 200   # muestra fija para comparar
"""

import argparse
import collections
import glob
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = PROC / "ia"

CLASES = ["uso", "estudio", "mencion", "ruido", "cita"]
SECTORES = ["clima_medio_ambiente", "movilidad_transporte", "urbanismo_territorio", "salud", "economia_empresa",
            "sector_publico_legal", "educacion_cultura", "sociedad_demografia", "tecnologia_datos", "otros"]
ACTORES = ["investigacion", "empresa", "administracion", "estudiante_particular", "comunidad_open_source",
           "divulgacion"]
CONFIANZAS = ["alta", "media", "baja"]

SISTEMA = ("Eres un analista del ecosistema de datos abiertos en España. Clasificas evidencias de que un "
           "portal de datos públicos aparece en repositorios de código (GitHub), publicaciones científicas "
           "(OpenAlex) o artículos de Wikipedia. Respondes solo con JSON válido, sin texto adicional.")

INSTRUCCIONES = f"""Para cada elemento decide:

- clase:
  - "uso": reutiliza datos del portal: los descarga, consulta su API, los analiza, construye una
    aplicación o producto con ellos, o los cita como fuente de sus resultados, tablas o cifras.
  - "estudio": su tema es el propio ecosistema de datos abiertos (portales, políticas de apertura,
    transparencia, estándares, calidad o gobierno del dato) y cita el portal como objeto de estudio o ejemplo.
  - "mencion": solo nombra o enlaza el portal sin usar sus datos (listas de recursos, materiales de
    curso que enumeran portales, avisos legales, enlaces a la portada o a noticias). También es
    mención declarar prefijos o espacios de nombres RDF del portal, incluirlo en listas de endpoints
    o de portales, o citarlo como fuente fiable sin descargar nada.
  - "ruido": el fragmento demuestra que la coincidencia es accidental o irrelevante (dice que se
    dejó de usar, URL de ejemplo en un test, datos simulados, textos legales copiados). No uses
    "ruido" solo porque falte contexto: en ese caso elige la clase más probable con confianza baja.
  - "cita": solo para publicaciones científicas sin "Cita en el texto": se sabe que citan el
    portal pero no cómo.

- sector (temática de los datos o del trabajo): {", ".join(SECTORES)}
- actor (quién reutiliza): {", ".join(ACTORES)}
  (las publicaciones científicas suelen ser "investigacion"; Wikipedia es "divulgacion")
- confianza: alta, media o baja
- motivo: máximo 15 palabras en español

Criterios por fuente:
- GitHub: código o configuración que llama a la API del portal o descarga conjuntos concretos
  (también para recolectar sus metadatos) es "uso".
- Publicaciones: decide con la "Cita en el texto" (frase real del artículo donde aparece el portal).
- Wikipedia: enlazar la ficha de un conjunto de datos concreto del portal como referencia de datos
  o hechos del artículo es "uso"; enlazar la portada o una noticia es "mencion".

Devuelve exactamente este formato, con un resultado por elemento y los mismos id:
{{"resultados": [{{"id": "i0", "clase": "...", "sector": "...", "actor": "...", "confianza": "...", "motivo": "..."}}]}}

ELEMENTOS:
"""


def claude_bin():
    ruta = shutil.which("claude")
    if ruta:
        return ruta
    candidatos = sorted(glob.glob(os.path.expanduser(
        "~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")))
    if not candidatos:
        raise SystemExit("No encuentro el ejecutable de Claude Code")
    return candidatos[-1]


def clave(x):
    return f"{x['portal']}|{x['fuente']}|{x['id']}"


def recorta(texto, n):
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto if len(texto) <= n else texto[:n] + "…"


def fragmentos_github():
    frags = collections.defaultdict(list)
    for f in sorted((RAW / "github").glob("*.jsonl")):
        portal = f.stem
        for l in f.open():
            r = json.loads(l)
            if len(frags[(portal, r["repo"])]) < 3 and r["fragmentos"]:
                frags[(portal, r["repo"])].append(f"{r['fichero']}: {recorta(r['fragmentos'][0], 280)}")
    return frags


def describir(i, x, portales, frags):
    p = portales[x["portal"]]
    cab = f"### i{i} · portal: {p['nombre']} ({p['terminos_busqueda'].replace('|', ', ')})\n"
    if x["fuente"] == "github":
        lineas = [f"Fuente: repositorio de GitHub {x['nombre']}",
                  f"Descripción: {recorta(x.get('descripcion'), 200) or '(sin descripción)'}",
                  f"Lenguaje: {x.get('lenguaje') or '-'} · estrellas: {x.get('estrellas', '-')} · "
                  f"temas: {', '.join(x.get('temas') or []) or '-'}",
                  f"Ficheros donde aparece ({x['n_ficheros']}): {', '.join(x['ficheros'][:6])}",
                  "Fragmentos:"] + [f"> {fr}" for fr in frags.get((x["portal"], x["nombre"]), [])]
    elif x["fuente"] == "openalex":
        citas = x.get("citas_en_texto") or []
        lineas = [f"Fuente: publicación científica (el texto completo menciona el portal)",
                  f"Título: {x['nombre']}",
                  f"Año: {x.get('anio')} · tipo: {x.get('tipo')} · campo: {x.get('campo') or '-'}",
                  f"Instituciones: {', '.join((x.get('instituciones') or [])[:4]) or '-'}",
                  f"Resumen: {recorta(x.get('resumen'), 500) or '(sin resumen)'}"]
        lineas += ([f"Cita en el texto: > {recorta(c, 600)}" for c in citas[:2]] if citas
                   else ["Cita en el texto: (no disponible, el PDF no es accesible)"])
    else:
        lineas = [f"Fuente: artículo de Wikipedia ({x['idioma']}) «{x['nombre']}»",
                  f"Enlaces al portal: {', '.join(x['enlaces'][:3])}",
                  f"Contexto del enlace: {recorta(x.get('contexto'), 450)}"]
    return cab + "\n".join(lineas)


def resumen_openalex():
    # El resumen no se guarda en reutilizaciones.jsonl; se recupera de los datos en bruto.
    res = {}
    for f in sorted((RAW / "openalex").glob("*.jsonl")):
        for l in f.open():
            r = json.loads(l)
            res.setdefault(r["id"], r.get("resumen"))
    return res


def parse(texto):
    texto = texto.strip()
    texto = re.sub(r"^```(json)?|```$", "", texto, flags=re.M).strip()
    return json.loads(texto[texto.find("{"):texto.rfind("}") + 1])


def valido(r):
    return (r.get("clase") in CLASES and r.get("sector") in SECTORES and r.get("actor") in ACTORES
            and r.get("confianza") in CONFIANZAS)


class LimiteUso(Exception):
    pass


LIMITE = re.compile(r"(usage|session|weekly|opus) limit|rate.?limit|limit reached|hit your\\b[^.]{0,30}\\blimit|quota|overloaded|resets? (at|in|\\d)", re.I)


def llamar(binario, modelo, prompt):
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.run(
            [binario, "-p", "--model", modelo, "--output-format", "json", "--system-prompt", SISTEMA,
             "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"],
            input=prompt, capture_output=True, text=True, cwd=tmp, timeout=900)
    salida = p.stdout.strip()
    try:
        d = json.loads(salida)
    except json.JSONDecodeError:
        msg = f"{salida[:300]} {p.stderr[:300]}"
        if LIMITE.search(msg):
            raise LimiteUso(msg)
        raise RuntimeError(f"salida no JSON: {msg}")
    if d.get("is_error"):
        msg = str(d.get("result", ""))
        if LIMITE.search(msg):
            raise LimiteUso(msg)
        raise RuntimeError(msg[:300])
    return d["result"], [m for m in (d.get("modelUsage") or {}) if modelo in m] or list(d.get("modelUsage") or {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="haiku")
    ap.add_argument("--muestra", type=int, help="muestra fija y estratificada por fuente")
    ap.add_argument("--misma-muestra", help="clasifica solo los elementos de otro fichero de resultados")
    ap.add_argument("--solo-con-cita", action="store_true",
                    help="en publicaciones, clasifica solo las que tienen la frase de la cita "
                         "extraída del PDF (las demás no se pueden juzgar)")
    ap.add_argument("--por-grupo", type=int,
                    help="máximo de elementos por portal y fuente: si hay más, se clasifica una "
                         "muestra aleatoria y el resto se estima con margen de error")
    ap.add_argument("--salida", help="nombre del fichero de resultados (por defecto, el del modelo)")
    ap.add_argument("--lote", type=int, default=40)
    ap.add_argument("--hilos", type=int, default=3)
    args = ap.parse_args()

    import csv
    portales = {p["id"]: p for p in csv.DictReader((ROOT / "data" / "portales.csv").open())}
    items = [json.loads(l) for l in (PROC / "reutilizaciones.jsonl").open()]
    resumenes = resumen_openalex()
    for x in items:
        if x["fuente"] == "openalex":
            x["resumen"] = resumenes.get(x["id"])

    if args.muestra:
        rnd = random.Random(2026)
        cuotas = {"github": 0.5, "openalex": 0.3, "wikipedia": 0.2}
        sel = []
        for fuente, q in cuotas.items():
            grupo = sorted((x for x in items if x["fuente"] == fuente), key=clave)
            sel += rnd.sample(grupo, min(len(grupo), round(args.muestra * q)))
        items = sel

    if args.solo_con_cita:
        items = [x for x in items if x["fuente"] != "openalex" or x.get("citas_en_texto")]
        print(f"{len(items)} elementos tras quedarnos solo con las publicaciones verificables")

    if args.por_grupo:
        rnd = random.Random(2026)
        grupos = collections.defaultdict(list)
        for x in items:
            grupos[(x["portal"], x["fuente"])].append(x)
        sel, muestreados = [], []
        for (portal, fuente), grupo in sorted(grupos.items()):
            grupo.sort(key=clave)
            if len(grupo) > args.por_grupo:
                sel += rnd.sample(grupo, args.por_grupo)
                muestreados.append({"portal": portal, "fuente": fuente, "total": len(grupo),
                                    "muestra": args.por_grupo})
            else:
                sel += grupo
        items = sel
        (OUT / "muestreo.json").parent.mkdir(parents=True, exist_ok=True)
        (OUT / "muestreo.json").write_text(json.dumps(muestreados, ensure_ascii=False, indent=1))
        print(f"{len(items)} elementos a clasificar; {len(muestreados)} grupos muestreados")

    if args.misma_muestra:
        claves = {json.loads(l)["clave"] for l in Path(args.misma_muestra).open()}
        items = [x for x in items if clave(x) in claves]

    OUT.mkdir(parents=True, exist_ok=True)
    destino = OUT / f"{args.salida or args.modelo}.jsonl"
    hechos = {json.loads(l)["clave"] for l in destino.open()} if destino.exists() else set()
    pendientes = [x for x in items if clave(x) not in hechos]
    print(f"{len(items)} elementos, {len(hechos & {clave(x) for x in items})} ya clasificados, "
          f"{len(pendientes)} pendientes")

    frags = fragmentos_github()
    binario = claude_bin()
    lock = threading.Lock()
    lotes = [pendientes[i:i + args.lote] for i in range(0, len(pendientes), args.lote)]
    hechos_n = [0]

    def procesar(lote):
        prompt = INSTRUCCIONES + "\n\n".join(describir(i, x, portales, frags) for i, x in enumerate(lote))
        fallos = 0
        while True:
            try:
                texto, modelos = llamar(binario, args.modelo, prompt)
                res = {r["id"]: r for r in parse(texto)["resultados"] if valido(r)}
                break
            except LimiteUso as e:
                # Se espera sin gastar intentos hasta que el plan renueve su cuota.
                print(f"  límite de uso alcanzado; espero 20 min y reintento ({str(e)[:100]})")
                time.sleep(1200)
            except Exception as e:
                fallos += 1
                print(f"  error en lote (intento {fallos}): {str(e)[:160]}")
                if fallos == 3:
                    print("  lote descartado tras 3 intentos; se reintentará en la próxima ejecución")
                    return
                time.sleep(20)
        with lock, destino.open("a") as f:
            for i, x in enumerate(lote):
                r = res.get(f"i{i}")
                if r and x["fuente"] == "openalex" and not x.get("citas_en_texto"):
                    r["clase"] = "cita"  # sin la frase del artículo no se puede saber cómo lo usa
                elif r and r["clase"] == "cita":
                    r["confianza"] = "baja"
                if r:
                    f.write(json.dumps({"clave": clave(x), "modelo": modelos, **{k: r[k] for k in
                            ("clase", "sector", "actor", "confianza", "motivo")}}, ensure_ascii=False) + "\n")
            hechos_n[0] += len(res)
            print(f"  {hechos_n[0]}/{len(pendientes)} clasificados")

    with ThreadPoolExecutor(args.hilos) as ex:
        list(ex.map(procesar, lotes))


if __name__ == "__main__":
    main()
