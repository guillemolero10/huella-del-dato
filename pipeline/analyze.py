"""Calcula los resultados finales a partir de la clasificación de la IA.

En los grupos (portal + fuente) que se clasificaron por muestra, la proporción de
cada clase se extrapola al total con un intervalo de confianza del 95% (Wilson),
así que las cifras estimadas se publican siempre con su margen.

Escribe data/processed/resultados.json
"""

import collections
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"


def wilson(exitos, n, z=1.96):
    """Intervalo de confianza del 95% para una proporción."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = exitos / n
    d = 1 + z ** 2 / n
    centro = (p + z ** 2 / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return p, max(0.0, centro - margen), min(1.0, centro + margen)


def main():
    portales = {p["id"]: p for p in csv.DictReader((ROOT / "data" / "portales.csv").open())}
    items = {f"{x['portal']}|{x['fuente']}|{x['id']}": x
             for x in map(json.loads, (PROC / "reutilizaciones.jsonl").open())}
    ia = {}
    for l in (PROC / "ia" / "sonnet.jsonl").open():
        r = json.loads(l)
        ia[r["clave"]] = r

    grupos = collections.defaultdict(list)
    for k, x in items.items():
        grupos[(x["portal"], x["fuente"])].append(k)

    resultados = {"portales": {}, "global": {}}
    for (portal, fuente), claves in sorted(grupos.items()):
        # En publicaciones solo se puede juzgar el uso cuando tenemos la frase de la
        # cita sacada del PDF; el resto se extrapola desde esas, porque la muestra de
        # PDF descargados fue aleatoria.
        if fuente == "openalex":
            claves_juzgables = [k for k in claves if items[k].get("citas_en_texto")]
        else:
            claves_juzgables = claves
        clasificados = [ia[k] for k in claves_juzgables if k in ia]
        clasificados = [c for c in clasificados if c["clase"] != "cita"]
        conteo = collections.Counter(c["clase"] for c in clasificados)
        n, total = len(clasificados), len(claves)
        d = resultados["portales"].setdefault(portal, {"nombre": portales[portal]["nombre"],
                                                       "ambito": portales[portal]["ambito"],
                                                       "territorio": portales[portal]["territorio"],
                                                       "url": portales[portal]["url_portal"],
                                                       "fuentes": {}})
        p, lo, hi = wilson(conteo.get("uso", 0), n)
        d["fuentes"][fuente] = {
            "encontrados": total, "verificables": len(claves_juzgables), "clasificados": n,
            "muestreado": n < total, "clases": dict(conteo),
            "uso_estimado": round(p * total),
            "uso_min": round(lo * total), "uso_max": round(hi * total),
        }

    # Totales por portal y ranking
    for portal, d in resultados["portales"].items():
        d["encontrados"] = sum(f["encontrados"] for f in d["fuentes"].values())
        d["uso_estimado"] = sum(f["uso_estimado"] for f in d["fuentes"].values())
        d["uso_min"] = sum(f["uso_min"] for f in d["fuentes"].values())
        d["uso_max"] = sum(f["uso_max"] for f in d["fuentes"].values())

    clasificados = [(k, ia[k]) for k in items if k in ia]
    g = resultados["global"]
    g["portales"] = len(resultados["portales"])
    g["encontrados"] = len(items)
    g["clasificados"] = len(clasificados)
    g["clases"] = dict(collections.Counter(r["clase"] for _, r in clasificados))
    g["sectores"] = dict(collections.Counter(r["sector"] for _, r in clasificados if r["clase"] == "uso"))
    g["actores"] = dict(collections.Counter(r["actor"] for _, r in clasificados if r["clase"] == "uso"))
    g["uso_estimado_total"] = sum(d["uso_estimado"] for d in resultados["portales"].values())
    g["ranking"] = sorted(((d["uso_estimado"], p) for p, d in resultados["portales"].items()), reverse=True)

    # Portales sin ninguna reutilización de uso detectada
    g["sin_uso_detectado"] = [p for p, d in resultados["portales"].items() if d["uso_estimado"] == 0]

    # Ejemplos destacados: repositorios con más estrellas cuyo uso es real
    ejemplos = []
    for k, r in clasificados:
        x = items[k]
        if r["clase"] == "uso" and x["fuente"] == "github" and (x.get("estrellas") or 0) >= 100:
            ejemplos.append({"portal": x["portal"], "nombre": x["nombre"], "url": x["url"],
                             "estrellas": x["estrellas"], "descripcion": x.get("descripcion"),
                             "motivo": r["motivo"], "sector": r["sector"]})
    ejemplos.sort(key=lambda e: -e["estrellas"])
    g["ejemplos_github"] = ejemplos[:40]

    # Años de las publicaciones que usan datos
    anios = collections.Counter()
    for k, r in clasificados:
        x = items[k]
        if x["fuente"] == "openalex" and r["clase"] == "uso" and x.get("anio"):
            anios[x["anio"]] += 1
    g["anios_publicaciones"] = dict(sorted(anios.items()))

    (PROC / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in g.items() if k not in ("ejemplos_github",)},
                     ensure_ascii=False, indent=1)[:2500])


if __name__ == "__main__":
    main()
