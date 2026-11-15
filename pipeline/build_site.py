"""Genera la web estática de La Huella del Dato en web/.

Todo el HTML, los gráficos (SVG) y los sellos se producen aquí a partir de los datos
ya procesados. La web no depende de ningún servicio externo: la tipografía se sirve
desde la propia web y el poco JavaScript que lleva (buscador, animación de portada y
avisos al pasar el ratón) va incluido en las páginas.
"""

import collections
import csv
import html
import json
import math
import re
import shutil
from pathlib import Path

import classify
from web_estilo import CSS, JS_AVISOS, JS_BUSCADOR, JS_CONSTELACION, JS_COPIAR

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
GEO = ROOT / "data" / "geo"
ASSETS = ROOT / "assets"
WEB = ROOT / "web"
BASE_URL = "https://huella-del-dato.vercel.app"
REPO_URL = "https://github.com/guillemolero10/huella-del-dato"

SECTORES = {
    "clima_medio_ambiente": "Clima y medio ambiente", "movilidad_transporte": "Movilidad y transporte",
    "urbanismo_territorio": "Urbanismo y territorio", "salud": "Salud",
    "economia_empresa": "Economía y empresa", "sector_publico_legal": "Sector público y legal",
    "educacion_cultura": "Educación y cultura", "sociedad_demografia": "Sociedad y demografía",
    "tecnologia_datos": "Tecnología y datos", "otros": "Otros",
}
ACTORES = {
    "investigacion": "Investigación", "empresa": "Empresas", "administracion": "Administración",
    "estudiante_particular": "Estudiantes y particulares",
    "comunidad_open_source": "Comunidad de software libre", "divulgacion": "Divulgación",
}
EN_FUENTE = {"github": "código de GitHub", "openalex": "publicaciones científicas", "wikipedia": "Wikipedia"}
FUENTES = {"github": "Código (GitHub)", "openalex": "Publicaciones científicas", "wikipedia": "Wikipedia"}
CLASES = {"uso": "Uso real", "mencion": "Solo lo menciona", "cita": "Cita sin verificar",
          "estudio": "Estudia el ecosistema", "ruido": "Coincidencia"}
ORDEN_CLASES = ["uso", "mencion", "cita", "estudio", "ruido"]
IDIOMAS = {"es": "en español", "ca": "en catalán", "gl": "en gallego", "eu": "en euskera", "en": "en inglés"}
AMBITOS = {"nacional": "Estatal", "autonomico": "Autonómico", "local": "Municipal"}
CORTO = {"datosgob": "datos.gob.es", "ine": "INE", "ign": "IGN / CNIG", "aemet": "AEMET",
         "catastro": "Catastro", "boe": "BOE y BORME", "placsp": "Contratación", "dgt": "DGT",
         "transparencia": "Transparencia", "universidata": "UniversiDATA", "euskadi": "Open Data Euskadi",
         "cmadrid": "C. de Madrid", "cvalenciana": "C. Valenciana", "baleares": "Baleares", "clm": "C.-La Mancha"}
# Dos casos reales para enseñar cómo decide la IA: uno de uso y otro de mención
EJEMPLOS_IA = ["madrid|wikipedia|en:Las Acacias (Madrid)", "datosgob|github|lightlessdays/The-API-Project"]
CONFIANZA = {"alta": "Alta", "media": "Media", "baja": "Baja"}
# Casos que no se ponen como escaparate en portada (siguen en su ficha y en el buscador):
# un proyecto de vigilancia de personas no representa bien la reutilización de datos públicos.
NO_DESTACAR = {"BigBodyCobain/Shadowbroker"}
DESCARTADOS = 2255  # copias y repositorios del propio organismo, quitados en consolidate.py
E = html.escape

ICONOS = {  # trazos de 24x24, sin relleno
    "rastrea": "<circle cx='10.5' cy='10.5' r='6.5'/><path d='M15.5 15.5 21 21'/>",
    "lee": "<path d='M6 3h9l4 4v14H6z'/><path d='M14 3v5h5'/><path d='M9 12h7M9 15.5h7M9 19h4'/>",
    "decide": "<path d='M12 3v6'/><path d='M12 9 5.5 15.5M12 9l6.5 6.5'/><circle cx='5' cy='18.5' r='2.5' class='relleno-uso'/><circle cx='19' cy='18.5' r='2.5'/>",
    "publica": "<path d='M4 20V10M10 20V4M16 20v-7M22 20H2'/>",
}


def icono(nombre):
    return (f"<svg class='icono' viewBox='0 0 24 24' aria-hidden='true' fill='none' stroke='currentColor' "
            f"stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>{ICONOS[nombre]}</svg>")


def como_funciona(G):
    """Banda de cuatro pasos bajo la portada: qué hace la herramienta, de un vistazo."""
    clases = G["clases"]
    uso, leidos = clases.get("uso", 0), sum(clases.values())
    pasos = [
        ("rastrea", "Rastrea", num(G["encontrados"] + DESCARTADOS), "apariciones encontradas",
         f"Busca las direcciones de {G['portales']} portales públicos en código de GitHub, artículos "
         "científicos y Wikipedia."),
        ("lee", "Lee", num(leidos), "leídas una a una",
         "Una IA lee el fragmento donde aparece cada portal, como lo haría una persona, y anota el motivo."),
        ("decide", "Separa", num(uso), f"usos reales ({pct(uso, leidos)}%)",
         "Distingue a quien usa los datos de verdad de quien solo los menciona, y guarda la prueba."),
        ("publica", "Mide y publica", num(G["uso_estimado_total"]), "usos estimados con margen",
         "Extrapola con estadística y publica una ficha por portal, un buscador y los datos en abierto."),
    ]
    tarjetas = "".join(f"""<li class="paso">
    <div class="paso-cab"><span class="paso-num">{i + 1}</span>{icono(ic)}</div>
    <h3>{titulo}</h3>
    <p class="paso-cifra"><b>{cifra}</b><span>{unidad}</span></p>
    <p class="paso-desc">{texto}</p></li>""" for i, (ic, titulo, cifra, unidad, texto) in enumerate(pasos))
    return f"""<section class="como" aria-labelledby="como-titulo">
  <div class="como-dentro">
    <p class="antetitulo">Cómo funciona</p>
    <h2 id="como-titulo">De un enlace suelto a la prueba de que alguien usa los datos</h2>
    <ol class="pasos">{tarjetas}</ol>
  </div>
</section>"""

LOGO = ("<svg class='logo' viewBox='0 0 32 32' aria-hidden='true'><g fill='none' stroke='currentColor' "
        "stroke-width='2.4' stroke-linecap='round'><path d='M9 25c-2-2.6-3-5.6-3-9a10 10 0 0 1 17.5-6.6'/>"
        "<path d='M13 27c-1.8-3-2.8-6.3-2.8-10a5.8 5.8 0 0 1 11.6 0c0 1.6-.1 3-.4 4.4'/>"
        "<path d='M16 17c0 4 1 7.6 3 10.5'/><path d='M26 13.5c.3 1.1.4 2.3.4 3.5 0 3-.5 5.6-1.5 7.9'/></g></svg>")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%230b0f19'/%3E%3Cg fill='none' stroke='%23ff7a45' "
           "stroke-width='2.6' stroke-linecap='round'%3E%3Cpath d='M9 25c-2-2.6-3-5.6-3-9a10 10 0 0 1 17.5-6.6'/%3E"
           "%3Cpath d='M13 27c-1.8-3-2.8-6.3-2.8-10a5.8 5.8 0 0 1 11.6 0c0 1.6-.1 3-.4 4.4'/%3E"
           "%3Cpath d='M16 17c0 4 1 7.6 3 10.5'/%3E%3C/g%3E%3C/svg%3E")


# --- Utilidades -------------------------------------------------------------

def limpia(texto):
    """Quita los códigos de emoji de GitHub (:rocket:) y espacios sobrantes."""
    return re.sub(r"\s+", " ", re.sub(r":[a-z0-9_+-]+:", "", texto or "")).strip()


