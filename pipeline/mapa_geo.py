"""Prepara las siluetas de las comunidades autónomas para el mapa de la web.

Parte de las provincias de Natural Earth (dominio público), las une por comunidad,
las simplifica y las proyecta a coordenadas SVG, con Canarias en un recuadro.
Solo hace falta ejecutarlo una vez; el resultado queda en data/geo/ccaa.json.

Requiere shapely (pip install shapely), solo para este paso.
"""

import json
import math
from pathlib import Path

from shapely.geometry import shape, MultiPolygon, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
GEO = ROOT / "data" / "geo"

REGION_A_PORTAL = {
    "Andalucía": "andalucia", "Aragón": "aragon", "Asturias": "asturias", "Cantabria": "cantabria",
    "Castilla y León": "cyl", "Castilla-La Mancha": "clm", "Cataluña": "cataluna",
    "Extremadura": "extremadura", "Foral de Navarra": "navarra", "Galicia": "galicia",
    "Islas Baleares": "baleares", "La Rioja": "larioja", "Madrid": "cmadrid", "Murcia": "murcia",
    "País Vasco": "euskadi", "Valenciana": "cvalenciana", "Canary Is.": "canarias",
    "Ceuta": "ceuta", "Melilla": "melilla",
}
ANCHO = 800
COS = math.cos(math.radians(40))


def main():
    fc = json.loads((GEO / "natural_earth_provincias.geojson").read_text())
    grupos = {}
    for f in fc["features"]:
        pid = REGION_A_PORTAL[f["properties"]["region"]]
        grupos.setdefault(pid, []).append(shape(f["geometry"]).buffer(0))
    geoms = {pid: unary_union(g).simplify(0.012, preserve_topology=True) for pid, g in grupos.items()}

    # Canarias se desplaza a un recuadro abajo a la izquierda, como en los mapas oficiales.
    from shapely.affinity import translate
    geoms["canarias"] = translate(geoms["canarias"], xoff=8.2, yoff=6.1)

    def proy(lon, lat):
        return lon * COS, -lat
    cb = geoms["canarias"].bounds
    marco = Polygon([(cb[0] - 0.4, cb[1] - 0.4), (cb[2] + 0.4, cb[1] - 0.4),
                     (cb[2] + 0.4, cb[3] + 0.4), (cb[0] - 0.4, cb[3] + 0.4)])
    minx, miny, maxx, maxy = unary_union(list(geoms.values()) + [marco]).bounds
    x0, y0 = proy(minx, maxy)
    x1, y1 = proy(maxx, miny)
    esc = (ANCHO - 20) / (x1 - x0)
    alto = round((y1 - y0) * esc + 20)

    def xy(lon, lat):
        x, y = proy(lon, lat)
        return (x - x0) * esc + 10, (y - y0) * esc + 10

    def anillo(coords):
        pts = [xy(*c[:2]) for c in coords]
        return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"

    salida = {"ancho": ANCHO, "alto": alto, "regiones": {}}
    for pid, g in geoms.items():
        polis = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
        polis = [p for p in polis if p.area > 0.0004]  # fuera los islotes diminutos
        d = "".join(anillo(p.exterior.coords) + "".join(anillo(i.coords) for i in p.interiors)
                    for p in polis)
        c = max(polis, key=lambda p: p.area).representative_point()
        cx, cy = xy(c.x, c.y)
        salida["regiones"][pid] = {"d": d, "cx": round(cx, 1), "cy": round(cy, 1)}

    # Marco del recuadro de Canarias
    ax, ay = xy(cb[0] - 0.4, cb[3] + 0.4)
    bx, by = xy(cb[2] + 0.4, cb[1] - 0.4)
    salida["recuadro_canarias"] = [round(ax, 1), round(ay, 1), round(bx - ax, 1), round(by - ay, 1)]
    (GEO / "ccaa.json").write_text(json.dumps(salida, ensure_ascii=False))
    print("ccaa.json:", len(salida["regiones"]), "regiones,", (GEO / "ccaa.json").stat().st_size // 1024, "KB,",
          f"{ANCHO}x{alto}")


if __name__ == "__main__":
    main()
