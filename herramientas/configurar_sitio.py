#!/usr/bin/env python3
"""Actualiza metadatos estáticos, sitemap e identificadores públicos de RayNovik.

Solo requiere Python 3. No inicia sesión ni publica el sitio.
"""
from argparse import ArgumentParser
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
import json
import posixpath
import re

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- INICIO SEO GENERADO -->'
END = '<!-- FIN SEO GENERADO -->'
PREFIX = 'TPI115 - 2026 - '
SOCIAL = [
    'https://www.instagram.com/raynovik_sv/',
    'https://www.facebook.com/share/18ZVRKMmEA/',
    'https://www.tiktok.com/@raynovik',
]
SECTIONS = {'rutinas': 'Rutinas', 'alimentacion': 'Alimentación', 'suplementacion': 'Suplementación'}

class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.description = ''
        self.base = ''
        self.in_title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'base': self.base = data.get('href', '')
        if tag == 'meta' and data.get('name') == 'description': self.description = data.get('content', '')

    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False

    def handle_data(self, text):
        if self.in_title: self.title += text

def validate(config):
    url = str(config.get('siteUrl', '')).strip()
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or re.search(r'[\s<>"\\]', url)):
        raise ValueError('siteUrl debe ser una dirección HTTPS completa, sin consultas, fragmentos ni espacios.')
    config['siteUrl'] = urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip('/') + '/', '', ''))
    analytics = str(config.get('analyticsId', '')).strip()
    if analytics and (not re.fullmatch(r'G-[A-Z0-9]{4,32}', analytics) or re.fullmatch(r'G-X+', analytics)):
        raise ValueError('analyticsId debe ser el identificador real de GA4, por ejemplo el que comienza por G-. Déjalo vacío si todavía no existe.')
    token = str(config.get('searchConsoleVerification', '')).strip()
    if token and not re.fullmatch(r'[A-Za-z0-9_-]{10,256}', token):
        raise ValueError('searchConsoleVerification debe contener solo el valor content de la etiqueta que proporciona Google.')
    config['analyticsId'] = analytics
    config['searchConsoleVerification'] = token
    return config

def breadcrumbs(name, title, base):
    parts = [{'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': base}]
    section = name.split('/')[0]
    if section in SECTIONS:
        parts.append({'@type': 'ListItem', 'position': 2, 'name': SECTIONS[section], 'item': base + section + '/' + section + '.html'})
        if name != section + '/' + section + '.html':
            parts.append({'@type': 'ListItem', 'position': 3, 'name': title.replace('RayNovik - ', '').replace(' | RayNovik', ''), 'item': base + name})
    elif name == 'contacto/escribenos.html':
        parts += [
            {'@type': 'ListItem', 'position': 2, 'name': 'Contacto', 'item': base + 'contacto.html'},
            {'@type': 'ListItem', 'position': 3, 'name': 'Escríbenos', 'item': base + name},
        ]
    else:
        label = {'contacto.html': 'Contacto', 'empieza.html': 'Empieza aquí', 'privacidad.html': 'Privacidad'}.get(name, title)
        parts.append({'@type': 'ListItem', 'position': 2, 'name': label, 'item': base + name})
    return parts

