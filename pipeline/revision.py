"""Revisión manual a ciegas de la clasificación de la IA.

Elige 100 casos al azar entre los que juzgó la IA y los enseña en una página local
con el mismo texto que ella leyó, pero sin su veredicto. La persona que revisa responde
una sola pregunta, «¿usa de verdad los datos del portal?» (sí, no o no lo sé), y cada respuesta se guarda al momento, así que se puede
interrumpir y seguir otro día. Al final se compara con la IA.

Uso:
  python3 pipeline/revision.py              # abre la revisión en http://localhost:8766
  python3 pipeline/revision.py --resultado  # calcula el acierto de la IA
"""

import argparse
import collections
import csv
import json
import math
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import classify

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
DIR = PROC / "revision"
MUESTRA = DIR / "muestra.json"
RESPUESTAS = DIR / "respuestas.json"
RESULTADO = DIR / "resultado.json"
N = 100
SEMILLA = 20260923
PUERTO = 8766
FUENTES = {"github": "Código (GitHub)", "openalex": "Publicación científica", "wikipedia": "Wikipedia"}


def preparar_muestra():
    if MUESTRA.exists():
        return json.loads(MUESTRA.read_text())
    items = {classify.clave(x): x for x in map(json.loads, (PROC / "reutilizaciones.jsonl").open())}
    ia = {r["clave"]: r for r in map(json.loads, (PROC / "ia" / "sonnet.jsonl").open())}
    # "cita" no es una decisión de la IA (se asigna sola cuando no hay frase del artículo)
    juzgados = sorted(k for k, r in ia.items() if k in items and r["clase"] != "cita")
    # Muestra estratificada por fuente (34 + 33 + 33): así se puede medir el acierto en cada una y
    # ponderarlo por su peso real en la cifra estimada, dominada por Wikipedia.
    rnd = random.Random(SEMILLA)
    por_fuente = collections.defaultdict(list)
    for k in juzgados:
        por_fuente[items[k]["fuente"]].append(k)
    cupos = {"wikipedia": 34, "openalex": 33, "github": 33}
    elegidos = [k for f, n in cupos.items() for k in rnd.sample(por_fuente[f], n)]
    rnd.shuffle(elegidos)
    portales = {p["id"]: p for p in csv.DictReader((ROOT / "data" / "portales.csv").open())}
    resumenes = classify.resumen_openalex()
    frags = classify.fragmentos_github()
    casos = []
    for k in elegidos:
        x = dict(items[k])
        if x["fuente"] == "openalex":
            x["resumen"] = resumenes.get(x["id"])
        casos.append({"clave": k, "fuente": FUENTES[x["fuente"]], "portal": portales[x["portal"]]["nombre"],
                      "titulo": x["nombre"] or x["url"], "url": x["url"],
                      "texto": classify.describir(0, x, portales, frags).split("\n", 1)[1]})
    DIR.mkdir(parents=True, exist_ok=True)
    MUESTRA.write_text(json.dumps({"semilla": SEMILLA, "poblacion": len(juzgados),
                                   "poblacion_por_fuente": {f: len(v) for f, v in por_fuente.items()}, "casos": casos},
                                  ensure_ascii=False, indent=1))
    return json.loads(MUESTRA.read_text())


def leer_respuestas():
    return json.loads(RESPUESTAS.read_text()) if RESPUESTAS.exists() else {}


