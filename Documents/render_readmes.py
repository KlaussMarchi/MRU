#!/usr/bin/env python3
"""Renderiza os READMEs de Calibration e Main em HTML local, sem recursos de rede.

Uso, a partir da raiz do MRU:
    python3 Documents/render_readmes.py
    python3 Documents/render_readmes.py --check

Dependências de geração: Markdown e beautifulsoup4.
Os HTML gerados abrem diretamente no navegador, sem essas dependências.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import markdown
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    ROOT / "Calibration/README.md",
    ROOT / "Hardware/Embedded/Main/README.md",
)

CSS = """
:root {
  --paper:#ffffff; --canvas:#eef2f2; --ink:#19313b; --muted:#546b73;
  --accent:#08776b; --accent-soft:#e7f4ef; --line:#dce5e5;
  --code:#112c38; --gold:#a96b17; --radius:14px;
}
* { box-sizing:border-box }
html { scroll-behavior:smooth; scroll-padding-top:28px }
body { margin:0; background:var(--canvas); color:var(--ink);
  font:15px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif }
a { color:var(--accent); text-decoration-thickness:1px; text-underline-offset:3px }
a:hover { color:#034e46 }
button,a { -webkit-tap-highlight-color:transparent }
:focus-visible { outline:3px solid #c58c32; outline-offset:4px }
.skip { position:absolute; left:16px; top:-100px; background:white; padding:8px 16px; z-index:5 }
.skip:focus { top:12px }
.topbar { border-top:5px solid var(--accent); background:var(--paper); border-bottom:1px solid var(--line) }
.topbar-inner { max-width:1512px; margin:auto; padding:17px 36px;
  display:flex; align-items:center; justify-content:space-between; gap:20px }
.brand { display:flex; align-items:center; gap:12px; font-weight:800; letter-spacing:1px; color:var(--ink); text-decoration:none }
.brand-mark { display:grid; place-items:center; width:34px; height:34px; border-radius:8px; background:var(--accent); color:white;
  font-size:12px; letter-spacing:0 }
.topbar-label { font-size:11px; font-weight:700; letter-spacing:1.8px; text-transform:uppercase; color:var(--muted) }
.layout { max-width:1512px; margin:0 auto; padding:32px 36px 48px;
  display:grid; grid-template-columns:236px minmax(0,1fr); gap:32px; align-items:start }
.sidebar { position:sticky; top:24px; max-height:calc(100vh - 48px); overflow-y:auto;
  scrollbar-width:thin; padding:8px 14px 16px 0 }
.nav-label { display:block; color:var(--muted); font-size:10px; font-weight:800; letter-spacing:1.8px;
  text-transform:uppercase; margin:0 0 12px 12px }
.toc { display:flex; flex-direction:column; gap:3px }
.toc a { display:flex; gap:10px; color:var(--muted); text-decoration:none; font-size:12px; line-height:1.5;
  padding:8px 10px; border-left:2px solid transparent; border-radius:0 7px 7px 0 }
.toc a:hover,.toc a[aria-current="location"] { color:var(--accent); background:var(--accent-soft); border-left-color:var(--accent) }
.toc-number { flex:0 0 18px; color:#829598; font-size:10px; line-height:1.9; font-variant-numeric:tabular-nums }
.toc a.sub { padding-left:24px; font-size:11px }
.nav-related { border-top:1px solid var(--line); margin:20px 0 0 12px; padding-top:18px; font-size:12px }
.nav-related a { display:block; margin-top:6px; font-weight:600 }
main { min-width:0; background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); overflow:hidden;
  box-shadow:0 7px 28px #183b3e05 }
.hero { padding:38px 40px 32px; border-bottom:1px solid var(--line);
  background:linear-gradient(120deg,#f4faf7 0%,white 75%); position:relative }
.eyebrow { display:flex; align-items:center; gap:9px; font-size:10px; letter-spacing:2px; text-transform:uppercase;
  color:var(--accent); font-weight:800; margin-bottom:13px }
.eyebrow::before { content:""; width:7px; height:7px; border-radius:50%; background:var(--accent) }
h1 { font-size:clamp(29px,3.5vw,43px); line-height:1.17; letter-spacing:-1.5px; margin:0 0 16px; font-weight:800 }
.deck { color:var(--muted); max-width:760px; line-height:1.8; margin:0; font-size:15px }
.deck strong { color:var(--ink) }
.actions { display:flex; gap:10px; flex-wrap:wrap; margin-top:24px }
.button { border:1px solid var(--line); border-radius:7px; padding:8px 13px; color:var(--ink); text-decoration:none;
  font-family:inherit; font-size:12px; font-weight:600; line-height:1.5; background:white; cursor:pointer }
.button:hover { background:var(--accent-soft); border-color:#b9d8cf; color:var(--accent) }
.button.primary { background:var(--accent); border-color:var(--accent); color:white }
.prose { padding:10px 40px 36px; overflow-wrap:break-word }
.prose p { margin:18px 0 }
.prose h2,.prose h3 { scroll-margin-top:24px; color:var(--ink); line-height:1.4; }
.prose h2 { font-size:22px; letter-spacing:-.5px; margin:42px 0 18px; padding-top:25px; border-top:1px solid var(--line) }
.prose h2:first-of-type { border-top:0; padding-top:0; margin-top:30px }
.prose h3 { font-size:19px; margin:32px 0 15px; padding:13px 17px; border-left:3px solid var(--accent);
  border-radius:0 7px 7px 0; background:#f1f7f5; letter-spacing:-.25px }
.prose ul,.prose ol { padding-left:24px; margin:16px 0 }
.prose li { padding-left:3px; margin:9px 0 }
.prose li::marker { color:var(--accent); font-weight:700 }
.prose strong { font-weight:700 }
code { font: .87em/1.5 "SFMono-Regular",Consolas,"Liberation Mono",monospace; background:#edf2f3; color:#234651;
  border-radius:4px; padding:2px 5px; overflow-wrap:anywhere }
pre { background:var(--code); color:#e2f0f2; border:1px solid #173c49; border-radius:10px;
  padding:21px 22px; overflow:auto; margin:22px 0; line-height:1.7; tab-size:4; scrollbar-width:thin }
pre code { padding:0; background:none; color:inherit; border-radius:0; font-size:12px; white-space:pre; overflow-wrap:normal }
.table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:10px; margin:22px 0;
  scrollbar-width:thin; background:white }
table { width:100%; border-collapse:collapse; text-align:left; font-size:13px; line-height:1.7 }
th { background:#e9f2ef; color:#24544c; font-weight:700; font-size:11px; letter-spacing:.3px; padding:13px 15px;
  border-bottom:1px solid #ccdfd8; vertical-align:top }
td { padding:15px; border-bottom:1px solid var(--line); vertical-align:top }
tbody tr:last-child td { border-bottom:0 }
tbody tr:nth-child(even) { background:#f9fbfb }
tbody tr:hover { background:#f0f7f4 }
td:first-child { font-weight:500; min-width:125px }
td code,th code { font-size:11px; background:#eaf0f1 }
table.wide { min-width:790px }
table.wide th:first-child { width:21% }
table.wide th:nth-child(2) { width:16% }
table.wide th:nth-child(3) { width:37% }
table.wide th:last-child { width:26% }
.doc-footer { padding:22px 40px; border-top:1px solid var(--line); background:#fafcfc;
  font-size:12px; color:var(--muted); display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px }
.doc-footer a { font-weight:600 }
@media (max-width:1100px) {
  .layout { grid-template-columns:205px minmax(0,1fr); padding:24px; gap:24px }
  .hero { padding:30px } .prose { padding:6px 30px 28px } .doc-footer { padding:20px 30px }
}
@media (max-width:780px) {
  .topbar-inner { padding:14px 20px } .topbar-label { font-size:9px; letter-spacing:1px }
  .layout { display:block; padding:16px 12px 28px }
  .sidebar { position:static; max-height:none; padding:0; margin-bottom:16px; border:1px solid var(--line);
    border-radius:10px; background:white }
  .sidebar details { padding:12px 16px }
  .sidebar summary { cursor:pointer; font-size:12px; color:var(--accent); font-weight:700 }
  .sidebar details:not([open]) .nav-label { display:none }
  .sidebar details[open] .nav-label { margin-top:18px }
  .toc { max-height:260px; overflow:auto }
  .nav-related { display:none }
  .hero { padding:26px 22px } h1 { letter-spacing:-1px }
  .deck { font-size:14px } .prose { padding:4px 20px 26px; font-size:14px }
  .prose h2 { font-size:20px; margin-top:32px } .prose h3 { font-size:17px }
  pre { padding:17px; border-radius:8px } pre code { font-size:11px }
  .table-wrap { margin:18px 0 } table:not(.wide) { min-width:540px }
  .doc-footer { padding:18px 22px }
}
@media (min-width:781px) { .sidebar summary { display:none } }
@media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto } }
@media print {
  @page { size:A4; margin:14mm }
  body { background:white; color:#111; font-size:10pt; line-height:1.55 }
  .topbar,.sidebar,.actions,.skip,.doc-footer { display:none !important }
  .layout { display:block; padding:0; max-width:none }
  main { border:0; border-radius:0; box-shadow:none; overflow:visible }
  .hero { padding:0 0 16px; background:white }
  h1 { font-size:26pt } .eyebrow { font-size:8pt } .deck { font-size:10pt }
  .prose { padding:0; font-size:10pt }
  .prose h2 { font-size:15pt; padding-top:14px; margin-top:24px; break-after:avoid }
  .prose h3 { font-size:12pt; break-after:avoid; background:#f4f6f6 }
  .table-wrap { overflow:visible; border-radius:0 }
  table,table.wide,table:not(.wide) { min-width:0; font-size:8pt; width:100%; table-layout:fixed }
  th { font-size:8pt } th,td { padding:7px; min-width:0; overflow-wrap:anywhere }
  thead { display:table-header-group } tr { break-inside:avoid }
  td code,th code { font-size:7.5pt }
  pre { background:#f1f4f4; border-color:#d6dede; color:#111; overflow:visible; padding:12px }
  pre code { font-size:7pt; white-space:pre-wrap; overflow-wrap:anywhere }
  a { color:#175c54; text-decoration:none }
}
"""

SCRIPT = """
const menu = document.querySelector('.sidebar details');
const media = matchMedia('(min-width: 781px)');
function adaptMenu() { menu.open = media.matches; }
adaptMenu();
media.addEventListener('change', adaptMenu);
document.querySelector('[data-print]').addEventListener('click', () => window.print());
const links = [...document.querySelectorAll('.toc a')];
const headings = links.map(link => document.getElementById(link.hash.slice(1)));
function markSection() {
  let current = headings[0];
  for (const heading of headings) {
    if (heading.getBoundingClientRect().top <= 110) current = heading;
  }
  for (const link of links) {
    if (current && link.hash === '#' + current.id) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}
let ticking = false;
addEventListener('scroll', () => {
  if (!ticking) requestAnimationFrame(() => { markSection(); ticking = false; });
  ticking = true;
}, {passive:true});
markSection();
"""


def slug(text: str) -> str:
    clean = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")


def relative_url(path: Path, base: Path) -> str:
    return quote(os.path.relpath(path, base), safe="/")


def render(source: Path) -> str:
    raw = source.read_text(encoding="utf-8")
    soup = BeautifulSoup(
        markdown.markdown(raw, extensions=["tables", "fenced_code", "sane_lists"]),
        "html.parser",
    )
    title_node = soup.find("h1")
    if title_node is None:
        raise ValueError(f"Título ausente: {source}")
    title = title_node.get_text()
    title_node.decompose()
    deck = soup.find("p")
    if deck is None:
        raise ValueError(f"Introdução ausente: {source}")
    deck["class"] = "deck"
    deck_html = str(deck.extract())

    # Os READMEs usam parágrafos em negrito como títulos. No HTML, esses
    # mesmos textos viram seções sem alterar o Markdown original.
    for paragraph in soup.find_all("p", recursive=False):
        nodes = [node for node in paragraph.contents if str(node).strip()]
        if len(nodes) == 1 and getattr(nodes[0], "name", None) == "strong":
            text = paragraph.get_text()
            if text.endswith(".") or len(text) > 140:
                continue
            paragraph.name = "h3" if re.match(r"^\d+\s*·", text) else "h2"
            paragraph.strong.unwrap()

    toc = []
    used_ids: set[str] = set()
    for index, heading in enumerate(soup.find_all(["h2", "h3"]), start=1):
        text = heading.get_text(" ", strip=True)
        base = slug(text)
        identifier = base
        suffix = 2
        while identifier in used_ids:
            identifier = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(identifier)
        heading["id"] = identifier
        depth = "sub" if heading.name == "h3" else ""
        toc.append(
            f'<a class="{depth}" href="#{identifier}">'
            f'<span class="toc-number" aria-hidden="true">{index:02d}</span>'
            f'<span>{html.escape(text)}</span></a>'
        )

    for index, table in enumerate(soup.find_all("table"), start=1):
        if len(table.select("thead th")) >= 4:
            table["class"] = "wide"
        wrapper = soup.new_tag(
            "div",
            attrs={
                "class": "table-wrap",
                "role": "region",
                "aria-label": f"Tabela {index} — role horizontalmente se necessário",
                "tabindex": "0",
            },
        )
        table.wrap(wrapper)
        for th in table.select("thead th"):
            th["scope"] = "col"
    for pre in soup.find_all("pre"):
        pre["tabindex"] = "0"
        pre["aria-label"] = "Código ou diagrama; role horizontalmente se necessário"

    # Navegação entre os dois documentos abre a versão HTML.
    generated_sources = {path.resolve() for path in SOURCES}
    for anchor in soup.find_all("a", href=True):
        link = urlsplit(anchor["href"])
        if link.scheme or link.netloc or not link.path:
            continue
        target = (source.parent / unquote(link.path)).resolve()
        if target in generated_sources:
            anchor["href"] = relative_url(target.with_suffix(".html"), source.parent)
            if link.fragment:
                anchor["href"] += "#" + link.fragment

    other = next(path for path in SOURCES if path != source)
    other_label = "Firmware · ESP32-S3" if other == SOURCES[1] else "Pipeline de calibração"
    related = relative_url(other.with_suffix(".html"), source.parent)
    md_url = relative_url(source, source.parent)
    category = "Calibração · processamento offline" if source == SOURCES[0] else "Firmware · processamento embarcado"
    path_label = source.parent.relative_to(ROOT).as_posix()
    content = str(soup)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="{html.escape(title)} — arquivos, fluxo de dados e funcionamento dos algoritmos do MRU.">
<title>{html.escape(title)} · Documentação MRU</title>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#conteudo">Ir para o conteúdo</a>
<header class="topbar"><div class="topbar-inner">
<a class="brand" href="#inicio" aria-label="MRU — início"><span class="brand-mark">M</span> MRU</a>
<span class="topbar-label">Documentação técnica</span>
</div></header>
<div class="layout">
<aside class="sidebar" aria-label="Navegação do documento">
<details open><summary>Navegar pelas seções</summary>
<span class="nav-label">Neste documento</span>
<nav class="toc" aria-label="Índice">{''.join(toc)}</nav>
</details>
<div class="nav-related">Continue a leitura<a href="{related}">{html.escape(other_label)} ↗</a></div>
</aside>
<main id="inicio">
<header class="hero">
<div class="eyebrow">{html.escape(category)}</div>
<h1>{html.escape(title)}</h1>
{deck_html}
<div class="actions">
<button class="button primary" type="button" data-print>Imprimir / salvar PDF</button>
<a class="button" href="{md_url}">Abrir Markdown</a>
<a class="button" href="{related}">{html.escape(other_label)} ↗</a>
</div>
</header>
<article class="prose" id="conteudo" aria-label="{html.escape(title)}">
{content}
</article>
<footer class="doc-footer"><span>MRU / {html.escape(path_label)}</span>
<a href="#inicio">Voltar ao início ↑</a></footer>
</main>
</div>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Confere se os HTML correspondem aos Markdown.")
    args = parser.parse_args()
    outdated = []
    for source in SOURCES:
        output = source.with_suffix(".html")
        content = render(source)
        if args.check:
            if not output.exists() or output.read_text(encoding="utf-8") != content:
                outdated.append(str(output.relative_to(ROOT)))
        else:
            output.write_text(content, encoding="utf-8")
            print(f"Gerado: {output.relative_to(ROOT)}")
    if outdated:
        parser.exit(1, "HTML ausente ou desatualizado: " + ", ".join(outdated) + "\n")
    if args.check:
        print("Os dois HTML correspondem aos README.md.")


if __name__ == "__main__":
    main()
