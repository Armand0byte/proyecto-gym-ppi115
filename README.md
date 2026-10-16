# RayNovik — Proyecto PPI115

Sitio estático de apoyo para principiantes en el gimnasio. HTML, CSS y JavaScript,
con guías de rutinas, alimentación y suplementación.

## Estado del sitio

- 19 páginas de contenido, contacto por redes, landing de una guía PDF gratuita y privacidad.
- Favicons, navegación, fuentes de los artículos y ajustes para pantallas pequeñas.
- Metadatos, datos estructurados y sitemap con las rutas de las páginas organizadas por sección.
- Integración de Analytics preparada. Permanece desactivada hasta añadir su ID real de GA4.
- Search Console admite su etiqueta de verificación cuando se incorpora el código real de Google.

El prefijo `TPI115 - 2026 -` de los títulos se conserva por la indicación de la
página 8 de los lineamientos. La asignatura y el nombre del repositorio siguen
siendo PPI115. Los títulos para compartir conservan la marca y el tema del contenido.

## Revisar localmente

Abre `index.html` con Live Server de VS Code. También puedes ejecutar desde la raíz:

```bash
python -m http.server 8000
```

Visita `http://localhost:8000/`. Las guías de las subcarpetas incluyen un elemento
`base` que dirige sus recursos a la raíz del proyecto.

## Configurar servicios

La configuración se encuentra en `config/sitio.json`. Los dos identificadores de
Google están vacíos intencionadamente: los proporciona la cuenta del equipo.

Desde la raíz del proyecto, con Python 3:

```bash
python herramientas/configurar_sitio.py
```

Opciones disponibles:

- `--url`: dirección HTTPS pública del sitio, conservando la subcarpeta si existe.
- `--analytics`: identificador de medición real, que comienza por `G-`.
- `--verification`: solo el valor `content` de la etiqueta de verificación de Search Console.

Puedes editar los valores en `config/sitio.json` y ejecutar el comando sin opciones.
El programa actualiza los metadatos estáticos, la etiqueta de verificación del
inicio, `js/configuracion.js`, el sitemap, los robots y la página 404. Solo requiere
la biblioteca estándar de Python. No inicia sesión, acepta términos ni publica el sitio.

El archivo HTML de cada página debe tener título y descripción. Al agregar una
página, vuelve a ejecutar el configurador para incluirla en el sitemap.

### Google Analytics

1. En la cuenta de Google del equipo, crea o selecciona una propiedad GA4 para RayNovik.
2. Crea un flujo web con la dirección pública definitiva.
3. Copia el ID de medición al campo `analyticsId` y ejecuta el configurador.
4. Publica los cambios, acepta la medición en la página y comprueba el informe
   en tiempo real o Tag Assistant.

El código común está en las 19 páginas. Cuando hay ID real, el visitante puede
aceptar o rechazar la medición y cambiar su elección en el pie. La etiqueta de Google
solo carga después de aceptar. Se registran las páginas y los eventos propios
`descargar_guia` y `visitar_red_social`; no se envían los textos de búsquedas como eventos.
La implementación no habilita publicidad personalizada ni Google Signals.

Una prueba local de la integración no demuestra que la propiedad de Google ya
reciba datos. La validación de recepción se realiza después de configurar y publicar.

### Search Console

1. Añade una propiedad de **prefijo de URL** con la dirección pública completa del proyecto.
2. Selecciona verificación mediante etiqueta HTML.
3. Copia únicamente su valor `content` al campo `searchConsoleVerification`.
4. Ejecuta el configurador y publica la actualización del inicio.
5. Pulsa Verificar en Search Console y conserva la etiqueta después de verificar.
6. Envía `sitemap.xml`, inspecciona el inicio y las secciones, y guarda las evidencias.

## Publicación en GitHub Pages

Integra el cambio a `main` y selecciona en el repositorio:

`Settings → Pages → Deploy from a branch → main → /(root) → Save`.

La dirección configurada es `https://armand0byte.github.io/proyecto-gym-ppi115/`.
Si cambia, actualiza `siteUrl` y ejecuta el configurador antes de publicar.
El archivo `.nojekyll` permite servir los archivos estáticos directamente.

### Ubicación efectiva de robots.txt

Google lee **un robots por dominio/subdominio**, en la ruta `/robots.txt` del host.
Con la dirección de proyecto anterior, la ubicación efectiva es:

`https://armand0byte.github.io/robots.txt`

El archivo en `/proyecto-gym-ppi115/robots.txt` queda disponible como copia, pero
no regula el rastreo del host por estar en una subcarpeta.

La copia de `despliegue/raiz-del-dominio/robots.txt` se debe integrar en la raíz del
sitio de usuario `Armand0byte.github.io`, si se administra ese alojamiento. Antes
de reemplazar un robots existente, conserva sus reglas y añade la línea Sitemap
de este proyecto. Si se usa un dominio propio para RayNovik en su raíz, el robots
del proyecto queda en la ubicación adecuada al publicarlo allí.

El sitemap del proyecto se puede enviar directamente en Search Console aunque
la raíz del dominio se gestione por separado. No hace falta bloquear el contenido público.

## Comprobaciones posteriores a publicar

- Abrir el inicio, los tres catálogos, contacto y la descarga PDF.
- Comprobar el sitio desde un teléfono y verificar sus enlaces sociales.
- Confirmar que `sitemap.xml` contiene las URL públicas correctas.
- Validar los metadatos y los datos estructurados.
- Verificar recepción de Analytics y propiedad de Search Console.
- Guardar capturas de publicación, verificación e informes para el documento.

Publicación, indexación y posicionamiento son procesos distintos. La solicitud de
indexación y el sitemap no garantizan una aparición inmediata ni una posición concreta.

## Fuentes de contenido

Las guías de alimentación y suplementos enlazan fuentes de Harvard, NHS, USDA,
FDA, NIH ODS e ISSN. Se revisaron las afirmaciones para evitar dosis universales,
promesas de resultados y tablas nutricionales sin especificar el alimento o la preparación.
Los ejemplos de comidas son propuestas educativas del sitio, sin cantidades prescritas.
Las rutinas conservan sus fuentes de ACSM, ACE y otras referencias de técnica.
Las ilustraciones conservan los créditos y la licencia en `img/rutinas/`.

## Evidencias para el trabajo

El sitio no reemplaza el informe académico. El equipo debe incorporar sus
resultados reales de encuesta, público objetivo, investigación de palabras clave,
marca, dominio y redes, valor agregado, diseño, cronograma, tecnologías usadas,
conclusiones y evidencias de publicación y seguimiento.

La página de contacto utiliza los perfiles reales facilitados por el equipo;
no incluye un formulario de envío sin un servicio que lo reciba. La landing
ofrece una descarga funcional de una página sin registro.

## Documentación oficial de implementación

- https://developers.google.com/tag-platform/gtagjs
- https://developers.google.com/tag-platform/security/guides/consent
- https://support.google.com/webmasters/answer/9008080?hl=es
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/crawling/docs/robots-txt/create-robots-txt
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
