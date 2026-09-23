"""Hoja de estilos y JavaScript de la web. Van aparte para que build_site.py se lea mejor.

Colores de datos validados con el validador de paleta (dataviz): naranja = uso real,
grises = lo que no es uso, rampa azul de un solo tono para magnitudes.
"""

CSS = r"""
@font-face { font-family: "Bricolage Grotesque"; src: url("fuentes/bricolage.woff2") format("woff2");
  font-weight: 400 800; font-display: swap; }
:root {
  --display: "Bricolage Grotesque", system-ui, -apple-system, "Segoe UI", sans-serif;
  --texto: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --fondo: #f7f6f2; --superficie: #ffffff; --tinta: #0f1422; --tinta-2: #4b5263; --tenue: #767c8b;
  --linea: #e4e2dc; --enlace: #1c5cab;
  --uso: #eb6834; --azul: #2a78d6; --pista: #e7edf6;
  --g-mencion: #9aa3b5; --g-cita: #bcc2ce; --g-estudio: #7f8799; --g-ruido: #d6d9e0; --seg-texto: #0f1422;
  --m1: #cde2fb; --m2: #86b6ef; --m3: #3987e5; --m4: #1c5cab; --m5: #0d366b; --m-sin: #e4e2dc;
  --tm-top: #1c5cab; --tm-resto: #b7d3f6; --tm-zoom: #256abf; --tm-resto-tinta: #0f1422;
  --oscuro: #0b0f19; --oscuro-2: #151c2c; --o-tinta: #f2f3f5; --o-tinta-2: #aab2c3; --naranja: #ff7a45;
  --radio: 14px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fondo: #0d1017; --superficie: #151a24; --tinta: #eef0f4; --tinta-2: #b4bac6; --tenue: #8d94a3;
    --linea: #262c38; --enlace: #86b6ef;
    --uso: #d95926; --azul: #3987e5; --pista: #1d2433;
    --g-mencion: #5b6478; --g-cita: #4a5163; --g-estudio: #6b7389; --g-ruido: #3a4050; --seg-texto: #ffffff;
    --m1: #1f3350; --m2: #1c5cab; --m3: #3987e5; --m4: #86b6ef; --m5: #cde2fb; --m-sin: #262c38;
    --tm-top: #3987e5; --tm-resto: #2a3b57; --tm-zoom: #256abf; --tm-resto-tinta: #eef0f4;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
body { margin: 0; background: var(--fondo); color: var(--tinta); font: 17px/1.6 var(--texto);
  -webkit-font-smoothing: antialiased; }
a { color: var(--enlace); text-underline-offset: 3px; }
h1, h2, h3 { font-family: var(--display); letter-spacing: -0.02em; line-height: 1.08; }
img { max-width: 100%; }
:focus-visible { outline: 3px solid var(--naranja); outline-offset: 2px; }
.saltar { position: absolute; left: -9999px; }
.saltar:focus { left: 8px; top: 8px; background: #fff; color: #000; padding: 8px; z-index: 10; }
.solo-lector { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.solo-impresion { display: none; }

/* --- Zona oscura: cabecera + portada/banda --- */
.oscuro { background: var(--oscuro); color: var(--o-tinta); position: relative; overflow: hidden; }
.oscuro a { color: var(--o-tinta); }
.cabecera { position: relative; z-index: 3; display: flex; flex-wrap: wrap; gap: 12px 28px; align-items: center;
  justify-content: space-between; max-width: 1180px; margin: 0 auto; padding: 18px 24px; }
.marca { display: inline-flex; align-items: center; gap: 10px; font: 700 1.1rem var(--display);
  text-decoration: none; letter-spacing: -0.01em; }
.logo { width: 28px; height: 28px; color: var(--naranja); flex: none; }
.cabecera nav { display: flex; flex-wrap: wrap; gap: 4px 22px; }
.cabecera nav a { text-decoration: none; color: var(--o-tinta-2); font-size: 0.95rem; padding: 4px 0; }
.cabecera nav a:hover { color: var(--o-tinta); text-decoration: underline; }

.hero { position: relative; min-height: min(76vh, 720px); display: flex; align-items: center; }
#constelacion { position: absolute; inset: 0; width: 100%; height: 100%; }
.hero::before { content: ""; position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background: linear-gradient(90deg, rgba(11,15,25,.94) 0%, rgba(11,15,25,.82) 42%, rgba(11,15,25,.18) 78%, rgba(11,15,25,0) 100%); }
.hero::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 120px; z-index: 1;
  pointer-events: none; background: linear-gradient(0deg, var(--oscuro), transparent); }
.hero-texto { position: relative; z-index: 2; max-width: 1180px; width: 100%; margin: 0 auto; padding: 48px 24px 88px; }
.hero-texto > * { max-width: 640px; }
.antetitulo { font: 600 0.8rem/1.4 var(--texto); letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--naranja); margin: 0 0 18px; }
.antetitulo a { color: inherit; }
.hero h1 { font-size: clamp(2.4rem, 6vw, 4.6rem); font-weight: 800; margin: 0 0 28px; }
.hero-cifra { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; margin: 0 0 20px; }
.hero-cifra b { font: 800 clamp(3.2rem, 9vw, 6.4rem)/1 var(--display); letter-spacing: -0.04em; color: #fff; }
.hero-cifra span { font-size: 1.1rem; color: var(--o-tinta-2); max-width: 22ch; line-height: 1.35; }
.hero-leyenda { font-size: 0.95rem; color: var(--o-tinta-2); line-height: 1.7; }
.hero-leyenda b { color: #fff; }
.punto-uso, .punto-resto { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  margin: 0 7px 0 2px; vertical-align: 0; }
.punto-uso { background: var(--naranja); box-shadow: 0 0 10px var(--naranja); }
.punto-resto { background: #6c7489; margin-left: 10px; }
.acciones { display: flex; flex-wrap: wrap; gap: 12px; margin: 32px 0 0; }
.boton { display: inline-flex; align-items: center; gap: 8px; background: var(--naranja); color: #0b0f19 !important;
  font: 700 0.98rem var(--texto); text-decoration: none; padding: 13px 22px; border-radius: 999px; border: 0;
  cursor: pointer; transition: transform .15s ease, box-shadow .15s ease; }
.boton:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(255,122,69,.35); }
.boton.secundario { background: transparent; color: var(--o-tinta) !important; box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.3); }
.boton.secundario:hover { box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.7); }
.boton.secundario.claro { color: var(--tinta) !important; box-shadow: inset 0 0 0 1.5px var(--linea); }

.banda { position: relative; z-index: 2; max-width: 1180px; margin: 0 auto; padding: 40px 24px 64px; }
.banda h1 { font-size: clamp(2.1rem, 5vw, 3.8rem); font-weight: 800; margin: 0 0 20px; max-width: 20ch; }
.entradilla-banda { font-size: 1.15rem; color: var(--o-tinta-2); max-width: 62ch; margin: 0; }
.entradilla-banda a { color: var(--o-tinta); }
.banda-cifras { display: flex; flex-wrap: wrap; gap: 24px 64px; align-items: flex-end; }
.banda-cifras .hero-cifra b { font-size: clamp(3rem, 8vw, 5.2rem); }
.banda-dl { display: flex; flex-wrap: wrap; gap: 16px 40px; margin: 0 0 24px; }
.banda-dl dt { font-size: 0.8rem; color: var(--o-tinta-2); }
.banda-dl dd { margin: 2px 0 0; font: 700 1.5rem var(--display); }

/* Cómo funciona */
.como { position: relative; z-index: 2; background: linear-gradient(180deg, var(--oscuro) 0%, var(--oscuro-2) 100%);
  border-top: 1px solid rgba(255,255,255,.07); }
.como-dentro { max-width: 1180px; margin: 0 auto; padding: 56px 24px 72px; }
.como h2 { font-size: clamp(1.6rem, 3.4vw, 2.4rem); font-weight: 800; margin: 0 0 36px; max-width: 26ch; }
.pasos { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.paso { position: relative; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.09);
  border-radius: var(--radio); padding: 22px 22px 24px; }
.paso:not(:last-child)::after { content: ""; position: absolute; top: 40px; right: -16px; width: 14px; height: 14px;
  z-index: 1; background: no-repeat center / contain url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 14 14'%3E%3Cpath d='M2 7h9M7.5 3.5 11 7l-3.5 3.5' fill='none' stroke='%23ff7a45' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"); }
.paso-cab { display: flex; align-items: center; justify-content: space-between; }
.paso-num { font: 800 0.85rem var(--display); display: inline-grid; place-items: center; width: 28px; height: 28px;
  border-radius: 50%; background: var(--naranja); color: #0b0f19; }
.icono { width: 34px; height: 34px; color: var(--o-tinta-2); }
.icono .relleno-uso { fill: var(--naranja); stroke: var(--naranja); }
.paso:last-child .icono { color: var(--naranja); }
.paso h3 { font-size: 1.3rem; margin: 18px 0 10px; color: #fff; }
.paso-cifra { margin: 0 0 10px; }
.paso-cifra b { display: block; font: 800 2.2rem/1 var(--display); letter-spacing: -0.03em; color: #fff; }
.paso:last-child .paso-cifra b { color: var(--naranja); }
.paso-cifra span { font-size: 0.85rem; color: var(--o-tinta-2); }
.paso-desc { margin: 0; font-size: 0.93rem; line-height: 1.5; color: var(--o-tinta-2); }
.paso { transition: border-color .2s ease, transform .2s ease; }
.paso:hover { border-color: rgba(255,122,69,.55); transform: translateY(-3px); }
@media (prefers-reduced-motion: reduce) { .paso, .paso:hover { transition: none; transform: none; } }
@media (max-width: 960px) {
  .pasos { grid-template-columns: 1fr 1fr; }
  .paso:nth-child(2)::after { display: none; }
}
@media (max-width: 560px) {
  .pasos { grid-template-columns: 1fr; gap: 22px; }
  .paso:not(:last-child)::after { display: block !important; top: auto; bottom: -19px; right: 50%;
    transform: translateX(50%) rotate(90deg); }
  .como-dentro { padding: 44px 16px 56px; }
}

/* --- Contenido --- */
main { max-width: 1180px; margin: 0 auto; padding: 0 24px 40px; }
.seccion { padding: 88px 0 0; }
.sec-cab { margin-bottom: 32px; max-width: 780px; }
.sec-cab .antetitulo { color: var(--uso); display: flex; gap: 12px; align-items: center; }
.sec-cab .antetitulo span { font-family: var(--display); color: var(--tenue); }
.sec-cab h2 { font-size: clamp(1.9rem, 4.2vw, 3rem); font-weight: 800; margin: 0 0 16px; }
.entradilla { font-size: 1.14rem; color: var(--tinta-2); margin: 0; max-width: 68ch; }
.sub { font-size: 1.2rem; margin: 40px 0 16px; }
.nota { color: var(--tinta-2); font-size: 0.93rem; max-width: 72ch; }
.texto p, .texto li { max-width: 72ch; }
.texto .sec-cab { margin-top: 0; }
.enlace-flecha { font-weight: 700; text-decoration: none; }
.enlace-flecha:hover { text-decoration: underline; }
.figura { margin: 0; }
.figura figcaption { font-size: 0.9rem; color: var(--tinta-2); margin-top: 12px; }
.dos { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px 56px; }
.dos .sub { margin-top: 8px; }
.tres { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }

/* Barras */
.barras { display: flex; flex-direction: column; gap: 10px; margin: 8px 0 16px; }
.barra { display: grid; grid-template-columns: minmax(130px, 38%) 1fr 64px; gap: 14px; align-items: center; }
.etq { font-size: 0.93rem; }
.pista { display: block; height: 14px; }
.relleno { display: block; height: 100%; width: var(--w); background: var(--azul); border-radius: 0 4px 4px 0; }
.val { font-size: 0.9rem; color: var(--tinta-2); text-align: right; font-variant-numeric: tabular-nums; }

/* Barra apilada */
.apilada { display: flex; gap: 2px; height: 64px; margin: 8px 0 14px; }
.seg { display: flex; align-items: center; padding: 0 14px; min-width: 3px; font: 700 0.95rem var(--texto);
  color: var(--seg-texto); white-space: nowrap; overflow: visible; }
.seg:first-child { border-radius: 8px 0 0 8px; }
.seg:last-child { border-radius: 0 8px 8px 0; }
.seg-uso { background: var(--uso); color: #0b0f19; }
.seg-mencion { background: var(--g-mencion); }
.seg-cita { background: var(--g-cita); }
.seg-estudio { background: var(--g-estudio); }
.seg-ruido { background: var(--g-ruido); }
.leyenda { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px 22px;
  font-size: 0.9rem; color: var(--tinta-2); }
.leyenda b { color: var(--tinta); font-weight: 600; margin-left: 4px; }
.muestra { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 7px; vertical-align: -1px; }
.muestra.tm-top { background: var(--tm-top); } .muestra.tm-resto { background: var(--tm-resto); }
.muestra.m1 { background: var(--m1); } .muestra.m2 { background: var(--m2); } .muestra.m3 { background: var(--m3); }
.muestra.m4 { background: var(--m4); } .muestra.m5 { background: var(--m5); }

/* Tarjetas de casos */
.casos { list-style: none; padding: 0; margin: 0; display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.casos-cuatro { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
.caso { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 18px 20px;
  display: flex; flex-direction: column; gap: 8px; }
.caso p { margin: 0; }
.caso-cab { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-size: 0.8rem; color: var(--tenue); }
.chip { font: 700 0.72rem var(--texto); letter-spacing: 0.05em; text-transform: uppercase; padding: 3px 9px; border-radius: 999px;
  background: var(--g-ruido); color: var(--tinta); }
.chip-uso { background: var(--uso); color: #0b0f19; }
.caso-titulo { font: 700 1.05rem/1.3 var(--display); letter-spacing: -0.01em; color: var(--tinta); text-decoration: none;
  overflow-wrap: anywhere; }
.caso-titulo:hover { text-decoration: underline; }
.caso-motivo { font-size: 0.94rem; }
.ia { font: 700 0.66rem var(--texto); border: 1px solid var(--linea); color: var(--tenue); border-radius: 4px;
  padding: 1px 5px; margin-right: 8px; vertical-align: 1px; }
.evidencia { font-size: 0.84rem; color: var(--tinta-2); border-left: 3px solid var(--linea); padding-left: 12px;
  font-style: italic; overflow-wrap: anywhere; }
.caso-pie { font-size: 0.82rem; color: var(--tenue); margin-top: auto !important; padding-top: 4px; }

/* Treemap */
.treemap, .mapa-svg, .linea { width: 100%; height: auto; display: block; }
.treemap rect { transition: opacity .15s; }
.treemap a:hover rect, .treemap a:focus rect { opacity: .82; }
.tm-top { fill: var(--tm-top); } .tm-resto { fill: var(--tm-resto); } .tm-zoom { fill: var(--tm-zoom); }
.tm-nombre { font-family: var(--display); font-weight: 700; fill: #fff; }
.tm-valor { fill: rgba(255,255,255,.85); font-variant-numeric: tabular-nums; }
.tm-txt-claro { fill: var(--tm-resto-tinta); }

/* Mapa */
.mapa-bloque { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 40px; align-items: start; }
.mapa-fig { margin: 0; }
.region { stroke: var(--fondo); stroke-width: 1.2; stroke-linejoin: round; transition: opacity .15s; }
.region.m1 { fill: var(--m1); } .region.m2 { fill: var(--m2); } .region.m3 { fill: var(--m3); }
.region.m4 { fill: var(--m4); } .region.m5 { fill: var(--m5); } .region.sin { fill: var(--m-sin); }
.mapa-svg a:hover .region, .mapa-svg a:focus .region { opacity: .75; }
.recuadro { fill: none; stroke: var(--linea); stroke-width: 1.5; }
.lista-ccaa { list-style: none; padding: 0; margin: 0; font-size: 0.92rem; counter-reset: c; }
.lista-ccaa li { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--linea); }
.lista-ccaa a { color: var(--tinta); text-decoration: none; }
.lista-ccaa a:hover { text-decoration: underline; }
.lista-ccaa b { font-variant-numeric: tabular-nums; }

/* Línea */
.rejilla { stroke: var(--linea); stroke-width: 1; }
.eje { fill: var(--tenue); font-size: 12px; font-variant-numeric: tabular-nums; }
.area { fill: var(--azul); opacity: .1; }
.trazo { fill: none; stroke: var(--azul); stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }
.punto { fill: var(--azul); stroke: var(--fondo); stroke-width: 2; }
.punto.hueco { fill: var(--fondo); stroke: var(--azul); }
.diana { fill: transparent; }
.etq-dato { fill: var(--tinta); font: 700 13px var(--texto); }

/* Así decide la IA */
.desglose { font-size: 1rem; color: var(--o-tinta-2); margin: -4px 0 18px; max-width: 560px; line-height: 1.55; }
.desglose b { color: #fff; font-weight: 700; }
.demo { display: flex; flex-direction: column; gap: 18px; }
.demo-fila { display: grid; grid-template-columns: minmax(0, 1.45fr) 40px minmax(0, 1fr); align-items: stretch;
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); overflow: hidden; }
.demo-entrada { background: var(--oscuro); color: #d5dae4; padding: 20px 22px; }
.demo-entrada pre { margin: 0; font: 0.8rem/1.6 ui-monospace, "SF Mono", Menlo, monospace; white-space: pre-wrap;
  overflow-wrap: anywhere; max-height: 260px; overflow: auto; }
.demo-rotulo { font: 700 0.72rem var(--texto); letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 12px; color: var(--tenue); }
.demo-entrada .demo-rotulo { color: var(--naranja); }
.demo-flecha { display: grid; place-items: center; font: 800 1.6rem var(--display); color: var(--uso); }
.demo-salida { padding: 20px 22px 20px 4px; }
.demo-salida p { margin: 0; }
.chip-grande { font-size: 0.85rem; padding: 6px 14px; }
.demo-salida dl { margin: 16px 0 0; display: grid; gap: 10px; }
.demo-salida dt { font-size: 0.75rem; color: var(--tenue); }
.demo-salida dd { margin: 1px 0 0; font-size: 0.97rem; }
.demo-salida dl div:first-child dd { font: 700 1.08rem/1.35 var(--display); }
.demo-enlace { margin-top: 14px !important; font-size: 0.88rem; }
.hechos { list-style: none; padding: 0; margin: 24px 0 8px; display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); }
.hechos li { border-top: 2px solid var(--uso); padding-top: 12px; }
.hechos b { display: block; font: 700 1rem var(--display); margin-bottom: 4px; }
.hechos span { font-size: 0.9rem; color: var(--tinta-2); }
.instrucciones { margin-top: 24px; background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 18px 22px; }
.instrucciones summary { font: 700 1.05rem var(--display); cursor: pointer; }
.instrucciones pre { font: 0.8rem/1.6 ui-monospace, Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere;
  background: var(--oscuro); color: #d5dae4; padding: 18px; border-radius: 10px; margin: 12px 0 0; }
@media (max-width: 760px) {
  .demo-fila { grid-template-columns: 1fr; }
  .demo-flecha { transform: rotate(90deg); padding: 6px 0; }
  .demo-salida { padding: 0 20px 20px; }
}

/* Empresas */
.empresas { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.empresa-portal { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 24px; }
.empresa-cifra { margin: 0; color: var(--tinta-2); font-size: 0.95rem; }
.empresa-cifra b { display: block; font: 800 3.2rem/1 var(--display); color: var(--tinta); letter-spacing: -0.03em; margin-bottom: 6px; }
.empresa-portal h3 { font-size: 1.15rem; margin: 18px 0 12px; }
.empresa-portal h3 a { color: var(--tinta); }
.chips { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.chips a { display: inline-block; font-size: 0.82rem; padding: 4px 10px; border-radius: 999px;
  background: var(--fondo); border: 1px solid var(--linea); color: var(--tinta-2); text-decoration: none; }
.chips a:hover { border-color: var(--uso); color: var(--tinta); }

/* Destacados */
.destacados { list-style: none; padding: 0; margin: 0; display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
.destacado { background: var(--oscuro); color: var(--o-tinta); border-radius: var(--radio); padding: 22px;
  display: flex; flex-direction: column; gap: 8px; }
.destacado p { margin: 0; font-size: 0.9rem; color: var(--o-tinta-2); }
.destacado .estrellas { font: 800 1.9rem/1 var(--display); color: var(--naranja); letter-spacing: -0.02em; }
.destacado-nombre { font: 700 1.02rem/1.3 var(--display); color: #fff; text-decoration: none; overflow-wrap: anywhere; }
.destacado-nombre:hover { text-decoration: underline; }
.destacado .usa { margin-top: auto; padding-top: 8px; font-size: 0.82rem; }
.destacado .usa a { color: var(--o-tinta); }

/* Organismos */
.accion { display: block; background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio);
  padding: 26px; color: var(--tinta); text-decoration: none; transition: border-color .15s, transform .15s; }
.accion:hover { border-color: var(--uso); transform: translateY(-2px); }
.accion h3 { font-size: 1.3rem; margin: 14px 0 8px; }
.accion p { margin: 0; color: var(--tinta-2); font-size: 0.95rem; }
.accion-num { font: 800 0.9rem var(--display); display: inline-grid; place-items: center; width: 30px; height: 30px;
  border-radius: 50%; background: var(--uso); color: #0b0f19; }
.sello-mini { display: block; margin-top: 8px; }

/* Ficha */
.claves { list-style: none; padding: 0; margin: 0; display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
.claves li { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 20px; }
.claves b { display: block; font: 800 1.7rem/1.1 var(--display); letter-spacing: -0.02em; margin-bottom: 8px; }
.claves span { color: var(--tinta-2); font-size: 0.93rem; }
.sello-bloque textarea { width: 100%; max-width: 760px; font: 0.85rem ui-monospace, Menlo, monospace; padding: 12px;
  border-radius: 10px; border: 1px solid var(--linea); background: var(--superficie); color: var(--tinta); display: block; margin-top: 6px; }

/* Tablas */
.tabla-envoltorio { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.95rem; }
.tabla th, .tabla td { text-align: left; padding: 12px; border-bottom: 1px solid var(--linea); vertical-align: middle; }
.tabla th { font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--tenue); font-weight: 600; }
.tabla .n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.tabla a { color: var(--tinta); font-weight: 600; text-decoration: none; }
.tabla a:hover { text-decoration: underline; }
.rango { color: var(--tinta-2); font-size: 0.85rem; }
.puesto { color: var(--tenue); font-family: var(--display); font-weight: 700; }
.sub-celda { display: block; font-size: 0.8rem; color: var(--tenue); }
.celda-barra { width: 28%; min-width: 120px; }
.ranking tbody tr:hover { background: var(--superficie); }

/* Metodología */
.embudo { list-style: none; padding: 0; margin: 0; display: grid; gap: 0; counter-reset: paso; }
.embudo li { display: grid; grid-template-columns: 220px 1fr; gap: 4px 32px; padding: 22px 0; border-bottom: 1px solid var(--linea);
  align-items: baseline; }
.embudo b { font: 800 2.6rem/1 var(--display); letter-spacing: -0.03em; grid-row: span 2; }
.embudo li:last-child b { color: var(--uso); }
.paso-titulo { font-weight: 700; font-size: 1.1rem; }
.paso-texto { color: var(--tinta-2); font-size: 0.95rem; max-width: 64ch; }

/* Buscador */
.filtros { display: grid; grid-template-columns: 2fr 1.3fr 1fr 1fr; gap: 12px; align-items: end; }
.campo { display: flex; flex-direction: column; gap: 6px; font-size: 0.8rem; font-weight: 600; color: var(--tinta-2); }
.campo input, .campo select { font: 1rem var(--texto); padding: 12px 14px; border-radius: 10px; border: 1px solid var(--linea);
  background: var(--superficie); color: var(--tinta); width: 100%; }
.campo input:focus, .campo select:focus { outline: 3px solid var(--naranja); outline-offset: 0; border-color: transparent; }
.cuenta { font: 700 1.1rem var(--display); margin: 24px 0 16px; }

/* Datos */
.descargas { list-style: none; padding: 0; margin: 0; display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.descargas li { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 22px; }
.descarga-nombre { font: 700 1.05rem var(--display); overflow-wrap: anywhere; }
.tam { margin-left: 10px; color: var(--tenue); font-size: 0.85rem; }
.descargas p { margin: 8px 0 0; color: var(--tinta-2); font-size: 0.93rem; }
.cita-bloque { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 18px; }
code { font: 0.9em ui-monospace, Menlo, monospace; background: var(--superficie); border: 1px solid var(--linea);
  padding: 1px 5px; border-radius: 5px; }

/* Pie */
.pie { margin-top: 96px; background: var(--oscuro); color: var(--o-tinta-2); font-size: 0.88rem; }
.pie-dentro { max-width: 1180px; margin: 0 auto; padding: 40px 24px 56px; }
.pie p { max-width: 80ch; margin: 8px 0; }
.pie a { color: var(--o-tinta); }
.marca-pie { display: flex; align-items: center; gap: 10px; font: 700 1.1rem var(--display); color: var(--o-tinta); }

/* Avisos (tooltip) */
#aviso { position: fixed; z-index: 50; pointer-events: none; max-width: 300px; background: var(--oscuro); color: #fff;
  font-size: 0.85rem; line-height: 1.4; padding: 8px 12px; border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,.25); }

@media (max-width: 860px) {
  .mapa-bloque { grid-template-columns: 1fr; }
  .lista-ccaa { columns: 2; column-gap: 24px; }
  .lista-ccaa li { break-inside: avoid; }
  .filtros { grid-template-columns: 1fr 1fr; }
  .campo-texto { grid-column: 1 / -1; }
  .embudo li { grid-template-columns: 1fr; }
  .embudo b { grid-row: auto; }
}
@media (max-width: 640px) {
  body { font-size: 16px; }
  .cabecera { padding: 14px 16px; }
  .hero-texto, .banda, main { padding-left: 16px; padding-right: 16px; }
  .hero::before { background: rgba(11,15,25,.62); }
  .seccion { padding-top: 64px; }
  .barra { grid-template-columns: 1fr 52px; gap: 4px 10px; }
  .barra .etq { grid-column: 1 / -1; }
  .apilada { height: 52px; }
  .seg span { display: none; }
  .casos { grid-template-columns: 1fr; }
  .lista-ccaa { columns: 1; }
  .celda-barra { display: none; }
}
@media print {
  .oscuro, .pie { background: none !important; color: #000 !important; }
  .oscuro a, .hero-cifra b, .banda-dl dd { color: #000 !important; }
  .cabecera nav, .acciones, .sello-bloque, #aviso, .saltar, .enlace-flecha { display: none !important; }
  .solo-impresion { display: block; font-size: 0.8rem; color: #555; }
  .entradilla-banda, .hero-cifra span, .banda-dl dt { color: #333 !important; }
  .seccion { padding-top: 28px; break-inside: avoid-page; }
  .caso, .claves li { break-inside: avoid; }
  body { background: #fff; font-size: 11pt; }
}
"""