PAGINA = r"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>¿Usa los datos?</title>
<style>
:root{--f:#f7f6f2;--s:#fff;--t:#0f1422;--t2:#4b5263;--l:#e4e2dc;--n:#ff7a45;--o:#0b0f19;--si:#1f9d55;--no:#c0392b}
*{box-sizing:border-box}body{margin:0;background:var(--f);color:var(--t);font:17px/1.55 system-ui,-apple-system,sans-serif}
header{background:var(--o);color:#f2f3f5;padding:14px 24px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
.prog{flex:1;min-width:160px;height:8px;background:#2a3142;border-radius:9px;overflow:hidden}.prog i{display:block;height:100%;background:var(--n);width:0}
main{max-width:860px;margin:0 auto;padding:24px 20px 60px}
.ayuda{background:#fff4ec;border:1px solid #ffd9c4;border-radius:14px;padding:16px 20px;margin-bottom:20px;font-size:.95rem}
.ayuda p{margin:6px 0}.caso{background:var(--s);border:1px solid var(--l);border-radius:14px;padding:22px}
.meta{font-size:.9rem;color:var(--t2);margin:0}h1{font-size:1.5rem;line-height:1.25;margin:8px 0 4px}
.texto{background:var(--o);color:#dde2ea;padding:16px;border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere;
font:.85rem/1.65 ui-monospace,Menlo,monospace;max-height:45vh;overflow:auto;margin:14px 0}
mark{background:var(--n);color:#0b0f19;border-radius:3px;padding:0 2px}
.botones{display:grid;grid-template-columns:1fr 1fr 0.7fr;gap:12px;margin-top:16px}
button{font:700 1.05rem system-ui;padding:16px;border-radius:12px;border:2px solid var(--l);background:var(--s);color:var(--t);cursor:pointer}
button small{display:block;font-weight:400;font-size:.8rem;color:var(--t2);margin-top:4px}
.si:hover,.si.elegido{border-color:var(--si)}.si.elegido{background:var(--si);color:#fff}
.no:hover,.no.elegido{border-color:var(--no)}.no.elegido{background:var(--no);color:#fff}
.ns:hover,.ns.elegido{border-color:var(--t2)}.ns.elegido{background:var(--t2);color:#fff}
button.elegido small{color:#fff}
.nav{display:flex;justify-content:space-between;margin-top:14px}.nav button{padding:8px 14px;font-size:.9rem;font-weight:600}
.fin{background:var(--s);border:1px solid var(--l);border-radius:14px;padding:30px;text-align:center}
@media(max-width:600px){.botones{grid-template-columns:1fr}}
</style></head><body>
<header><b>¿Usa los datos?</b><span id="cuenta"></span><div class="prog"><i id="barra"></i></div><span id="guardado" style="font-size:.8rem;color:#9aa3b5"></span></header>
<main id="app"></main>
<script>
let C=[],R={},i=0;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function marcar(txt,terms){let h=esc(txt);terms.forEach(t=>{if(!t)return;const re=new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');h=h.replace(re,m=>'<mark>'+m+'</mark>')});return h}
async function cargar(){const d=await(await fetch('/datos')).json();C=d.casos;R=d.respuestas;i=C.findIndex(c=>!R[c.clave]);if(i<0)i=C.length;pintar()}
function pintar(){const n=Object.keys(R).length;document.getElementById('cuenta').textContent=n+' de '+C.length;
document.getElementById('barra').style.width=(100*n/C.length)+'%';const app=document.getElementById('app');
if(i>=C.length){app.innerHTML=`<div class="fin"><h1>¡Terminado!</h1><p>Has respondido ${n} casos. Ya puedes cerrar esta página y decírselo a Claude.</p><p><button onclick="i=0;pintar()">Repasar</button></p></div>`;return}
const c=C[i],r=R[c.clave];
app.innerHTML=`<div class="ayuda"><p><b>Qué hay que hacer:</b> leer el texto y responder si este proyecto o artículo <b>usa de verdad datos</b> del portal, o solo lo nombra.</p>
<p><b>Sí</b> → descarga datos, llama a su API o saca de él una cifra concreta (una población, una superficie, una temperatura…).<br>
<b>No</b> → solo lo nombra: una lista de enlaces, la portada del portal, una recomendación, un ejemplo.</p>
<p>La parte en <mark>naranja</mark> es donde aparece el portal. Si dudas, abre el original. Si no hay forma de saberlo, pulsa «No lo sé».</p></div>
<section class="caso"><p class="meta">Caso ${i+1} de ${C.length} · ${esc(c.fuente)}</p>
<h1>¿«${esc(c.titulo)}» usa datos de ${esc(c.portal)}?</h1><a href="${esc(c.url)}" target="_blank" rel="noopener">Abrir el original ↗</a>
<div class="texto">${marcar(c.texto,c.terminos)}</div>
<div class="botones"><button class="si ${r==='uso'?'elegido':''}" data-c="uso">Sí, usa sus datos<small>tecla S</small></button>
<button class="no ${r==='no'?'elegido':''}" data-c="no">No, solo lo nombra<small>tecla N</small></button>
<button class="ns ${r==='nose'?'elegido':''}" data-c="nose">No lo sé<small>tecla D</small></button></div>
<div class="nav"><button id="ant" ${i===0?'disabled':''}>← Anterior</button><button id="sig">Siguiente →</button></div></section>`;
app.querySelectorAll('[data-c]').forEach(b=>b.onclick=()=>responder(b.dataset.c));
document.getElementById('ant').onclick=()=>{i=Math.max(0,i-1);pintar()};document.getElementById('sig').onclick=()=>{i=Math.min(C.length,i+1);pintar()};
const t=app.querySelector('.texto mark');if(t)t.scrollIntoView({block:'center',behavior:'instant'});window.scrollTo(0,0)}
async function responder(clase){const c=C[i];R[c.clave]=clase;
const res=await fetch('/respuesta',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clave:c.clave,clase})});
document.getElementById('guardado').textContent=res.ok?'Guardado ✓':'¡No se pudo guardar!';i++;pintar()}
document.addEventListener('keydown',e=>{if(e.metaKey||e.ctrlKey||i>=C.length)return;const k=e.key.toLowerCase();
if(k==='s')responder('uso');else if(k==='n')responder('no');else if(k==='d')responder('nose');
else if(e.key==='ArrowLeft'){i=Math.max(0,i-1);pintar()}else if(e.key==='ArrowRight'){i=Math.min(C.length,i+1);pintar()}});
cargar();
</script></body></html>"""


class Servidor(BaseHTTPRequestHandler):
    def _enviar(self, cuerpo, tipo):
        datos = cuerpo.encode()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path == "/datos":
            m = json.loads(MUESTRA.read_text())
            terminos = {p["id"]: p["terminos_busqueda"].split("|")
                        for p in csv.DictReader((ROOT / "data" / "portales.csv").open())}
            casos = [dict({k: c[k] for k in ("clave", "fuente", "portal", "titulo", "url", "texto")},
                          terminos=terminos[c["clave"].split("|")[0]]) for c in m["casos"]]
            self._enviar(json.dumps({"casos": casos, "respuestas": {k: v["clase"] for k, v in leer_respuestas().items()}},
                                    ensure_ascii=False), "application/json; charset=utf-8")
        else:
            self._enviar(PAGINA, "text/html; charset=utf-8")

    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        claves = {c["clave"] for c in json.loads(MUESTRA.read_text())["casos"]}
        if d.get("clave") not in claves or d.get("clase") not in ("uso", "no", "nose"):
            self.send_response(400)
            self.end_headers()
            return
        r = leer_respuestas()
        r[d["clave"]] = {"clase": d["clase"], "momento": time.strftime("%Y-%m-%d %H:%M:%S")}
        RESPUESTAS.write_text(json.dumps(r, ensure_ascii=False, indent=1))
        self._enviar("{}", "application/json")

    def log_message(self, *a):
        pass


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - m), min(1, c + m)


def resultado():
    m = json.loads(MUESTRA.read_text())
    ia = {r["clave"]: r for r in map(json.loads, (PROC / "ia" / "sonnet.jsonl").open())}
    resp = leer_respuestas()
    pares = [(ia[c["clave"]]["clase"], resp[c["clave"]]["clase"]) for c in m["casos"] if c["clave"] in resp]
    juzgables = [(a, h) for a, h in pares if h != "nose"]
    aciertos = sum((a == "uso") == (h == "uso") for a, h in juzgables)
    uso_ia = [(a, h) for a, h in juzgables if a == "uso"]
    uso_hum = [(a, h) for a, h in juzgables if h == "uso"]
    # Lo que importa para las cifras: ¿coincide la frontera entre "uso" y "no uso"?
    binario = sum((a == "uso") == (h == "uso") for a, h in juzgables)
    fuente_de = {c["clave"]: c["clave"].split("|")[1] for c in m["casos"]}
    res_global = json.loads((PROC / "resultados.json").read_text())
    peso = collections.Counter()
    for d in res_global["portales"].values():
        for f, v in d["fuentes"].items():
            peso[f] += v["uso_estimado"]
    total_peso = sum(peso.values())
    por_fuente, pond, var = {}, 0.0, 0.0
    for f in ("wikipedia", "openalex", "github"):
        sub = [(ia[k]["clase"], resp[k]["clase"]) for k in resp if fuente_de.get(k) == f and resp[k]["clase"] != "nose"]
        sub = [("uso" if a == "uso" else "no", h) for a, h in sub]
        usos = [h for a, h in sub if a == "uso"]
        prec = wilson(sum(h == "uso" for h in usos), len(usos))
        por_fuente[f] = {"juzgables": len(sub), "acierto_clase": wilson(sum(a == h for a, h in sub), len(sub)),
                         "precision_uso": prec, "usos_ia": len(usos), "peso_en_estimacion": peso[f] / total_peso}
        if usos:
            w = peso[f] / total_peso
            pond += w * prec[0]
            var += w * w * prec[0] * (1 - prec[0]) / len(usos)
    margen = 1.96 * math.sqrt(var)
    out = {
        "por_fuente": por_fuente,
        "precision_uso_ponderada": (pond, max(0, pond - margen), min(1, pond + margen)),
        "revisados": len(pares), "no_se_puede_saber": len(pares) - len(juzgables), "juzgables": len(juzgables),
        "acierto_clase": wilson(aciertos, len(juzgables)),
        "acierto_uso_vs_no_uso": wilson(binario, len(juzgables)),
        "precision_uso": wilson(sum(h == "uso" for _, h in uso_ia), len(uso_ia)),
        "exhaustividad_uso": wilson(sum(a == "uso" for a, _ in uso_hum), len(uso_hum)),
        "confusion": {f"{a}→{h}": n for (a, h), n in collections.Counter(juzgables).items()},  # veredicto IA → persona
        "poblacion": m["poblacion"], "semilla": m["semilla"],
    }
    RESULTADO.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    f = lambda t: f"{100 * t[0]:.0f}% (IC 95%: {100 * t[1]:.0f}–{100 * t[2]:.0f}%)"
    print(f"Revisados {out['revisados']} de {N}; juzgables {out['juzgables']} ({out['no_se_puede_saber']} «no se puede saber»)")
    print(f"  Misma frontera uso / no uso:      {binario}/{len(juzgables)} = {f(out['acierto_uso_vs_no_uso'])}")
    print(f"  Precisión de «uso» de la IA:      {f(out['precision_uso'])}  (de lo que la IA llama uso, cuánto lo es)")
    print(f"  Exhaustividad de «uso»:           {f(out['exhaustividad_uso'])}  (de los usos reales, cuántos detecta)")
    for fu, v in out["por_fuente"].items():
        print(f"  {fu:<10} acierto {f(v['acierto_clase'])} · precisión de uso {f(v['precision_uso'])} "
              f"· pesa {100 * v['peso_en_estimacion']:.0f}% de la cifra")
    print(f"  Precisión de «uso» ponderada por el peso de cada fuente en los 55.457: {f(out['precision_uso_ponderada'])}")
    print("  Discrepancias (IA→persona):", {k: v for k, v in out["confusion"].items()
                                          if (k.split("→")[0] == "uso") != (k.split("→")[1] == "uso")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resultado", action="store_true")
    args = ap.parse_args()
    m = preparar_muestra()
    if args.resultado:
        resultado()
        return
    print(f"Muestra de {len(m['casos'])} casos sobre {m['poblacion']} juzgados por la IA. "
          f"Respuestas guardadas: {len(leer_respuestas())}")
    print(f"Abre http://localhost:{PUERTO}")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Servidor).serve_forever()


if __name__ == "__main__":
    main()
