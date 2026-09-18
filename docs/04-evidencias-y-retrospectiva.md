# Evidencias reales y apoyo para la retrospectiva

Regla de este documento: **solo se presenta como evidencia lo que realmente se ejecutó**. La Guía 5 lo exige, y una captura que no corresponda a una ejecución real es falsificación académica, no un detalle de forma.

## A. Capturas que deben salir de una ejecución real

| # | Captura | Cómo obtenerla (5 minutos) | Dónde va en la Guía |
|---|---|---|---|
| 1 | **GitHub Actions en verde** — ✅ hecha (`capturas/github-actions-ci.png`, run #1) | Ver sección B para repetirla | §3.3 (evidencia) y paso 3 de la demo |
| 2 | **`docker compose ps`** con los 4 servicios *healthy* | Con Docker abierto: `docker compose up -d` y `docker compose ps`. Captura la terminal o la pestaña *Containers* de Docker Desktop | Paso 1 de la demo |
| 3 | **Tablas en PostgreSQL** | `docker compose exec postgres psql -U ecoumb -c "\dt"` | Paso 2 de la demo |
| 4 | **Registro 201 / 409 en el navegador** | <http://localhost:5173/registro> → DevTools → *Network*: filas `register` con 201 y, al repetir, 409 | Paso 4–5 de la demo |
| 5 | **Home tras iniciar sesión y tras F5** | Login → Home con tu nombre → F5 | Paso 6 de la demo |
| 6 | **Swagger** | <http://localhost:8000/docs> | Paso 7 de la demo |
| 7 | **`pytest --cov`** | `cd backend && pytest --cov=app --cov-report=term-missing` | §3.3 |

Ya existen **capturas reales** de la ejecución en Docker en `docs/evidencias/capturas/` (PWA, Swagger y salidas de terminal), regenerables con `node scripts/capture_ui.mjs` y `node scripts/render_terminal.mjs`. Las de la PWA y Swagger son del navegador; las `term-*` son texto real de terminal dibujado sin edición y rotulado como tal. En `docs/evidencias/` hay además salidas de texto reales de las ejecuciones hechas durante el desarrollo (pruebas, cobertura, migración, prueba de humo, compose). Sirven como respaldo, pero **una captura propia de su ejecución vale más ante el docente**.

## B. Pipeline de GitHub Actions (ya ejecutado; cómo repetirlo)

El repositorio local está en `Tesis/GitHub/EcoUMB` y su remoto ya apunta a `git@github.com:PWA-UMB/EcoUMB.git` (rama `main`, sin commits todavía). Subirlo lo hace el equipo desde su propia sesión de GitHub: publicar código en un servicio externo es una decisión suya.

```bash
# El repositorio de GitHub debe estar VACÍO (sin README, .gitignore ni licencia).
cd C:\Users\cuent\Documents\Universidad\Tesis\GitHub\EcoUMB
git add -A
git commit -m "chore: estructura inicial del Sprint 1"
git push -u origin main
git switch -c develop && git push -u origin develop         # Git Flow
git switch -c feature/S1-06-auth develop                    # una rama de trabajo para el PR
```

**Estado:** el primer push (commit `9b5d3c6`) disparó el CI y los tres jobs terminaron en verde. GitHub muestra además una anotación de *deprecación de Node 20* en las acciones `checkout`/`setup-*`: es un aviso, no un fallo; se resuelve subiendo esas acciones a su versión más reciente en `.github/workflows/ci.yml`.

Después: GitHub → pestaña **Actions** → workflow **CI** → esperar los tres jobs (*Backend*, *Migraciones sobre PostgreSQL 16*, *Frontend*). Capturar la página del run con los tres en verde.

Si algún job falla, **no lo maquilles**: copia el log, corrígelo y vuelve a ejecutar. Los fallos típicos y su causa probable:
- *Backend / ruff*: diferencia de versión de ruff → `pip install -r backend/requirements-dev.txt` y `ruff format .`
- *Frontend / npm ci*: falta `frontend/package-lock.json` en el commit (no está en `.gitignore`).
- *Migraciones*: el único job que corre contra PostgreSQL 16; es el que valida el `downgrade` de los ENUM.

## C. Insumos para la retrospectiva (Guía §6)

La retrospectiva de la Guía §6 **ya está redactada** en `Guia5_SprintReview_EcoUMB_completado.docx` a partir de estos hechos y de los archivos del proyecto (incluido cómo se construyó y se revisó HERIS). Debe **leerla y confirmarla el equipo**: los hechos salen de documentos, fechas de commits y ejecuciones reales, pero el reparto de horas, los bloqueos personales y la comunicación solo los conocen ustedes. Falta el respaldo (acta o captura de la reunión).

**Hechos técnicos ocurridos durante la construcción**
- Se midió un problema de CORS al abrir la PWA en `127.0.0.1` y no en `localhost`; se amplió el valor por defecto de desarrollo.
- `pre-commit` detectó un `ci.yml` con YAML inválido (un `: ` sin comillas) y un orden de imports que dependía del directorio de ejecución: dos defectos que habrían roto el CI.
- El script de humo agotó el límite de 10 solicitudes/min de `/auth/*` en la segunda corrida seguida; el limitador funcionaba, el script estaba mal diseñado.
- El entorno local usa Python 3.14 mientras Docker y CI usan 3.12 (lo que dice el SAD): riesgo de "en mi máquina funciona".
- La migración sobre PostgreSQL no se pudo probar hasta tener Docker operativo.
- Dependencias: `@eslint/js` sin versión fija trajo la v10 y rompió la instalación; se fijó a la serie 9.

**Preguntas de la Guía con datos para discutir**
1. *¿Qué funcionó bien?* Pruebas escritas antes del código, arquitectura hexagonal verificada por una prueba automática, CI/pre-commit atrapando errores antes de integrar.
2. *¿Qué obstáculos hubo?* (los de arriba; sumen los propios)
3. *¿La estimación de 47 h de 60 h disponibles se ajustó?* Solo el equipo tiene sus horas reales: registren cuánto tomó realmente cada historia S1-01…S1-09 frente a lo estimado (4, 4, 5, 6, 4, 8, 6, 6, 4 h).
4. *¿Qué cambiar para el Sprint 2?* Propuestas para valorar: fijar Python 3.12 en local (pyenv/venv), levantar Docker desde el día 1 del sprint, mover el refresh token a cookie `httpOnly`, y ensayar la demo completa el día anterior.

Cuando la hayan hecho, peguen las respuestas reales en la Guía §6 y adjunten el acta o una captura de la reunión.
