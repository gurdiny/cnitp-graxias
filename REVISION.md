# Revisión · Inicio CNITP (borrador 1)

## Estado (2026-11-24)

Versión de producción en `dist/`, generada con `python3 scripts/build.py [--site-url https://…]`
a partir de `Main.dc.html` + `src/main.js`. Si se re-exporta el diseño, basta reemplazar
`Main.dc.html`/`assets/` y volver a correr el build.

**Aplicado:** viewport · sin React/support.js (JS propio de 10 KB) · ambas áreas en el DOM ·
menú "Tanatología/Psicología" abre su área (también por enlace directo `#psicologia`) ·
anuncio del cambio de área + `aria-controls` · h3→h4→h5 dentro de áreas · aviso de
"pestaña nueva" · salto al contenido · title/description/canonical/Open Graph/favicon ·
JSON-LD (organización + evento de la gala) · fuentes recortadas + preconnect · preload del
hero · fotos a WebP con srcset/sizes, width/height y lazy · mariposa se pausa fuera de
pantalla o con la pestaña oculta · `_headers` (CSP, seguridad, caché inmutable) · 404.html,
robots.txt, sitemap.xml · imagen OG 1200×630.

Medido en Chromium a 1440 px: carga inicial ~2.2 MB → ~0.55 MB; móvil ~0.46 MB; sin errores
de consola con la CSP aplicada; misma altura y aspecto que el original.

**Pendiente (requiere decisión del cliente):** aviso de privacidad propio (punto 3) y
destinos distintos para cada CTA (punto 4). Las URLs canónicas asumen
`https://cnitp.pages.dev`; si el proyecto o dominio es otro, reconstruir con `--site-url`.

---

Fecha: 2026-11-24 · Archivo revisado: `Main.dc.html` (1,314 líneas, 129 KB) + `assets/` (31 archivos, 1.8 MB)

> Contexto: es una exportación de una herramienta de diseño (`<x-dc>` + React + `support.js`).
> El README la marca como **maqueta de referencia**, no como código de producción. La revisión
> separa lo que hay que corregir en el diseño de lo que hay que resolver al pasarlo a producción.

## 1. Críticos

| # | Problema | Dónde | Arreglo |
|---|---|---|---|
| 1 | **Falta `<meta name="viewport">`**. En el celular la página se pinta a 980 px y se ve encogida; todos los `clamp()`/`vw` dejan de servir. | `<head>` | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
| 2 | **El contenido depende de JS**: React + ReactDOM + `support.js` (~197 KB) solo para pintar HTML estático. Malo para SEO, LCP y sin JS no hay página. | `<head>`, `<x-dc>` | En producción: HTML/CSS estático + ~3 KB de JS vanilla (mariposa, contadores, selector de área). |
| 3 | **Aviso de privacidad apunta a otro dominio** (`sonrieestasvivo.org`). Por la LFPDPPP el aviso debe ser del responsable (CNITP), y además se recaban datos en el formulario. | footer | Publicar aviso propio en el dominio del Consejo. |
| 4 | **Los 20 CTA van al mismo Google Form** (postulación a Los 100): "Solicitar fechas de talleres", "Quiero ser columnista", "Quiero información" (investigación), contacto… | todo el documento | Confirmar si es placeholder. Un formulario por intención, o el mismo con parámetro precargado (`?entry.XXX=talleres`) para saber de dónde viene cada lead. |
| 5 | **Navegación "Psicología" no muestra Psicología**: los enlaces "Tanatología" y "Psicología" (nav y footer) van a `#areas` y no cambian el estado; por defecto siempre se ve Tanatología. Existen `#tanatologia` y `#psicologia`, pero solo uno está en el DOM a la vez. | líneas 72-73, 860-861 | Enlazar a `#tanatologia` / `#psicologia` y leer el hash (`hashchange`) para fijar el área. |

## 2. SEO y metadatos

- `<title>` dice "CNITP · Inicio (borrador 4)" → título final (~60 car.).
- Sin `meta description`, `canonical`, Open Graph/Twitter (se va a compartir mucho por WhatsApp: sin `og:image` sale sin vista previa), ni favicon.
- Sin datos estructurados: `EducationalOrganization` (nombre, `alternateName` = INEST, teléfono, `sameAs`) y `Event` para la gala (19 dic 2026, 17:00, Colima 56, Roma) — candidato a rich result.
- Jerarquía de encabezados: dentro de "Área de Tanatología" (h3) las tarjetas Investigación/Talleres/Cursos/Certificaciones también son h3 → deberían ser h4.
- El contenido del área no seleccionada no existe en el DOM (`sc-if`): Google solo indexa una de las dos áreas. En producción, renderizar ambas y ocultar con CSS/`hidden`.

