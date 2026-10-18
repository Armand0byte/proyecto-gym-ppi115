#!/usr/bin/env python3
"""Rastreo complementario de SEO. Solo requiere Python 3; no ejecuta Analytics.

Publicado: py herramientas/auditar_seo.py --salida ../auditoria-publicada
Local: py herramientas/auditar_seo.py --carpeta . --salida ../auditoria-local
Los informes se guardan fuera del sitio que se debe subir a Neocities.
"""
from argparse import ArgumentParser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
import csv
import json
import xml.etree.ElementTree as ET


class Documento(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.base = ""
        self.h1 = 0
        self.images = []
        self.links = []
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get("id"):
            self.ids.add(data["id"])
        if tag == "title":
            self.in_title = True
        if tag == "base":
            self.base = data.get("href", "")
        if tag == "h1":
            self.h1 += 1
        if tag == "meta":
            name = data.get("name", "").lower()
            if name == "description":
                self.description = data.get("content", "")
            if name == "robots":
                self.robots = data.get("content", "")
        if tag == "link" and "canonical" in data.get("rel", "").split():
            self.canonical = data.get("href", "")
        if tag == "img":
            self.images.append(data)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, text):
        if self.in_title:
            self.title += text


def descargar(url):
    request = Request(url, headers={"User-Agent": "RayNovikAuditoriaSEO/1.0"})
    try:
        with urlopen(request, timeout=35) as response:
            return response.status, response.read(), response.geturl()
    except HTTPError as error:
        return error.code, error.read(), url
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error).encode(), url


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://raynovik.neocities.org/")
    parser.add_argument("--carpeta", type=Path, help="Examinar una copia local sin peticiones externas.")
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    base = args.url.rstrip("/") + "/"
    root = args.carpeta.resolve() if args.carpeta else None
    output = args.salida.resolve()
    site_root = root or Path(__file__).resolve().parents[1]
    if output == site_root or site_root in output.parents:
        parser.error("La salida debe quedar fuera de la carpeta del sitio.")
    output.mkdir(parents=True, exist_ok=True)

    def obtener(url):
        if root is None:
            return descargar(url)
        path = urlsplit(url).path
        prefix = urlsplit(base).path
        name = unquote(path[len(prefix):]) if path.startswith(prefix) else ""
        file = (root / (name or "index.html")).resolve()
        if root not in file.parents or not file.is_file():
            return 404, b"", url
        return 200, file.read_bytes(), url

    status, sitemap, _ = obtener(urljoin(base, "sitemap.xml"))
    if status != 200:
        parser.error("No se pudo obtener sitemap.xml: HTTP " + str(status))
    urls = [item.text for item in ET.fromstring(sitemap).iter()
            if item.tag.endswith("}loc") and item.text]
    if not urls or any(not url.startswith(base) for url in urls):
        parser.error("El sitemap está vacío o contiene direcciones ajenas a --url.")
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(obtener, urls))
    docs = {}
    rows = []
    findings = []

    def issue(code, page, detail):
        findings.append({"comprobacion": code, "url": page, "detalle": detail})

    titles = defaultdict(list)
    descriptions = defaultdict(list)
    for url, (code, content, final_url) in zip(urls, responses):
        doc = Documento(content.decode("utf-8", errors="replace"))
        docs[url] = doc
        dimensions = sum(not image.get("width") or not image.get("height") for image in doc.images)
        rows.append({"url": url, "http": code, "url_final": final_url,
                     "titulo": doc.title.strip(), "descripcion": doc.description,
                     "canonical": doc.canonical, "h1": doc.h1, "imagenes": len(doc.images),
                     "imagenes_sin_dimensiones": dimensions})
        if code != 200:
            issue("http", url, "Respuesta HTTP " + str(code))
        if not doc.title.strip():
            issue("titulo_ausente", url, "No hay un título de página.")
        else:
            titles[doc.title.strip()].append(url)
        if not doc.description.strip():
            issue("descripcion_ausente", url, "No hay meta description.")
        else:
            descriptions[doc.description.strip()].append(url)
        if doc.canonical != url:
            issue("canonical", url, "El canonical no coincide con la URL del sitemap.")
        if "noindex" in doc.robots.lower():
            issue("noindex_en_sitemap", url, "Una página del sitemap declara noindex.")
        if doc.h1 != 1:
            issue("h1", url, "Cantidad de encabezados H1: " + str(doc.h1))
        missing_alt = [image.get("src", "") for image in doc.images if "alt" not in image]
        if missing_alt:
            issue("alt_ausente", url, ", ".join(missing_alt))
        if dimensions:
            issue("dimensiones_imagen", url,
                  str(dimensions) + " imágenes sin width y height explícitos; comprobar estabilidad visual.")
    duplicates = [{"titulo": title, "urls": pages} for title, pages in titles.items() if len(pages) > 1]
    for item in duplicates:
        for page in item["urls"]:
            issue("titulo_duplicado", page, item["titulo"])
    duplicate_descriptions = [{"descripcion": description, "urls": pages}
                              for description, pages in descriptions.items() if len(pages) > 1]
    for item in duplicate_descriptions:
        for page in item["urls"]:
            issue("descripcion_duplicada", page, item["descripcion"])

    # Solo se comprueban los destinos del mismo sitio; nunca se envían formularios.
    targets = {}
    anchors = []
    for url, doc in docs.items():
        for href in doc.links:
            resolved = urlsplit(urljoin(urljoin(url, doc.base), href))
            target = resolved._replace(fragment="", query="").geturl()
            if not target.startswith(base):
                continue
            if target == base + "index.html":
                target = base
            targets[target] = None
            if resolved.fragment:
                anchors.append((url, target, unquote(resolved.fragment)))
    extra = sorted(set(targets) - set(docs))
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = dict(zip(extra, pool.map(obtener, extra)))
    for target, (code, _, _) in checked.items():
        if code != 200:
            issue("enlace_interno", target, "El destino responde HTTP " + str(code))
    for url, target, fragment in anchors:
        if target in docs and fragment not in docs[target].ids:
            issue("ancla_inexistente", url, target + "#" + fragment)
    robots_status, robots, _ = obtener(urljoin(base, "robots.txt"))
    report = {
        "herramienta": "Rastreador SEO complementario de RayNovik",
        "version": "1.0", "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "sitio": base, "entorno": "copia local" if root else "sitio publicado",
        "alcance": "Páginas del sitemap, títulos, descripciones, canonical, H1, alt, dimensiones y enlaces internos. No mide tiempos de carga ni posiciones en Google.",
        "paginas": rows, "paginas_total": len(rows), "titulos_duplicados": duplicates,
        "descripciones_duplicadas": duplicate_descriptions, "hallazgos": findings,
        "destinos_internos_comprobados": len(targets), "robots_http": robots_status,
        "robots": robots.decode("utf-8", errors="replace")
    }
    (output / "rastreo-seo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, records in [("paginas.csv", rows), ("hallazgos.csv", findings)]:
        with (output / name).open("w", newline="", encoding="utf-8-sig") as file:
            fields = list(records[0]) if records else ["comprobacion", "url", "detalle"]
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

    def table(records, fields):
        header = "".join("<th>" + escape(field) + "</th>" for field in fields)
        body = "".join("<tr>" + "".join("<td>" + escape(str(record.get(field, ""))) + "</td>"
                                      for field in fields) + "</tr>" for record in records)
        return "<table><thead><tr>" + header + "</tr></thead><tbody>" + body + "</tbody></table>"
    html = """<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe del rastreador SEO RayNovik</title>
<style>body{font:16px/1.5 Arial,sans-serif;max-width:1250px;margin:32px auto;padding:0 20px;color:#222}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}th,td{border:1px solid #ccc;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#eee}h1{font-size:28px}@media print{thead{display:table-header-group}tr{break-inside:avoid}}</style><h1>Informe del rastreador SEO RayNovik</h1>"""
    html += "<p>Fecha UTC: " + escape(report["fecha_utc"]) + "<br>Sitio: " + escape(base)
    html += "<br>Entorno: " + escape(report["entorno"]) + "<br>Herramienta: " + escape(report["herramienta"]) + " 1.0</p>"
    html += "<p>" + escape(report["alcance"]) + "</p><p>Páginas: " + str(len(rows))
    html += ". Grupos de títulos duplicados: " + str(len(duplicates)) + ".</p>"
    html += "<h2>Resultados por página</h2>" + table(rows, ["url", "http", "titulo", "h1", "imagenes_sin_dimensiones"])
    html += "<h2>Hallazgos</h2>" + (table(findings, ["comprobacion", "url", "detalle"]) if findings else "<p>Sin hallazgos en las comprobaciones realizadas.</p>")
    html += "<h2>robots.txt</h2><pre>" + escape(report["robots"]) + "</pre></html>"
    (output / "rastreo-seo.html").write_text(html, encoding="utf-8")
    print(json.dumps({"paginas": len(rows), "titulos_duplicados": len(duplicates),
                      "hallazgos": len(findings), "salida": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