def collection_data(source, name, base):
    """Conserva las listas propias, tanto en @graph como dentro de mainEntity."""
    graph = []
    for raw in re.findall(r'<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source, re.I | re.S):
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError('JSON-LD no válido en ' + name) from error
        documents = document if isinstance(document, list) else [document]
        for item in documents:
            if isinstance(item, dict):
                nodes = item.get('@graph', [item])
                if isinstance(nodes, list):
                    graph.extend(node for node in nodes if isinstance(node, dict))
    collection = next((node for node in graph if node.get('@type') == 'CollectionPage'), {})
    lists = [node for node in graph if node.get('@type') == 'ItemList']
    main = collection.get('mainEntity', {})
    if isinstance(main, dict) and main.get('@type') == 'ItemList':
        lists.append(main)
    if not lists:
        return {}, []
    website = collection.get('isPartOf', {})
    website_id = website.get('@id', '') if isinstance(website, dict) else ''
    old_url = collection.get('url', '')
    old_base = website_id[:-8] if website_id.endswith('#website') else old_url[:-len(name)] if old_url.endswith(name) else ''

    def rebase(value):
        if isinstance(value, dict):
            return {key: rebase(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, str) and old_base and value.startswith(old_base):
            return base + value[len(old_base):]
        return value

    lists = rebase(lists)
    for index, item in enumerate(lists):
        item.setdefault('@id', base + name + ('#guias' if index == 0 else '#guias-' + str(index + 1)))
    reference = rebase(main).get('@id') if isinstance(main, dict) else None
    ids = [item['@id'] for item in lists]
    return {'publisher': {'@id': base + '#organization'},
            'mainEntity': {'@id': reference if reference in ids else ids[0]}}, lists

def resource(name, base_href, target):
    effective = urljoin('https://raynovik.invalid/' + name, base_href)
    directory = posixpath.dirname(urlsplit(effective).path).lstrip('/') or '.'
    return posixpath.relpath(target, directory)

def integrate(text, name, base_href):
    """Incluye una sola copia de los recursos comunes, respetando base y subcarpetas."""
    text = re.sub(r'\n[ \t]*<link\b[^>]*\bhref=["\'][^"\']*css/complementos\.css["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'\n[ \t]*<script\b[^>]*\bsrc=["\'][^"\']*js/(?:configuracion|medicion)\.js["\'][^>]*>\s*</script>', '', text, flags=re.I)
    text = re.sub(r'\s*</head>', '\n</head>', text, count=1, flags=re.I)
    common = [
        '    <link rel="stylesheet" href="' + resource(name, base_href, 'css/complementos.css') + '">',
        '    <script src="' + resource(name, base_href, 'js/configuracion.js') + '" defer></script>',
        '    <script src="' + resource(name, base_href, 'js/medicion.js') + '" defer></script>',
    ]
    return text.replace('</head>', '\n'.join(common) + '\n</head>', 1)

def metadata(name, title, description, config, source=''):
    base = config['siteUrl']
    url = base if name == 'index.html' else base + name
    image = base + 'img/social/raynovik-og.png'
    organization = {'@id': base + '#organization'}
    website = {'@id': base + '#website'}
    section = name.split('/')[0]
    catalog = name in [key + '/' + key + '.html' for key in SECTIONS]
    article = section in SECTIONS and not catalog
    page_type = 'CollectionPage' if catalog else 'ContactPage' if name in ['contacto.html', 'contacto/escribenos.html'] else 'WebPage'
    page = {'@type': page_type, '@id': url + '#webpage', 'url': url, 'name': title,
            'description': description, 'inLanguage': 'es-SV', 'isPartOf': website,
            'primaryImageOfPage': {'@type': 'ImageObject', 'url': image, 'width': 1200, 'height': 630}}
    graph = []
    if name == 'index.html':
        graph += [
            {'@type': 'Organization', **organization, 'name': 'RayNovik', 'url': base,
             'logo': {'@type': 'ImageObject', 'url': base + 'img/favicon.png', 'width': 512, 'height': 512}, 'sameAs': SOCIAL},
            {'@type': 'WebSite', **website, 'url': base, 'name': 'RayNovik', 'inLanguage': 'es-SV',
             'description': description, 'publisher': organization},
        ]
        page['about'] = organization
    else:
        page['breadcrumb'] = {'@id': url + '#breadcrumb'}
    if article:
        page['mainEntity'] = {'@id': url + '#article'}
    lists = []
    if catalog:
        extras, lists = collection_data(source, name, base)
        page.update(extras)
    graph.append(page)
    graph.extend(lists)
    if article:
        graph.append({'@type': 'Article', '@id': url + '#article', 'headline': title,
                      'description': description, 'image': image, 'inLanguage': 'es-SV',
                      'author': organization, 'publisher': organization,
                      'mainEntityOfPage': {'@id': url + '#webpage'}})
    if name != 'index.html':
        graph.append({'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': breadcrumbs(name, title, base)})
    data = {'@context': 'https://schema.org', '@graph': graph}
    fields = [
        ('property', 'og:type', 'article' if article else 'website'),
        ('property', 'og:site_name', 'RayNovik'), ('property', 'og:locale', 'es_SV'),
        ('property', 'og:title', title), ('property', 'og:description', description),
        ('property', 'og:url', url), ('property', 'og:image', image),
        ('property', 'og:image:type', 'image/png'), ('property', 'og:image:width', '1200'),
        ('property', 'og:image:height', '630'), ('property', 'og:image:alt', 'RayNovik: rutinas, alimentación y suplementación para principiantes.'),
        ('name', 'twitter:card', 'summary_large_image'), ('name', 'twitter:title', title[:70]),
        ('name', 'twitter:description', description[:200]), ('name', 'twitter:image', image),
        ('name', 'twitter:image:alt', 'RayNovik: guías para empezar en el gimnasio.'),
    ]
    lines = [START, '    <link rel="canonical" href="' + escape(url, quote=True) + '">',
             '    <meta name="theme-color" content="#0d0e12">']
    lines += ['    <meta ' + attribute + '="' + key + '" content="' + escape(value, quote=True) + '">' for attribute, key, value in fields]
    if name == 'index.html' and config['searchConsoleVerification']:
        lines.append('    <meta name="google-site-verification" content="' + config['searchConsoleVerification'] + '">')
    lines += ['    <script type="application/ld+json">', json.dumps(data, ensure_ascii=False, indent=2), '    </script>', END]
    return '\n'.join(lines)

def remove_old_metadata(text):
    text = re.sub(r'\n[ \t]*' + re.escape(START) + r'.*?' + re.escape(END) + r'[ \t]*\n?', '\n', text, flags=re.S)
    text = re.sub(r'\s*<link\b[^>]*\brel=["\']canonical["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'\s*<meta\b[^>]*(?:\bproperty=["\']og:[^"\']+["\']|\bname=["\'](?:twitter:[^"\']+|google-site-verification|theme-color)["\'])[^>]*>', '', text, flags=re.I)
    text = re.sub(r'\s*<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>.*?</script>', '', text, flags=re.I | re.S)
    return text

def configure(config):
    pages = sorted(path for path in ROOT.rglob('*.html') if path.name != '404.html')
    prepared = []
    for file in pages:
        name = file.relative_to(ROOT).as_posix()
        text = file.read_text(encoding='utf-8')
        head = Head(text)
        title = re.sub(r'^TPI115\s*-\s*2026\s*-\s*', '', head.title).strip()
        if not title or not head.description:
            raise ValueError('Falta título o descripción en ' + name)
        text = re.sub(r'<title>.*?</title>', '<title>' + escape(PREFIX + title) + '</title>', text, count=1, flags=re.S)
        if not re.search(r'<meta\b[^>]*\bname=["\']keywords["\']', text, re.I):
            keywords = {
                'contacto.html': 'contacto RayNovik, redes sociales RayNovik, sugerencias para guías de gimnasio',
                'contacto/escribenos.html': 'formulario de contacto RayNovik, consultas sobre gimnasio, sugerencias de entrenamiento',
                'empieza.html': 'guía gratuita para empezar en el gimnasio, primeros pasos fitness, RayNovik',
                'privacidad.html': 'privacidad RayNovik, medición opcional de visitas, preferencias de Analytics',
            }.get(name, title.replace(' | RayNovik', '') + ', RayNovik')
            text = text.replace('</title>', '</title>\n    <meta name="keywords" content="' + escape(keywords, quote=True) + '">', 1)
        source = text
        text = remove_old_metadata(text)
        text = integrate(text, name, head.base)
        if 'prefix="og:' not in text:
            text = text.replace('<html lang="es">', '<html lang="es" prefix="og: https://ogp.me/ns#">', 1)
        text = text.replace('</head>', '    ' + metadata(name, title, head.description, config, source) + '\n</head>', 1)
        prepared.append((file, text))
    # Solo escribe cuando la configuración y todos los documentos son válidos.
    for file, text in prepared:
        file.write_text(text, encoding='utf-8')
    (ROOT / 'config/sitio.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    public_config = {key: config[key] for key in ['siteUrl', 'analyticsId']}
    (ROOT / 'js/configuracion.js').write_text('/* Generado por herramientas/configurar_sitio.py. Identificadores públicos. */\nwindow.RAYNOVIK_CONFIG = Object.freeze(' + json.dumps(public_config, ensure_ascii=False, indent=2) + ');\n', encoding='utf-8')
    sitemap = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for file in pages:
        name = file.relative_to(ROOT).as_posix()
        SubElement(SubElement(sitemap, 'url'), 'loc').text = config['siteUrl'] if name == 'index.html' else config['siteUrl'] + name
    indent(sitemap, space='  ')
    ElementTree(sitemap).write(ROOT / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    robots = '# Publicar este archivo en /robots.txt de la raíz del dominio.\n# Si el sitio usa una subcarpeta, robots debe permanecer en la raíz del host.\nUser-agent: *\nAllow: /\n\nSitemap: ' + config['siteUrl'] + 'sitemap.xml\n'
    (ROOT / 'robots.txt').write_text(robots, encoding='utf-8')
    deployment = ROOT / 'despliegue/raiz-del-dominio'
    deployment.mkdir(parents=True, exist_ok=True)
    (deployment / 'robots.txt').write_text(robots, encoding='utf-8')
    error_page = '''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>TPI115 - 2026 - Página no encontrada | RayNovik</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;box-sizing:border-box;font:18px/1.6 Arial,sans-serif;color:#252525;background:#fff5f4}main{max-width:600px}h1{color:#a50b08;line-height:1.2}a{display:inline-block;padding:12px 20px;border-radius:8px;background:#a50b08;color:white;text-decoration:none}a:focus-visible{outline:3px solid #a1720c;outline-offset:4px}</style></head><body><main><p>RayNovik · Error 404</p><h1>Esta página no está disponible.</h1><p>Puede que el enlace haya cambiado. Desde el inicio puedes encontrar las guías de rutinas, alimentación y suplementación.</p><a href="''' + escape(config['siteUrl'], quote=True) + '''">Ir al inicio de RayNovik</a></main></body></html>'''
    (ROOT / '404.html').write_text(error_page, encoding='utf-8')
    print('Preparadas ' + str(len(pages)) + ' páginas, sitemap y robots.')
    print('Analytics: ' + ('configurado; requiere consentimiento y validación en línea.' if config['analyticsId'] else 'pendiente del ID real de GA4.'))
    print('Search Console: ' + ('etiqueta incorporada; verifica después de publicar.' if config['searchConsoleVerification'] else 'pendiente del código de verificación.'))

def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='URL pública de la raíz del proyecto, con HTTPS.')
    parser.add_argument('--analytics', help='ID real de medición GA4; una cadena vacía lo desactiva.')
    parser.add_argument('--verification', help='Valor content de la etiqueta de verificación de Search Console.')
    arguments = parser.parse_args()
    config = json.loads((ROOT / 'config/sitio.json').read_text(encoding='utf-8'))
    if arguments.url is not None: config['siteUrl'] = arguments.url
    if arguments.analytics is not None: config['analyticsId'] = arguments.analytics
    if arguments.verification is not None: config['searchConsoleVerification'] = arguments.verification
    try:
        configure(validate(config))
    except (ValueError, OSError) as error:
        parser.exit(2, 'No se aplicaron los cambios: ' + str(error) + '\n')

if __name__ == '__main__':
    main()