JS_AVISOS = r"""(()=>{const t=document.getElementById('aviso');if(!t)return;
function ver(el,x,y){t.textContent=el.getAttribute('data-tip');t.hidden=false;const r=t.getBoundingClientRect();
let l=x+14,a=y+16;if(l+r.width>innerWidth-8)l=x-r.width-14;if(a+r.height>innerHeight-8)a=y-r.height-12;
t.style.left=Math.max(8,l)+'px';t.style.top=Math.max(8,a)+'px'}
document.addEventListener('pointermove',e=>{const el=e.target.closest&&e.target.closest('[data-tip]');if(el)ver(el,e.clientX,e.clientY);else t.hidden=true});
document.addEventListener('focusin',e=>{const el=e.target.closest&&e.target.closest('[data-tip]');if(el){const r=el.getBoundingClientRect();ver(el,r.left+r.width/2,r.bottom)}});
document.addEventListener('focusout',()=>{t.hidden=true});
addEventListener('scroll',()=>{t.hidden=true},{passive:true});})();"""

JS_CONSTELACION = r"""(()=>{const c=document.getElementById('constelacion');if(!c||!c.getContext)return;
const uso=+c.dataset.uso,n=uso+(+c.dataset.resto),ctx=c.getContext('2d');
const quieto=matchMedia('(prefers-reduced-motion: reduce)').matches;
let s=2026;const azar=()=>{s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
const cl=new Uint8Array(n);for(let i=0;i<uso;i++)cl[i]=1;
for(let i=n-1;i>0;i--){const j=Math.floor(azar()*(i+1)),v=cl[i];cl[i]=cl[j];cl[j]=v}
const jx=new Float32Array(n),jy=new Float32Array(n),re=new Float32Array(n);
for(let i=0;i<n;i++){jx[i]=azar()-.5;jy[i]=azar()-.5;re[i]=azar()}
let dpr=1,pts=null;
function medir(){dpr=Math.min(devicePixelRatio||1,2);const W=c.clientWidth,H=c.clientHeight;if(!W||!H)return;
c.width=W*dpr;c.height=H*dpr;const cols=Math.ceil(Math.sqrt(n*W/H)),filas=Math.ceil(n/cols),cw=W/cols,ch=H/filas;
pts=new Float32Array(2*n);for(let i=0;i<n;i++){pts[2*i]=((i%cols)+.5+jx[i]*.85)*cw*dpr;pts[2*i+1]=(Math.floor(i/cols)+.5+jy[i]*.85)*ch*dpr}}
function pintar(t){if(!pts)return;ctx.clearRect(0,0,c.width,c.height);const r=1.15*dpr;
ctx.fillStyle='rgba(150,162,186,.30)';for(let i=0;i<n;i++){if(cl[i]&&re[i]<t)continue;ctx.fillRect(pts[2*i]-r,pts[2*i+1]-r,2*r,2*r)}
ctx.fillStyle='#ff7a45';ctx.shadowColor='rgba(255,122,69,.8)';ctx.shadowBlur=6*dpr;ctx.beginPath();
for(let i=0;i<n;i++){if(cl[i]&&re[i]<t){ctx.moveTo(pts[2*i]+r*1.4,pts[2*i+1]);ctx.arc(pts[2*i],pts[2*i+1],r*1.4,0,6.2832)}}
ctx.fill();ctx.shadowBlur=0}
medir();
if(quieto){pintar(1)}else{let t0=null,hecho=false;const dur=2600,esp=500;
const paso=ts=>{if(hecho)return;if(t0===null)t0=ts;const k=Math.min(1,Math.max(0,(ts-t0-esp)/dur));pintar(1-Math.pow(1-k,3));if(k<1)requestAnimationFrame(paso);else hecho=true};
pintar(0);requestAnimationFrame(paso);setTimeout(()=>{if(!hecho){hecho=true;pintar(1)}},esp+dur+400)}
let rz;addEventListener('resize',()=>{clearTimeout(rz);rz=setTimeout(()=>{medir();pintar(1)},150)});})();"""