## 3. Rendimiento

**Imágenes (mayor ahorro):**
- 6 JPG de 1440×804 entre 104 y 226 KB, sin `srcset`/`sizes`. En móvil se descargan a tamaño completo. → AVIF/WebP en 640/960/1440 con `srcset`; ahorro estimado 50-70 %.
- Las 30 `<img>` no tienen atributos `width`/`height` (solo algunas usan `aspect-ratio` en CSS) → riesgo de CLS, sobre todo en la rejilla de logos.
- La imagen del hero (`abb1e…webp`) va como `background-image` en CSS: el navegador la descubre tarde. → `<link rel="preload" as="image" fetchpriority="high">` o convertirla en `<img>`.
- Logos de aliados: 360 px y hasta 28 KB para mostrarse a ~100 px de alto. Recomprimir (o SVG si existen); ~5 KB c/u es alcanzable.
- Logo OMSCI 480×480 (41 KB) repetido 3 veces a 180 px: ok en caché, pero bastan 360 px.

**Fuentes:**
- Se piden pesos que no se usan: Cinzel 700 y Cormorant 600. Usados de verdad: Cinzel 900, Cormorant italic 700, Montserrat 500/600/700/800.
- Falta `preconnect` a `fonts.googleapis.com` / `fonts.gstatic.com`. Mejor: auto-hospedar woff2 con subconjunto latino y `preload` de Montserrat 500 y Cinzel 900.
- URL recortada: `family=Cinzel:wght@900&family=Cormorant+Garamond:ital,wght@1,700&family=Montserrat:wght@500;600;700;800&display=swap`

**HTML/CSS:**
- 662 atributos `style=""`; el mismo bloque se repite decenas de veces (chips, `<li>` de listas, títulos Cinzel). Pasarlo a ~25 clases + variables CSS (`--verde-900: #071610`, `--oro: #B8923F`…) reduce el HTML ~60-70 % y hace el mantenimiento viable.

**JS (mariposa del hero):**
- El `requestAnimationFrame` corre para siempre: tras dibujarse (4.6 s) sigue repintando 2,400 puntos × 3 trazos por cuadro en la animación ambiental → consumo de batería en móvil. Opciones: detener tras N s, bajar a ~30 fps, o pausar con `document.hidden`.
- Cuando el canvas no es visible el loop sigue agendando rAF (solo se salta el pintado); mejor cancelar y reanudar desde el `IntersectionObserver`.
- `fit()` se llama cada 30 cuadros y recrea el gradiente; usar `ResizeObserver` en su lugar.
- `boot()` sondea el DOM hasta 60 veces con `setTimeout` porque el runtime monta tarde; en una versión estática basta `DOMContentLoaded`.
- `fmt()` de los contadores puede ser `n.toLocaleString('es-MX')`.

## 4. Accesibilidad

Bien resuelto: foco visible, `prefers-reduced-motion` respetado (CSS, canvas y contadores), objetivos táctiles ≥44 px, `aria-pressed` en el selector, `alt` descriptivos, canvas con `role="img"`. Contrastes medidos: crema/verde 10.8:1, oro/verde 7.7:1, texto verde sobre oro 6.4:1 — todos AA.

Pendiente:
- Falta enlace "Saltar al contenido".
- Los `target="_blank"` se anuncian de forma inconsistente (sí en video y formulario de contacto; no en barra superior, botón "Postular" ni CTA de tarjetas). Unificar con texto visible u oculto "(se abre en pestaña nueva)".
- Al cambiar de área no se anuncia nada ni se mueve el foco; el contenido nuevo aparece debajo sin aviso. Añadir `aria-controls` y una región con `aria-live="polite"` o mover el foco al h3 del área.
- Los botones del selector repiten el estado en texto ("Estás viendo esta área") además de `aria-pressed`: el lector lo dice dos veces. Marcar ese texto `aria-hidden="true"`.

## 5. Contenido

- Revisar fechas al publicar: cierre 5 dic y gala sábado 19 dic 2026 (verificado: es sábado).
- Footer: "Las fotografías de esta página son ilustrativas" — bien; si son generadas por IA, considerar decirlo explícitamente.
- `wa.me/5215541872203`: funciona; WhatsApp también acepta ya `525541872203` (sin el 1).

## 6. Prioridad sugerida

1. Viewport, aviso de privacidad propio, destinos de CTA, bug del enlace Psicología.
2. Metadatos + OG + JSON-LD.
3. Imágenes (AVIF/srcset/dimensiones) y fuentes.
4. Pasar a HTML/CSS estático con clases (elimina React/support.js).
5. Ajustes de accesibilidad y del loop del canvas.
