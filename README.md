# CNITP · Página de inicio

Sitio estático del Consejo Nacional de Investigaciones Tanatológicas y Psicológicas,
publicado en Cloudflare Pages por subida directa (sin integración con GitHub).

## Estructura

| Ruta | Qué es |
|---|---|
| `Main.dc.html`, `assets/`, `support.js`, `vendor/` | Exportación original del diseño (maqueta de referencia, usa React). Ver `README-exportacion.md`. |
| `src/main.js` | JS del sitio sin dependencias: selector de áreas, mariposa del hero, contadores. |
| `scripts/build.py` | Convierte la exportación en el sitio estático optimizado. |
| `dist/` | **Sitio listo para publicar.** Es lo que se sube a Cloudflare Pages. |
| `REVISION.md` | Revisión de buenas prácticas y lo que ya se aplicó. |

## Construir

Requiere Python 3 con Pillow (`pip install pillow`).

```bash
python3 scripts/build.py                                  # usa https://cnitp.pages.dev
python3 scripts/build.py --site-url https://tudominio.mx  # si cambia el dominio
```

Si se vuelve a exportar el diseño, reemplazar `Main.dc.html` y `assets/` y correr el build.

## Publicar en Cloudflare Pages (subida directa)

1. Comprimir el **contenido** de `dist/` (no la carpeta):
   `python3 -c "import shutil; shutil.make_archive('cnitp-sitio','zip','dist')"`
2. `dash.cloudflare.com` → Workers & Pages → proyecto `cnitp` → *Create new deployment* → subir el zip.

## Ver localmente

```bash
python3 -m http.server -d dist 8000   # http://localhost:8000
```