JS_COPIAR = r"""document.addEventListener('click',e=>{const b=e.target.closest('[data-copiar]');if(!b)return;
const ta=document.getElementById(b.dataset.copiar);ta.select();
(navigator.clipboard?navigator.clipboard.writeText(ta.value):Promise.reject()).catch(()=>document.execCommand('copy'))
.finally(()=>{const o=b.textContent;b.textContent='Copiado ✓';setTimeout(()=>b.textContent=o,1800)})});"""

JS_BUSCADOR = r"""(async()=>{const $=s=>document.querySelector(s);
const q=$('#q'),fp=$('#f-portal'),ff=$('#f-fuente'),fc=$('#f-clase'),out=$('#resultados'),cuenta=$('#cuenta'),mas=$('#mas');
let D;try{D=await(await fetch('datos/buscador.json')).json()}catch(e){cuenta.textContent='No se pudieron cargar los casos.';return}
Object.entries(D.portales).sort((a,b)=>a[1].localeCompare(b[1],'es')).forEach(([id,n])=>fp.add(new Option(n,id)));
const ps=new URLSearchParams(location.search);q.value=ps.get('q')||'';fp.value=ps.get('portal')||'';ff.value=ps.get('fuente')||'';
if(ps.has('clase'))fc.value=ps.get('clase');
const norm=s=>(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
const idx=D.filas.map(f=>norm([f[5],f[7],f[8],f[9],D.portales[f[0]],D.sectores[f[3]],D.actores[f[4]]].join(' ')));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>n.toLocaleString('es-ES');
function tarjeta(f){return `<li class="caso"><div class="caso-cab"><span class="chip chip-${esc(f[2])}">${esc(D.clases[f[2]])}</span>
<span class="caso-fuente">${esc(D.fuentes[f[1]])}${f[9]?' · '+esc(f[9]):''}</span></div>
<a class="caso-titulo" href="${esc(f[6])}" rel="noopener">${esc(f[5])}</a>
<p class="caso-motivo"><span class="ia">IA</span>${esc(f[7])}</p>${f[8]?`<p class="evidencia">«…${esc(f[8])}…»</p>`:''}
<p class="caso-pie"><a href="portales/${esc(f[0])}.html">${esc(D.portales[f[0]])}</a> · ${esc(D.sectores[f[3]]||f[3])} · ${esc(D.actores[f[4]]||f[4])}</p></li>`}
let res=[],vistos=0;
function pintar(){const trozo=res.slice(vistos,vistos+40);out.insertAdjacentHTML('beforeend',trozo.map(tarjeta).join(''));vistos+=trozo.length;mas.hidden=vistos>=res.length}
function filtrar(){const pal=norm(q.value.trim()).split(/\s+/).filter(Boolean);res=[];
for(let i=0;i<D.filas.length;i++){const f=D.filas[i];if(fp.value&&f[0]!==fp.value)continue;if(ff.value&&f[1]!==ff.value)continue;
if(fc.value&&f[2]!==fc.value)continue;if(pal.length&&!pal.every(w=>idx[i].includes(w)))continue;res.push(f)}
out.innerHTML='';vistos=0;pintar();cuenta.textContent=res.length?`${fmt(res.length)} ${res.length===1?'caso':'casos'}`:'Ningún caso con estos filtros';
const u=new URLSearchParams();if(q.value)u.set('q',q.value);if(fp.value)u.set('portal',fp.value);if(ff.value)u.set('fuente',ff.value);
if(fc.value!=='uso')u.set('clase',fc.value);history.replaceState(null,'',u.toString()?'?'+u:location.pathname)}
let esp;q.addEventListener('input',()=>{clearTimeout(esp);esp=setTimeout(filtrar,120)});
[fp,ff,fc].forEach(el=>el.addEventListener('change',filtrar));mas.addEventListener('click',pintar);filtrar();})();"""