def limpia_wiki(texto):
    """Deja legible un trozo de código wiki: sin etiquetas, llaves ni corchetes."""
    texto = re.sub(r"<[^>]*>", " ", texto or "")
    texto = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", texto)
    texto = re.sub(r"'{2,}|\{\{|\}\}|\[|\]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


TERMINOS = {f["id"]: [t.lower() for t in f["terminos_busqueda"].split("|")]
            for f in csv.DictReader((ROOT / "data" / "portales.csv").open())}


def evidencia(x, largo=240):
    """Trozo de la prueba centrado donde aparece el portal (o su enlace, en Wikipedia)."""
    if x["fuente"] == "openalex":
        texto = limpia((x.get("citas_en_texto") or [""])[0])
        low = texto.lower()
        pos = [low.find(t) for t in TERMINOS.get(x["portal"], []) if low.find(t) >= 0]
    elif x["fuente"] == "wikipedia":
        texto = limpia_wiki(x.get("contexto"))
        pos = [m.start() for m in re.finditer(r"url\s*=", texto)][:1]
    else:
        return ""
    if not texto:
        return ""
    centro = pos[0] if pos else len(texto) // 2
    ini = max(0, centro - largo * 2 // 5)
    fin = min(len(texto), ini + largo)
    trozo = texto[ini:fin]
    if ini > 0:
        trozo = trozo.split(" ", 1)[-1]
    if fin < len(texto):
        trozo = trozo.rsplit(" ", 1)[0]
    return trozo


def corta(texto, n):
    texto = limpia(texto)
    return texto if len(texto) <= n else texto[:n].rsplit(" ", 1)[0] + "…"


def num(n):
    return f"{n:,}".replace(",", ".")


def pct(a, b, decimales=0):
    v = 100 * a / b if b else 0
    return f"{v:.{decimales}f}".replace(".", ",")


def corto(pid, d):
    if pid in CORTO:
        return CORTO[pid]
    return f"Ayto. {d['territorio']}" if d["ambito"] == "local" else d["territorio"]


def recorta(texto, ancho_px, fs):
    """Recorta una etiqueta para que quepa en un rectángulo (estimación por carácter)."""
    cabe = int(ancho_px / (fs * 0.56))
    if len(texto) <= cabe:
        return texto
    return texto[:max(cabe - 1, 0)].rstrip() + "…" if cabe > 3 else ""


# --- Gráficos ---------------------------------------------------------------

def barras(datos, maximo=None):
    """Barras horizontales en HTML: finas, con el valor al final. Las etiquetas llegan escapadas."""
    if not datos:
        return "<p class='nota'>Sin datos.</p>"
    maximo = maximo or max(v for _, v in datos) or 1
    filas = "".join(
        f"<div class='barra'><span class='etq'>{etiqueta}</span>"
        f"<span class='pista'><span class='relleno' style='--w:{max(100 * valor / maximo, 0.8):.1f}%'></span></span>"
        f"<span class='val'>{num(valor)}</span></div>"
        for etiqueta, valor in datos)
    return f"<div class='barras'>{filas}</div>"


def apilada(clases):
    """Barra 100% con el reparto de lo que la IA leyó: el uso real, resaltado; lo demás, en grises."""
    total = sum(clases.values())
    segs, leyenda = [], []
    for c in ORDEN_CLASES:
        v = clases.get(c, 0)
        p = 100 * v / total
        texto = f"<span>{CLASES[c]} · {pct(v, total)}%</span>" if p >= 16 else ""
        segs.append(f"<span class='seg seg-{c}' style='flex-grow:{v}' tabindex='0' "
                    f"data-tip='{CLASES[c]}: {num(v)} ({pct(v, total, 1)}%)'>{texto}</span>")
        leyenda.append(f"<li><i class='muestra seg-{c}'></i>{CLASES[c]} <b>{num(v)}</b></li>")
    return (f"<div class='apilada' role='img' aria-label='De {num(total)} rastros leídos, "
            f"{num(clases.get('uso', 0))} son uso real'>{''.join(segs)}</div>"
            f"<ul class='leyenda'>{''.join(leyenda)}</ul>")


def squarify(valores, x, y, w, h):
    """Treemap 'squarified' (Bruls et al.): rectángulos lo más cuadrados posible."""
    total = sum(valores)
    areas = [v * w * h / total for v in valores]
    rects, i = [], 0

    def peor(fila, lado):
        s = sum(fila)
        return max(max(lado * lado * r / (s * s), s * s / (lado * lado * r)) for r in fila)

    while i < len(areas):
        lado = min(w, h)
        fila, j = [areas[i]], i + 1
        while j < len(areas) and peor(fila + [areas[j]], lado) <= peor(fila, lado):
            fila.append(areas[j])
            j += 1
        s = sum(fila)
        if w >= h:
            ancho, cy = s / h, y
            for a in fila:
                rects.append((x, cy, ancho, a / ancho))
                cy += a / ancho
            x, w = x + ancho, w - ancho
        else:
            alto, cx = s / w, x
            for a in fila:
                rects.append((cx, y, a / alto, alto))
                cx += a / alto
            y, h = y + alto, h - alto
        i = j
    return rects


def treemap(elementos, total, W=960, H=420, aria=""):
    """elementos: (nombre, valor, enlace, clase css). Las celdas pequeñas no llevan etiqueta:
    su valor está en el aviso al pasar el ratón y en la tabla del ranking."""
    elementos = sorted((e for e in elementos if e[1] > 0), key=lambda e: -e[1])
    rects = squarify([e[1] for e in elementos], 0, 0, W, H)
    celdas = []
    for (nombre, v, href, clase), (x, y, w, h) in zip(elementos, rects):
        rx, ry, rw, rh = x + 1, y + 1, max(w - 2, 0.5), max(h - 2, 0.5)
        texto = ""
        if rw >= 60 and rh >= 38:
            fs = 30 if (rw > 320 and rh > 200) else 16 if (rw > 150 and rh > 70) else 12
            etiqueta = recorta(nombre, rw - 20, fs)
            if etiqueta:
                tinta = " tm-txt-claro" if clase == "tm-resto" else ""
                texto = (f"<text x='{rx + 10:.1f}' y='{ry + fs + 8:.1f}' class='tm-nombre{tinta}' font-size='{fs}'>{E(etiqueta)}</text>"
                         f"<text x='{rx + 10:.1f}' y='{ry + 2 * fs + 14:.1f}' class='tm-valor{tinta}' font-size='{fs}'>"
                         f"{num(v)} · {pct(v, total)}%</text>")
        celdas.append(f"<a href='{href}' data-tip='{E(nombre)}: {num(v)} ({pct(v, total, 1)}%)'>"
                      f"<rect x='{rx:.1f}' y='{ry:.1f}' width='{rw:.1f}' height='{rh:.1f}' rx='3' class='{clase}'/>"
                      f"{texto}</a>")
    return (f"<svg class='treemap' viewBox='0 0 {W} {H}' role='img' aria-label='{E(aria)}'>"
            f"{''.join(celdas)}</svg>")


CORTES_MAPA = [10, 50, 100, 500]
TRAMOS_MAPA = ["Menos de 10", "10 a 49", "50 a 99", "100 a 499", "500 o más"]


def mapa(P):
    geo = json.loads((GEO / "ccaa.json").read_text())
    regiones = []
    for pid, r in geo["regiones"].items():
        if pid in P:
            v = P[pid]["uso_estimado"]
            tramo = sum(v >= c for c in CORTES_MAPA) + 1
            regiones.append(f"<a href='portales/{pid}.html' data-tip='{E(P[pid]['territorio'])}: {num(v)} "
                            f"reutilizaciones'><path d='{r['d']}' class='region m{tramo}'/></a>")
        else:
            regiones.append(f"<path d='{r['d']}' class='region sin'><title>Sin portal analizado</title></path>")
    x, y, w, h = geo["recuadro_canarias"]
    svg = (f"<svg class='mapa-svg' viewBox='0 0 {geo['ancho']} {geo['alto']}' role='img' "
           f"aria-label='Mapa de España coloreado según la reutilización de cada portal autonómico'>"
           f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='6' class='recuadro'/>{''.join(regiones)}</svg>")
    leyenda = "".join(f"<li><i class='muestra m{i + 1}'></i>{t}</li>" for i, t in enumerate(TRAMOS_MAPA))
    ccaa = sorted(((P[p]["uso_estimado"], p) for p in geo["regiones"] if p in P), reverse=True)
    lista = "".join(
        f"<li><a href='portales/{p}.html'><i class='muestra m{sum(v >= c for c in CORTES_MAPA) + 1}'></i>"
        f"{E(P[p]['territorio'])}</a><b>{num(v)}</b></li>" for v, p in ccaa)
    return f"""<div class="mapa-bloque">
  <figure class="mapa-fig">{svg}
    <figcaption><ul class="leyenda">{leyenda}</ul></figcaption></figure>
  <ol class="lista-ccaa">{lista}</ol>
</div>"""


def linea(anios):
    """Publicaciones verificadas por año. 2026 va aparte (punto hueco) porque el año no ha acabado."""
    datos = sorted((int(a), n) for a, n in anios.items() if int(a) >= 2015)
    completos = [(a, n) for a, n in datos if a < 2026]
    parcial = [(a, n) for a, n in datos if a >= 2026]
    W, H, ml, mr, mt, mb = 720, 300, 44, 118, 22, 34
    a0, a1 = datos[0][0], datos[-1][0]
    ymax = math.ceil(max(n for _, n in datos) / 50) * 50

    def X(a):
        return ml + (a - a0) / (a1 - a0) * (W - ml - mr)

    def Y(n):
        return mt + (1 - n / ymax) * (H - mt - mb)

    partes = []
    for t in range(0, ymax + 1, 50):
        partes.append(f"<line x1='{ml}' x2='{W - mr + 20}' y1='{Y(t):.1f}' y2='{Y(t):.1f}' class='rejilla'/>"
                      f"<text x='{ml - 8}' y='{Y(t) + 4:.1f}' class='eje' text-anchor='end'>{t}</text>")
    for a, _ in datos:
        partes.append(f"<text x='{X(a):.1f}' y='{H - 10}' class='eje' text-anchor='middle'>{a}</text>")
    pts = " ".join(f"{X(a):.1f},{Y(n):.1f}" for a, n in completos)
    partes.append(f"<path d='M{X(completos[0][0]):.1f},{Y(0):.1f} L{pts.replace(' ', ' L')} "
                  f"L{X(completos[-1][0]):.1f},{Y(0):.1f} Z' class='area'/>")
    partes.append(f"<polyline points='{pts}' class='trazo'/>")
    for a, n in completos:
        partes.append(f"<g data-tip='{a}: {n} publicaciones' tabindex='0'><circle cx='{X(a):.1f}' cy='{Y(n):.1f}' r='14' class='diana'/>"
                      f"<circle cx='{X(a):.1f}' cy='{Y(n):.1f}' r='4.5' class='punto'/></g>")
    pico = max(completos, key=lambda p: p[1])
    partes.append(f"<text x='{X(pico[0]):.1f}' y='{Y(pico[1]) - 12:.1f}' class='etq-dato' text-anchor='middle'>{pico[1]}</text>")
    ult = completos[-1]
    partes.append(f"<text x='{X(ult[0]) + 10:.1f}' y='{Y(ult[1]) - 8:.1f}' class='etq-dato'>{ult[1]} en {ult[0]}</text>")
    for a, n in parcial:
        partes.append(f"<g data-tip='{a} (hasta septiembre): {n} publicaciones' tabindex='0'>"
                      f"<circle cx='{X(a):.1f}' cy='{Y(n):.1f}' r='14' class='diana'/>"
                      f"<circle cx='{X(a):.1f}' cy='{Y(n):.1f}' r='4.5' class='punto hueco'/></g>"
                      f"<text x='{X(a) + 10:.1f}' y='{Y(n) + 4:.1f}' class='eje'>{n} (año en curso)</text>")
    return (f"<svg class='linea' viewBox='0 0 {W} {H}' role='img' aria-label='Publicaciones científicas "
            f"verificadas por año, de {a0} a {a1}'>{''.join(partes)}</svg>")


def sello(d):
    """Sello SVG que cada organismo puede poner en su web."""
    izq, der = "La Huella del Dato", f"{num(d['uso_estimado'])} reutilizaciones"
    wi, wd, h = 34 + round(len(izq) * 7.1), 20 + round(len(der) * 7.1), 28
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{wi + wd}" height="{h}" viewBox="0 0 {wi + wd} {h}" role="img" aria-label="La Huella del Dato: {der} de {E(d['nombre'])}">
<title>La Huella del Dato: {der} detectadas de {E(d['nombre'])}</title>
<clipPath id="r"><rect width="{wi + wd}" height="{h}" rx="6"/></clipPath>
<g clip-path="url(#r)"><rect width="{wi}" height="{h}" fill="#0b0f19"/><rect x="{wi}" width="{wd}" height="{h}" fill="#ff7a45"/></g>
<g transform="translate(9 6) scale(.5)" fill="none" stroke="#ff7a45" stroke-width="2.8" stroke-linecap="round"><path d="M9 25c-2-2.6-3-5.6-3-9a10 10 0 0 1 17.5-6.6"/><path d="M13 27c-1.8-3-2.8-6.3-2.8-10a5.8 5.8 0 0 1 11.6 0c0 1.6-.1 3-.4 4.4"/><path d="M16 17c0 4 1 7.6 3 10.5"/></g>
<g font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="12" font-weight="700">
<text x="30" y="18.5" fill="#ffffff">{izq}</text><text x="{wi + 10}" y="18.5" fill="#0b0f19">{der}</text></g>
</svg>"""


# --- Plantilla --------------------------------------------------------------

def pagina(titulo, descripcion, cuerpo, raiz=".", banda="", scripts="", ruta=""):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(titulo)}</title>
<meta name="description" content="{E(descripcion)}">
<link rel="canonical" href="{BASE_URL}/{ruta}">
<meta property="og:type" content="website">
<meta property="og:title" content="{E(titulo)}">
<meta property="og:description" content="{E(descripcion)}">
<meta property="og:image" content="{BASE_URL}/og.png">
<meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b0f19">
<link rel="preload" href="{raiz}/fuentes/bricolage.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{raiz}/estilo.css">
<link rel="icon" href="{FAVICON}">
<script defer src="/_vercel/insights/script.js"></script>
</head>
<body>
<a class="saltar" href="#principal">Saltar al contenido</a>
<div class="oscuro">
<header class="cabecera">
  <a class="marca" href="{raiz}/index.html">{LOGO}<span>La Huella del Dato</span></a>
  <nav aria-label="Principal">
    <a href="{raiz}/ranking.html">Ranking</a>
    <a href="{raiz}/buscar.html">Buscador</a>
    <a href="{raiz}/metodologia.html">Metodología</a>
    <a href="{raiz}/datos.html">Datos abiertos</a>
  </nav>
</header>
{banda}
</div>
<main id="principal">
{cuerpo}
</main>
<footer class="pie">
  <div class="pie-dentro">
    <p class="marca-pie">{LOGO}<span>La Huella del Dato</span></p>
    <p>Un proyecto de Guillermo Molero Jiménez, estudiante del Grado en Ciencia de Datos e Inteligencia
    Artificial de la Universidad Miguel Hernández de Elche.</p>
    <p>Datos del proyecto publicados bajo <a href="https://creativecommons.org/licenses/by/4.0/deed.es">CC BY 4.0</a>.
    Código abierto en <a href="{REPO_URL}">GitHub</a> (MIT).
    Fuentes: OpenAlex, Wikipedia y GitHub. Mapa: Natural Earth (dominio público). Tipografía: Bricolage
    Grotesque (SIL Open Font License). Última actualización: septiembre de 2026.</p>
  </div>
</footer>
<div id="aviso" role="tooltip" hidden></div>
<script>{JS_AVISOS}</script>
{scripts}
</body>
</html>
"""


def cabecera_seccion(numero, antetitulo, titulo, entradilla=""):
    return (f"<header class='sec-cab'><p class='antetitulo'><span>{numero}</span>{antetitulo}</p>"
            f"<h2>{titulo}</h2>{f'<p class=entradilla>{entradilla}</p>' if entradilla else ''}</header>")


def tarjeta_caso(x, r, P, raiz="."):
    """Tarjeta de un reutilizador concreto con el veredicto de la IA y su prueba."""
    meta, prueba = [], ""
    if x["fuente"] == "github":
        if x.get("estrellas"):
            meta.append(f"★ {num(x['estrellas'])}")
        if x.get("lenguaje"):
            meta.append(E(x["lenguaje"]))
    elif x["fuente"] == "openalex":
        if x.get("anio"):
            meta.append(str(x["anio"]))
        if x.get("revista"):
            meta.append(E(x["revista"][:60]))
        prueba = E(evidencia(x))
    else:
        meta.append(IDIOMAS.get(x["idioma"], x["idioma"]))
        prueba = E(evidencia(x))
    return f"""<li class="caso">
  <div class="caso-cab"><span class="chip chip-{r['clase']}">{CLASES[r['clase']]}</span>
  <span class="caso-fuente">{" · ".join([FUENTES[x['fuente']]] + meta)}</span></div>
  <a class="caso-titulo" href="{E(x['url'])}" rel="noopener">{E((x["nombre"] or x["url"])[:110])}</a>
  <p class="caso-motivo"><span class="ia">IA</span>{E(r['motivo'])}</p>
  {f'<p class="evidencia">«…{prueba}…»</p>' if prueba else ''}
  <p class="caso-pie"><a href="{raiz}/portales/{x['portal']}.html">{E(P[x['portal']]['nombre'])}</a> ·
  {SECTORES.get(r['sector'], r['sector'])} · {ACTORES.get(r['actor'], r['actor'])}</p>
</li>"""


# --- Páginas ----------------------------------------------------------------

CACHE_ENTRADAS = PROC / "ia" / "ejemplos_entrada.json"


def entrada_ia(x):
    """Texto literal que recibió la IA para este caso, con el mismo código que se usó al clasificar.
    Se guarda en caché para poder regenerar la web sin los datos en bruto (que no se publican)."""
    cache = json.loads(CACHE_ENTRADAS.read_text()) if CACHE_ENTRADAS.exists() else {}
    k = f"{x['portal']}|{x['fuente']}|{x['id']}"
    if k not in cache:
        portales = {f["id"]: f for f in csv.DictReader((ROOT / "data" / "portales.csv").open())}
        frags = classify.fragmentos_github() if x["fuente"] == "github" else {}
        cache[k] = classify.describir(0, x, portales, frags).split("\n", 1)[1]
        CACHE_ENTRADAS.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return cache[k]


def demo_ia(items, ia):
    filas = []
    for k in EJEMPLOS_IA:
        x, r = items[k], ia[k]
        filas.append(f"""<div class="demo-fila">
  <div class="demo-entrada"><p class="demo-rotulo">Lo que lee la IA</p>
    <pre>{E(entrada_ia(x))}</pre></div>
  <div class="demo-flecha" aria-hidden="true">→</div>
  <div class="demo-salida"><p class="demo-rotulo">Lo que responde</p>
    <p><span class="chip chip-{r['clase']} chip-grande">{CLASES[r['clase']]}</span></p>
    <dl>
      <div><dt>Motivo</dt><dd>{E(r['motivo'])}</dd></div>
      <div><dt>Sector</dt><dd>{SECTORES[r['sector']]}</dd></div>
      <div><dt>Quién reutiliza</dt><dd>{ACTORES[r['actor']]}</dd></div>
      <div><dt>Confianza</dt><dd>{CONFIANZA[r['confianza']]}</dd></div>
    </dl>
    <p class="demo-enlace"><a href="{E(x['url'])}" rel="noopener">Ver el original ↗</a></p></div>
</div>""")
    return f"""<div class="demo">{''.join(filas)}</div>
<ul class="hechos">
  <li><b>Qué IA</b><span>Claude Sonnet, de Anthropic.</span></li>
  <li><b>Con reglas fijas</b><span>Solo puede elegir entre cinco veredictos y debe justificar cada uno en una frase.</span></li>
  <li><b>Antes de publicar</b><span>La IA trabajó una vez sobre todos los casos. La web no la llama: por eso las cifras
  son fijas, cada decisión se puede revisar y mantenerla cuesta 0 €.</span></li>
  <li><b>Auditable</b><span>Cada una de sus decisiones se publica con su motivo y el enlace al original, en el
  <a href="buscar.html">buscador</a> y en los <a href="datos.html">datos abiertos</a>.</span></li>
</ul>
<p><a class="enlace-flecha" href="metodologia.html#instrucciones">Leer las instrucciones completas que sigue la IA →</a></p>"""


def portada(P, G, items, ia, empresas):
    clases = G["clases"]
    uso_v, total_leidos = clases.get("uso", 0), sum(clases.values())
    total = G["uso_estimado_total"]
    top3 = G["ranking"][:3]
    pct_top3 = pct(sum(n for n, _ in top3), total)
    pct_empresa = pct(G["actores"].get("empresa", 0), sum(G["actores"].values()), 1)
    por_fuente = collections.Counter()
    for d in P.values():
        for f, v in d["fuentes"].items():
            por_fuente[f] += v["uso_estimado"]

    banda = f"""<section class="hero">
  <canvas id="constelacion" data-uso="{uso_v}" data-resto="{total_leidos - uso_v}" aria-hidden="true"></canvas>
  <div class="hero-texto">
    <p class="antetitulo">{G['portales']} portales públicos · {num(G['encontrados'])} rastros · {num(total_leidos)} leídos uno a uno</p>
    <h1>¿Quién usa de verdad los datos públicos españoles?</h1>
    <p class="hero-cifra"><b>{num(total)}</b><span>reutilizaciones reales estimadas</span></p>
    <p class="desglose">De ellas, <b>{num(por_fuente['wikipedia'])}</b> son referencias en Wikipedia,
    <b>{num(por_fuente['openalex'])}</b> publicaciones científicas y <b>{num(por_fuente['github'])}</b> proyectos de código.</p>
    <p class="hero-leyenda"><i class="punto-uso"></i>Cada punto es un rastro que la IA leyó. En naranja,
    los <b>{num(uso_v)}</b> que usan los datos de verdad. <i class="punto-resto"></i>En gris, los que solo los mencionan.</p>
    <p class="acciones"><a class="boton" href="buscar.html">Busca un portal o un proyecto</a>
    <a class="boton secundario" href="#como-titulo">Cómo funciona ↓</a></p>
  </div>
</section>
{como_funciona(G)}"""


    # Treemaps: todos los portales y, aparte, los 32 que no se ven al lado de los tres grandes
    grandes = {p for _, p in top3}
    tm_todos = treemap([(corto(p, P[p]), P[p]["uso_estimado"], f"portales/{p}.html",
                         "tm-top" if p in grandes else "tm-resto") for p in P], total, H=400,
                       aria=f"Los tres portales más reutilizados suman el {pct_top3}% del total")
    resto = [p for p in P if p not in grandes]
    total_resto = sum(P[p]["uso_estimado"] for p in resto)
    tm_resto = treemap([(corto(p, P[p]), P[p]["uso_estimado"], f"portales/{p}.html", "tm-zoom") for p in resto],
                       total_resto, H=460, aria="Los otros 32 portales, ampliados")
    casi_invisibles = sum(1 for p in P if P[p]["uso_estimado"] < 20)

    # Empresas
    bloques_emp = []
    for p, n in empresas["orden"][:3]:
        ejemplos_emp = "".join(
            f"<li><a href='{E(x['url'])}' rel='noopener' data-tip='{E(r['motivo'])}'>{E(x['nombre'].split('/')[-1])}</a></li>"
            for x, r in empresas["ejemplos"][p][:4])
        bloques_emp.append(f"""<div class="empresa-portal">
  <p class="empresa-cifra"><b>{pct(n, empresas['usos'][p])}%</b> de sus usos son de empresas</p>
  <h3><a href="portales/{p}.html">{E(P[p]['nombre'])}</a></h3>
  <ul class="chips">{ejemplos_emp}</ul></div>""")

    # Casos destacados
    vistos, destacados = set(), []
    for e in G["ejemplos_github"]:
        propietario = e["nombre"].split("/")[0]
        if propietario in vistos or e["nombre"] in NO_DESTACAR:
            continue
        vistos.add(propietario)
        destacados.append(f"""<li class="destacado">
  <p class="estrellas">★ {num(e['estrellas'])}</p>
  <a class="destacado-nombre" href="{E(e['url'])}" rel="noopener">{E(e['nombre'])}</a>
  <p>{E(corta(e['descripcion'], 110))}</p>
  <p class="usa">Usa datos de <a href="portales/{e['portal']}.html">{E(corto(e['portal'], P[e['portal']]))}</a></p>
</li>""")
        if len(destacados) == 8:
            break

    anios = {a: n for a, n in G["anios_publicaciones"].items() if int(a) >= 2015}
    a2015, a2025 = anios.get("2015", 0), anios.get("2025", 0)
    ejemplo_ficha = G["ranking"][3][1]  # un portal mediano-grande como ejemplo del informe

    cuerpo = f"""
<section class="seccion" id="aparecer">
  {cabecera_seccion("01", "El método", "Aparecer no es usar",
    f"Que un portal aparezca en un repositorio, un artículo o una página de Wikipedia no significa que "
    f"alguien use sus datos. Por eso una IA leyó el contexto de {num(total_leidos)} rastros, uno a uno, y "
    f"decidió en cada caso. Solo el {pct(uso_v, total_leidos)}% resultó ser uso real.")}
  {apilada(clases)}
  <h3 class="sub">Así decide la IA, con dos casos reales</h3>
  {demo_ia(items, ia)}
</section>

<section class="seccion">
  {cabecera_seccion("02", "Hallazgo", f"Tres organismos concentran el {pct_top3}% de la huella",
    f"El INE, Open Data Euskadi y el Instituto Geográfico Nacional suman la inmensa mayoría de la "
    f"reutilización detectada. Los otros {len(resto)} portales se reparten el {100 - int(pct_top3)}% restante.")}
  <figure class="figura">{tm_todos}
    <figcaption><ul class="leyenda"><li><i class="muestra tm-top"></i>Los tres mayores</li>
    <li><i class="muestra tm-resto"></i>Los otros {len(resto)}</li></ul>
    Cada rectángulo es un portal y su área, su reutilización estimada. Pasa el ratón por encima para ver la cifra.</figcaption>
  </figure>
  <h3 class="sub">Los otros {len(resto)}, ampliados</h3>
  <p class="nota">A esta escala ya se distinguen. En {casi_invisibles} portales se han detectado menos de 20
  reutilizaciones con rastro público, lo que señala dónde hay más margen para dar a conocer sus datos.</p>
  <figure class="figura">{tm_resto}</figure>
  <p><a class="enlace-flecha" href="ranking.html">Ver el ranking completo con márgenes de error →</a></p>
</section>

<section class="seccion">
  {cabecera_seccion("03", "Territorio", "La huella de cada comunidad autónoma",
    "Reutilización detectada del portal de datos de cada comunidad. El tamaño del territorio no "
    "determina la huella: influyen la antigüedad del portal, el tipo de datos que publica y cuánto se enlazan.")}
  {mapa(P)}
</section>

<section class="seccion">
  {cabecera_seccion("04", "Sector infomediario", "Las empresas sí están, pero donde nadie mira",
    f"Solo el {pct_empresa}% de los usos visibles son de empresas: la mayoría reutiliza en privado y no deja "
    f"rastro público. Pero cuando aparecen, no lo hacen al azar. Se concentran en el registro mercantil, el "
    f"catastro y la contratación pública: aplicaciones inmobiliarias, herramientas de cumplimiento normativo y "
    f"buscadores de licitaciones.")}
  <div class="empresas">{''.join(bloques_emp)}</div>
  <p class="nota">Porcentaje sobre los usos verificados de cada portal. La media de los {G['portales']} portales
  es del {pct_empresa}%. Los nombres enlazan a cada proyecto; pasa el ratón para ver qué hace con los datos.</p>
</section>

<section class="seccion">
  {cabecera_seccion("05", "Perfil", "Quién reutiliza y para qué")}
  <div class="dos">
    <div><h3 class="sub">Quién</h3>
    {barras(sorted(((E(ACTORES.get(k, k)), v) for k, v in G['actores'].items()), key=lambda x: -x[1]))}</div>
    <div><h3 class="sub">Para qué</h3>
    {barras(sorted(((E(SECTORES.get(k, k)), v) for k, v in G['sectores'].items()), key=lambda x: -x[1]))}</div>
  </div>
  <p class="nota">Reparto de los {num(uso_v)} usos reales verificados.</p>
</section>

<section class="seccion">
  {cabecera_seccion("06", "Ciencia", f"La ciencia que usa datos públicos se ha multiplicado por {a2025 / max(a2015, 1):.0f} en diez años",
    f"Publicaciones científicas en las que se ha verificado, leyendo el texto completo, que usan datos de "
    f"estos portales: {a2015} en 2015 y {a2025} en 2025. Parte del crecimiento se debe a que hoy hay más "
    f"artículos en acceso abierto, pero la tendencia es clara.")}
  <figure class="figura">{linea(G['anios_publicaciones'])}</figure>
</section>

<section class="seccion">
  {cabecera_seccion("07", "Casos", "Proyectos con miles de usuarios que se apoyan en datos públicos",
    "Algunos de los repositorios más populares cuyo uso de datos se ha verificado.")}
  <ul class="destacados">{''.join(destacados)}</ul>
</section>

<section class="seccion organismos">
  {cabecera_seccion("08", "Para los organismos", "Una herramienta, no solo un estudio",
    "Cada portal tiene su propio informe, sus casos con la prueba de cada uno y un sello para su web.")}
  <div class="tres">
    <a class="accion" href="portales/{ejemplo_ficha}.html"><span class="accion-num">1</span>
      <h3>Informe por portal</h3><p>Quién usa sus datos, para qué y con qué margen de error. Se puede guardar en PDF.</p></a>
    <a class="accion" href="portales/{ejemplo_ficha}.html#sello"><span class="accion-num">2</span>
      <h3>Sello para su web</h3><p><img src="sellos/{ejemplo_ficha}.svg" alt="Ejemplo de sello" class="sello-mini"></p></a>
    <a class="accion" href="datos.html"><span class="accion-num">3</span>
      <h3>Datos abiertos</h3><p>Los {num(total_leidos)} casos clasificados, en CSV y JSON con licencia CC BY 4.0.</p></a>
  </div>
</section>
"""
    return banda, cuerpo


def ficha(pid, d, G, P, usos, clasificados, rank):
    total_usos = len(usos)
    fuentes_orden = sorted(d["fuentes"].items(), key=lambda kv: -kv[1]["uso_estimado"])
    fprin, vprin = fuentes_orden[0]
    sectores = collections.Counter(r["sector"] for _, r in usos)
    actores = collections.Counter(r["actor"] for _, r in usos)
    mediana = sorted(n for n, _ in G["ranking"])[len(G["ranking"]) // 2]
    emp = actores.get("empresa", 0)
    media_emp = pct(G["actores"].get("empresa", 0), sum(G["actores"].values()), 1)

    datos_clave = []
    if d["uso_estimado"]:
        datos_clave.append((f"{pct(vprin['uso_estimado'], d['uso_estimado'])}%",
                            f"de su huella está en {EN_FUENTE[fprin]}"))
    if sectores:
        s, n = sectores.most_common(1)[0]
        datos_clave.append((SECTORES.get(s, s), f"es el uso más frecuente ({n} de {total_usos} casos verificados)"))
    if actores:
        a, n = actores.most_common(1)[0]
        datos_clave.append((ACTORES.get(a, a), f"es quien más lo reutiliza ({pct(n, total_usos)}% de los casos)"))
    if mediana:
        veces = d["uso_estimado"] / mediana
        datos_clave.append((f"×{veces:.1f}".replace(".", ",") if veces >= 1 else f"{pct(d['uso_estimado'], mediana)}%",
                            f"respecto al portal mediano ({num(mediana)} reutilizaciones)"))
    datos_clave.append((f"{pct(emp, total_usos, 1)}%" if total_usos else "—",
                        f"de sus usos son de empresas (media de los {G['portales']}: {media_emp}%)"))
    claves_html = "".join(f"<li><b>{E(v)}</b><span>{E(t)}</span></li>" for v, t in datos_clave)

    tabla_fuentes = "".join(
        f"<tr><td>{FUENTES[f]}</td><td class='n'>{num(v['encontrados'])}</td><td class='n'>{num(v['clasificados'])}</td>"
        f"<td class='n'><b>{num(v['uso_estimado'])}</b></td><td class='n rango'>{num(v['uso_min'])}–{num(v['uso_max'])}</td></tr>"
        for f, v in fuentes_orden)

    def peso(par):
        x, _ = par
        return (x.get("estrellas") or 0) * 10 + (x.get("citas") or 0) * 5 + (1 if x.get("citas_en_texto") or x.get("contexto") else 0)
    usos = sorted(usos, key=peso, reverse=True)
    lista = "".join(tarjeta_caso(x, r, P, raiz="..") for x, r in usos[:24])
    codigo = (f'<a href="{BASE_URL}/portales/{pid}.html"><img src="{BASE_URL}/sellos/{pid}.svg" '
              f'alt="La Huella del Dato: {num(d["uso_estimado"])} reutilizaciones"></a>')

    banda = f"""<section class="banda">
  <p class="antetitulo"><a href="../ranking.html">Puesto {rank} de {G['portales']}</a> · {AMBITOS[d['ambito']]} · {E(d['territorio'])}</p>
  <h1>{E(d['nombre'])}</h1>
  <div class="banda-cifras">
    <p class="hero-cifra"><b>{num(d['uso_estimado'])}</b><span>reutilizaciones reales estimadas</span></p>
    <dl class="banda-dl">
      <div><dt>Margen de confianza (95%)</dt><dd>{num(d['uso_min'])}–{num(d['uso_max'])}</dd></div>
      <div><dt>Rastros analizados</dt><dd>{num(d['encontrados'])}</dd></div>
      <div><dt>Leídos uno a uno por la IA</dt><dd>{num(clasificados)}</dd></div>
    </dl>
  </div>
  <p class="acciones"><a class="boton" href="../buscar.html?portal={pid}">Ver sus {num(total_usos)} casos verificados</a>
  <button class="boton secundario" type="button" onclick="print()">Guardar informe en PDF</button>
  <a class="boton secundario" href="{E(d['url'])}" rel="noopener">Portal oficial ↗</a></p>
</section>"""

    cuerpo = f"""
<p class="solo-impresion">Informe de reutilización · La Huella del Dato · {BASE_URL}/portales/{pid}.html</p>
<section class="seccion">
  {cabecera_seccion("01", "Resumen", "Lo que dicen los datos")}
  <ul class="claves">{claves_html}</ul>
</section>
<section class="seccion">
  {cabecera_seccion("02", "Fuentes", "Dónde deja huella")}
  {barras([(E(FUENTES[f]), v['uso_estimado']) for f, v in fuentes_orden])}
  <table class="tabla"><thead><tr><th>Fuente</th><th class="n">Rastros</th><th class="n">Leídos por la IA</th>
  <th class="n">Uso estimado</th><th class="n">Margen (95%)</th></tr></thead><tbody>{tabla_fuentes}</tbody></table>
  <p class="nota">Cuando hay muchos rastros se lee una muestra aleatoria y se extrapola; por eso cada cifra lleva su margen.</p>
</section>
<section class="seccion">
  {cabecera_seccion("03", "Perfil", "Para qué y quién")}
  <div class="dos">
    <div><h3 class="sub">Para qué se usan</h3>{barras([(E(SECTORES.get(k, k)), v) for k, v in sectores.most_common()])}</div>
    <div><h3 class="sub">Quién los usa</h3>{barras([(E(ACTORES.get(k, k)), v) for k, v in actores.most_common()])}</div>
  </div>
</section>
<section class="seccion">
  {cabecera_seccion("04", "Casos", "Quién usa sus datos, con la prueba",
    f"Los {min(24, total_usos)} más relevantes de {num(total_usos)} verificados. Cada uno enlaza a su origen.")}
  <ul class="casos">{lista}</ul>
  <p><a class="enlace-flecha" href="../buscar.html?portal={pid}">Ver los {num(total_usos)} casos en el buscador →</a></p>
</section>
<section class="seccion sello-bloque" id="sello">
  {cabecera_seccion("05", "Para su web", "Sello de La Huella del Dato",
    "Si gestiona este portal, puede enseñar a sus usuarios cuánto se reutilizan sus datos. El sello enlaza a esta ficha.")}
  <p><img src="../sellos/{pid}.svg" alt="Sello: {num(d['uso_estimado'])} reutilizaciones"></p>
  <label for="codigo-sello" class="nota">Código para pegar en su web</label>
  <textarea id="codigo-sello" readonly rows="3">{E(codigo)}</textarea>
  <p><button class="boton secundario claro" type="button" data-copiar="codigo-sello">Copiar código</button></p>
</section>"""
    return banda, cuerpo


def main():
    resultados = json.loads((PROC / "resultados.json").read_text())
    P, G = resultados["portales"], resultados["global"]
    items = {f"{x['portal']}|{x['fuente']}|{x['id']}": x
             for x in map(json.loads, (PROC / "reutilizaciones.jsonl").open())}
    ia = {}
    for l in (PROC / "ia" / "sonnet.jsonl").open():
        r = json.loads(l)
        if r["clave"] in items:
            ia[r["clave"]] = r

    for sub in ("portales", "datos", "sellos", "fuentes"):
        (WEB / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(ASSETS / "fuentes" / "bricolage.woff2", WEB / "fuentes" / "bricolage.woff2")
    shutil.copy(ASSETS / "og.png", WEB / "og.png")  # imagen al compartir; se genera con assets/og.html

    por_portal = collections.defaultdict(list)
    for k, r in ia.items():
        por_portal[items[k]["portal"]].append((items[k], r))

    # Empresas: cuántos usos verificados de cada portal vienen de empresas, con ejemplos
    empresas = {"por_portal": collections.Counter(), "usos": collections.Counter(),
                "ejemplos": collections.defaultdict(list)}
    for p, lista in por_portal.items():
        for x, r in lista:
            if r["clase"] != "uso":
                continue
            empresas["usos"][p] += 1
            if r["actor"] == "empresa":
                empresas["por_portal"][p] += 1
                if x["fuente"] == "github":
                    empresas["ejemplos"][p].append((x, r))
    # Orden por peso relativo, no absoluto, y solo con al menos 10 casos para que no mande el azar
    empresas["orden"] = sorted(((p, n) for p, n in empresas["por_portal"].items() if n >= 10),
                               key=lambda pn: -pn[1] / empresas["usos"][pn[0]])
    for p in empresas["ejemplos"]:
        empresas["ejemplos"][p].sort(key=lambda xr: -(xr[0].get("estrellas") or 0))

    # --- Portada ---
    banda, cuerpo = portada(P, G, items, ia, empresas)
    (WEB / "index.html").write_text(pagina(
        "La Huella del Dato · Quién usa de verdad los datos públicos españoles",
        f"Rastreo automático de quién reutiliza los datos abiertos de {G['portales']} portales públicos españoles "
        "en GitHub, publicaciones científicas y Wikipedia, con la prueba de cada caso.",
        cuerpo, banda=banda, scripts=f"<script>{JS_CONSTELACION}</script>"))

    # --- Ranking ---
    maximo = G["ranking"][0][0]
    filas = []
    for i, (n, p) in enumerate(G["ranking"], 1):
        d = P[p]
        filas.append(f"""<tr><td class="n puesto">{i}</td>
  <td><a href="portales/{p}.html">{E(d['nombre'])}</a><span class="sub-celda">{E(d['territorio'])}</span></td>
  <td>{AMBITOS[d['ambito']]}</td>
  <td class="celda-barra"><span class="pista"><span class="relleno" style="--w:{max(100 * n / maximo, 0.6):.1f}%"></span></span></td>
  <td class="n"><b>{num(n)}</b></td><td class="n rango">{num(d['uso_min'])}–{num(d['uso_max'])}</td>
  <td class="n">{num(d['encontrados'])}</td></tr>""")
    banda_rk = f"""<section class="banda"><p class="antetitulo">Clasificación</p><h1>Ranking de portales</h1>
<p class="entradilla-banda">Los {G['portales']} portales ordenados por reutilizaciones reales estimadas en código,
ciencia y Wikipedia. El margen indica el intervalo de confianza del 95%.</p></section>"""
    (WEB / "ranking.html").write_text(pagina(
        "Ranking de portales · La Huella del Dato",
        f"Los {G['portales']} portales de datos abiertos españoles ordenados por reutilización detectada.",
        f"""<section class="seccion"><div class="tabla-envoltorio"><table class="tabla ranking"><thead><tr><th class="n">#</th><th>Portal</th>
<th>Ámbito</th><th class="celda-barra"><span class="solo-lector">Barra</span></th><th class="n">Uso estimado</th>
<th class="n">Margen (95%)</th><th class="n">Rastros</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table></div></section>""", banda=banda_rk, ruta="ranking.html"))

    # --- Fichas por portal y sellos ---
    posicion = {p: i for i, (_, p) in enumerate(G["ranking"], 1)}
    for pid, d in P.items():
        usos = [(x, r) for x, r in por_portal.get(pid, []) if r["clase"] == "uso"]
        banda_f, cuerpo_f = ficha(pid, d, G, P, usos, len(por_portal.get(pid, [])), posicion[pid])
        (WEB / "portales" / f"{pid}.html").write_text(pagina(
            f"{d['nombre']} · La Huella del Dato",
            f"Quién reutiliza los datos de {d['nombre']}: {num(d['uso_estimado'])} reutilizaciones reales "
            "estimadas, con la prueba de cada caso.",
            cuerpo_f, raiz="..", banda=banda_f, scripts=f"<script>{JS_COPIAR}</script>",
            ruta=f"portales/{pid}.html"))
        (WEB / "sellos" / f"{pid}.svg").write_text(sello(d))

    # --- Buscador ---
    filas_b = []
    for k, r in ia.items():
        x = items[k]
        if not x["url"].startswith("http"):
            continue
        if x["fuente"] == "github":
            meta = " · ".join(filter(None, [f"★ {num(x['estrellas'])}" if x.get("estrellas") else "", x.get("lenguaje") or ""]))
            evid = ""
        elif x["fuente"] == "openalex":
            meta = " · ".join(filter(None, [str(x.get("anio") or ""), (x.get("revista") or "")[:50]]))
            evid = evidencia(x, 200)
        else:
            meta = IDIOMAS.get(x["idioma"], x["idioma"])
            evid = evidencia(x, 200)
        filas_b.append([x["portal"], x["fuente"], r["clase"], r["sector"], r["actor"],
                        (x["nombre"] or x["url"])[:120], x["url"], r["motivo"], evid, meta])
    orden_clase = {c: i for i, c in enumerate(ORDEN_CLASES)}
    filas_b.sort(key=lambda f: (orden_clase.get(f[2], 9), f[0]))
    (WEB / "datos" / "buscador.json").write_text(json.dumps({
        "portales": {p: d["nombre"] for p, d in P.items()}, "fuentes": FUENTES, "clases": CLASES,
        "sectores": SECTORES, "actores": ACTORES, "filas": filas_b}, ensure_ascii=False, separators=(",", ":")))
    opciones_fuente = "".join(f"<option value='{k}'>{v}</option>" for k, v in FUENTES.items())
    opciones_clase = "".join(f"<option value='{k}'{' selected' if k == 'uso' else ''}>{v}</option>"
                             for k, v in CLASES.items())
    banda_b = f"""<section class="banda"><p class="antetitulo">Buscador</p><h1>Busca cualquier caso</h1>
<p class="entradilla-banda">Los {num(len(filas_b))} rastros que la IA leyó uno a uno, con su veredicto y la prueba.
Busca por portal, proyecto, tema o institución.</p></section>"""
    (WEB / "buscar.html").write_text(pagina(
        "Buscador · La Huella del Dato",
        "Busca entre los casos de reutilización de datos públicos españoles verificados uno a uno.",
        f"""<section class="seccion buscador">
  <form class="filtros" role="search" onsubmit="return false">
    <label class="campo campo-texto"><span>Buscar</span>
      <input id="q" type="search" placeholder="Ej.: tráfico, Catastro, Universidad de Sevilla, home-assistant" autocomplete="off"></label>
    <label class="campo"><span>Portal</span><select id="f-portal"><option value="">Todos</option></select></label>
    <label class="campo"><span>Fuente</span><select id="f-fuente"><option value="">Todas</option>{opciones_fuente}</select></label>
    <label class="campo"><span>Veredicto</span><select id="f-clase"><option value="">Todos</option>{opciones_clase}</select></label>
  </form>
  <p id="cuenta" class="cuenta" aria-live="polite">Cargando casos…</p>
  <ul id="resultados" class="casos"></ul>
  <p><button id="mas" class="boton secundario claro" type="button" hidden>Mostrar más</button></p>
  <noscript><p class="nota">El buscador necesita JavaScript. Todos los casos están también en
  <a href="datos/reutilizaciones-clasificadas.csv">este CSV</a>.</p></noscript>
</section>""", banda=banda_b, scripts=f"<script>{JS_BUSCADOR}</script>", ruta="buscar.html"))

    # --- Metodología ---
    descartados = DESCARTADOS
    clases = G["clases"]
    pasos = [
        (num(G["encontrados"] + descartados), "rastros en bruto",
         "Direcciones de los portales encontradas en código de GitHub, texto completo de publicaciones (OpenAlex) y Wikipedia en cinco idiomas."),
        (num(G["encontrados"]), "tras la limpieza",
         f"Fuera las copias de un mismo fichero y los repositorios del propio organismo: {num(descartados)} descartados."),
        (num(G["clasificados"]), "leídos uno a uno por la IA",
         "Todos los de los portales pequeños y una muestra aleatoria de los grandes. La IA lee el fragmento real donde aparece la dirección."),
        (num(clases.get("uso", 0)), "usos reales verificados",
         "Descarga datos, llama a la API, los analiza o los cita como fuente de sus cifras. El resto solo menciona el portal."),
        (num(G["uso_estimado_total"]), "usos reales estimados",
         "La proporción de cada muestra se extrapola a su total con un intervalo de confianza del 95% (Wilson)."),
    ]
    embudo = "".join(f"<li><b>{v}</b><span class='paso-titulo'>{t}</span><span class='paso-texto'>{x}</span></li>"
                     for v, t, x in pasos)
    banda_m = """<section class="banda"><p class="antetitulo">Metodología</p><h1>Cómo se mide la huella</h1>
<p class="entradilla-banda">Todo el proceso es reproducible y los datos intermedios están publicados. Estas son
las decisiones que hay detrás de cada cifra, incluidas sus limitaciones.</p></section>"""
    (WEB / "metodologia.html").write_text(pagina(
        "Metodología · La Huella del Dato",
        "Cómo se rastrea y verifica la reutilización de los datos públicos: fuentes, muestreo, "
        "clasificación con IA y limitaciones.",
        f"""<section class="seccion">
  {cabecera_seccion("01", "El proceso", "De {0} rastros a {1} usos reales".format(pasos[0][0], pasos[4][0]))}
  <ol class="embudo">{embudo}</ol>
</section>
<section class="seccion texto">
  {cabecera_seccion("02", "Qué se rastrea", "35 portales, tres fuentes")}
  <p>{G['portales']} portales de datos abiertos españoles: los grandes organismos estatales (INE, IGN, AEMET,
  Catastro, BOE, Plataforma de Contratación, DGT, Portal de la Transparencia, datos.gob.es y UniversiDATA), las 17
  comunidades autónomas y 8 ayuntamientos. De cada uno se buscan sus dominios y rutas oficiales, incluidos los de
  sus servicios técnicos y los dominios antiguos que se siguen citando.</p>
  <ul>
  <li><b>GitHub</b>: ficheros de código que contienen la dirección del portal.</li>
  <li><b>OpenAlex</b>: publicaciones científicas cuyo texto completo menciona el portal.</li>
  <li><b>Wikipedia</b>: artículos que enlazan al portal, en español, catalán, gallego, euskera e inglés.</li>
  </ul>
</section>
<section class="seccion texto">
  {cabecera_seccion("03", "El núcleo", "Aparecer no es usar")}
  <p>Cada rastro se clasifica en una de estas categorías: <b>uso</b> (descarga datos, llama a la API, los analiza o
  los cita como fuente de sus cifras), <b>estudio</b> (investiga el propio ecosistema de datos abiertos),
  <b>mención</b> (lo nombra sin usarlo, como en las listas de recursos) y <b>ruido</b> (coincidencia accidental).
  La clasificación la hace un modelo de lenguaje (Claude Sonnet) leyendo el fragmento real donde aparece la dirección,
  y deja escrito el motivo de cada decisión.</p>
  <p>Para elegir el modelo se compararon dos (Claude Haiku y Claude Sonnet) sobre los mismos 200 casos: coincidieron
  en el 80%. Los desacuerdos se revisaron uno a uno para ajustar las instrucciones, y se eligió Sonnet porque resolvía
  mejor los casos difíciles. Esa revisión la hizo también un asistente de IA, así que <b>no es una medida independiente
  de acierto</b>. La validación con revisión humana a ciegas de una muestra aleatoria es la principal tarea pendiente.
  Mientras tanto, cada decisión se publica con su motivo y el enlace al original para que cualquiera pueda comprobarla.</p>
  <details class="instrucciones" id="instrucciones" open>
    <summary>Las instrucciones exactas que recibe la IA</summary>
    <p class="nota">Se copian tal cual del código. Después de estas instrucciones, la IA recibe los casos en lotes de 40,
    cada uno con el texto que se ve en la portada.</p>
    <pre>{E(classify.SISTEMA)}

{E(classify.INSTRUCCIONES.strip())}</pre>
  </details>
</section>
<section class="seccion texto">
  {cabecera_seccion("04", "Estadística", "Muestreo y margen de error")}
  <p>En los portales con muchos rastros no se lee todo: se toma una muestra aleatoria de 250 por portal y fuente,
  y la proporción se extrapola con un intervalo de confianza del 95% (método de Wilson). Por eso las cifras
  estimadas se publican siempre con su margen.</p>
  <p>En las publicaciones científicas solo puede juzgarse el uso cuando se consigue el PDF de acceso abierto y se
  extrae la frase exacta donde se cita el portal. Se logró en el 58% de los casos, elegidos al azar, y desde ahí se
  extrapola. Las demás quedan como «cita sin verificar», sin afirmar que usen los datos.</p>
</section>
<section class="seccion texto">
  {cabecera_seccion("05", "Honestidad", "Limitaciones")}
  <ul>
  <li>Solo se ve la reutilización que deja rastro público. Una empresa que descarga datos y los usa en su producto es
  invisible aquí: la cifra de empresas debe leerse como «rastro público detectable», no como «uso real del sector».</li>
  <li>La búsqueda de código de GitHub tiene un tope de 1.000 resultados por consulta; se sortea partiendo por tamaño
  de fichero, con un límite de 4.000 ficheros por término.</li>
  <li>Un portal con más rastros no es necesariamente mejor: influyen su antigüedad, su tamaño y el tipo de datos
  que publica.</li>
  <li>El acierto de la IA no se ha validado todavía con una revisión humana independiente. Los márgenes de error
  publicados recogen la incertidumbre del muestreo, no los posibles errores de clasificación.</li>
  </ul>
</section>
<section class="seccion texto">
  {cabecera_seccion("06", "Reproducibilidad", "Todo abierto")}
  <p>El proceso completo (rastreo, limpieza, clasificación, análisis y esta web) son scripts de Python sin servicios
  de pago, <a href="{REPO_URL}">publicados en GitHub</a> con licencia MIT junto con los datos necesarios para
  rehacer el análisis. La web es estática: no llama a ningún servicio ni usa inteligencia artificial al visitarla.
  Los datos resultantes están <a href="datos.html">publicados en abierto</a>.</p>
  <p><a class="boton secundario claro" href="{REPO_URL}">Ver el código en GitHub ↗</a></p>
</section>""", banda=banda_m, ruta="metodologia.html"))

    # --- Datos abiertos ---
    columnas = ["portal", "portal_nombre", "fuente", "id", "nombre", "url", "clase_ia", "sector",
                "actor", "confianza", "motivo", "clase_reglas"]
    with (WEB / "datos" / "reutilizaciones-clasificadas.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        for k, r in ia.items():
            x = items[k]
            w.writerow([x["portal"], P[x["portal"]]["nombre"], x["fuente"], x["id"], x["nombre"],
                        x["url"], r["clase"], r["sector"], r["actor"], r["confianza"], r["motivo"],
                        x["clasificacion"]])
    with (WEB / "datos" / "portales.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portal", "nombre", "ambito", "territorio", "url", "rastros", "uso_estimado",
                    "uso_min", "uso_max"])
        for n, p in G["ranking"]:
            d = P[p]
            w.writerow([p, d["nombre"], d["ambito"], d["territorio"], d["url"], d["encontrados"],
                        n, d["uso_min"], d["uso_max"]])
    shutil.copy(PROC / "resultados.json", WEB / "datos" / "resultados.json")

    def tam(p):
        kb = (WEB / "datos" / p).stat().st_size / 1024
        return f"{kb / 1024:.1f} MB".replace(".", ",") if kb > 1024 else f"{kb:.0f} KB"
    descargas = [
        ("reutilizaciones-clasificadas.csv", "Cada rastro leído por la IA: portal, fuente, enlace, veredicto, sector, "
         "tipo de reutilizador, confianza y el motivo de la decisión."),
        ("portales.csv", f"Los {G['portales']} portales con sus cifras y su margen de error."),
        ("resultados.json", "Resultados completos por portal y fuente, con los recuentos de cada categoría."),
        ("buscador.json", "Los casos con su prueba, en el formato compacto que usa el buscador."),
    ]
    lista_d = "".join(f"<li><a class='descarga-nombre' href='datos/{n}' download>{n}</a><span class='tam'>{tam(n)}</span>"
                      f"<p>{t}</p></li>" for n, t in descargas)
    banda_d = """<section class="banda"><p class="antetitulo">Datos abiertos</p><h1>Un proyecto sobre reutilización publica sus datos</h1>
<p class="entradilla-banda">Todo se puede descargar y reutilizar libremente citando la fuente
(<a href="https://creativecommons.org/licenses/by/4.0/deed.es">CC BY 4.0</a>).</p></section>"""
    (WEB / "datos.html").write_text(pagina(
        "Datos abiertos · La Huella del Dato",
        "Descarga los datos de este proyecto en CSV y JSON, con licencia CC BY 4.0.",
        f"""<section class="seccion"><ul class="descargas">{lista_d}</ul></section>
<section class="seccion texto">
  {cabecera_seccion("", "Sellos", "Sellos para los portales")}
  <p>Cada portal tiene un sello SVG en <code>sellos/&lt;portal&gt;.svg</code>, con el código para insertarlo en su
  ficha.</p>
  {cabecera_seccion("", "Código", "Código fuente")}
  <p>Todo el proceso, con las instrucciones de la IA y los datos para reproducirlo, está en
  <a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a> (licencia MIT).</p>
  {cabecera_seccion("", "Cita", "Cómo citar")}
  <p class="cita-bloque">Molero Jiménez, G. (2026). <i>La Huella del Dato: quién reutiliza los datos públicos
  españoles</i>. Universidad Miguel Hernández de Elche. {BASE_URL}</p>
</section>""", banda=banda_d, ruta="datos.html"))

    (WEB / "estilo.css").write_text(CSS)
    (WEB / ".vercelignore").write_text(".*\n")  # nunca publicar ficheros ocultos (p. ej., estado de herramientas)
    print("web generada en", WEB)
    tam_total = sum(f.stat().st_size for f in WEB.rglob("*") if f.is_file())
    print(f"  {sum(1 for f in WEB.rglob('*.html'))} páginas, {tam_total / 1e6:.1f} MB en total")
    print(f"  buscador.json: {(WEB / 'datos' / 'buscador.json').stat().st_size / 1e6:.1f} MB, {len(filas_b)} casos")


if __name__ == "__main__":
    main()
