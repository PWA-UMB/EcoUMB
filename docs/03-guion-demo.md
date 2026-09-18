# Guion de la demostración — Sprint 1 (Guía 5 §5)

Ensayarlo completo el día anterior. La Guía advierte que cualquier fallo en vivo afecta la calificación.

**Preparación (antes de la clase):** Docker Desktop encendido y *en verde*; `cp .env.example .env` hecho; `docker compose build` ya ejecutado (así el arranque en vivo dura segundos); una pestaña con el pipeline de GitHub Actions abierta; el correo de la demo **no** registrado aún.

| # | Paso de la Guía | Comando / acción | Qué debe verse | Evidencia ya generada |
|---|---|---|---|---|
| 1 | Levantar el entorno | `docker compose up -d` y luego `docker compose ps` | `postgres`, `redis`, `api` y `web` en *healthy/running* | — (requiere Docker) |
| 2 | Migraciones y reversibilidad | `docker compose exec api alembic downgrade base` → `docker compose exec api alembic upgrade head` → `docker compose exec postgres psql -U ecoumb -c "\dt"` | Las 10 tablas + `alembic_version`; el downgrade no da error | `evidencias/alembic-sqlite.txt` (SQLite); **falta la corrida sobre PostgreSQL** |
| 3 | CI en verde | Abrir la última ejecución en GitHub Actions | Tres jobs verdes: *Backend*, *Migraciones sobre PostgreSQL 16*, *Frontend* | — (requiere subir el repo) |
| 4 | Registrar usuario desde la PWA | <http://localhost:5173/registro> con un correo nuevo | Redirige al login con "Cuenta creada"; en *Network* la llamada devolvió **201** | `evidencias/smoke-api.txt` |
| 5 | Mismo correo otra vez | Repetir el registro | Error en el campo de correo; *Network*: **409** | `evidencias/smoke-api.txt` |
| 6 | Login y persistencia de sesión | Iniciar sesión → llega a Home con el nombre → **F5** | Sigue en Home (la sesión persiste) | `evidencias/frontend-vitest.txt` (pruebas de sesión) |
| 7 | Swagger | <http://localhost:8000/docs> | Endpoints `/auth/register`, `/auth/login`, `/auth/refresh`, `/users/me`, `/health` | — |
| 8 | Pruebas y cobertura en vivo | `cd backend && pytest --cov=app --cov-report=term-missing` | 56 pruebas en verde, cobertura ≈ 98 % | `evidencias/backend-pytest.txt` |

**Comandos de apoyo**

```bash
bash scripts/smoke_api.sh                 # verifica los criterios de S1-06 contra la API viva (espera 60 s entre corridas)
docker compose logs -f api                # logs JSON estructurados
docker compose down                       # detener (añade -v para borrar la base)
```

## Si Docker falla en vivo (plan B)

Sin Docker el sistema corre igual sobre SQLite (ver README, *Arranque sin Docker*). Cubre los pasos 4–8. Los pasos 1–3 dependen de Docker y GitHub; dilo con honestidad al presentar en lugar de simularlos.

## Lo que este repositorio NO puede probar por sí solo

- **Paso 3 (CI en verde):** ya está verificado: [run #1 en GitHub Actions](https://github.com/PWA-UMB/EcoUMB/actions/runs/35385430484), commit `9b5d3c6`, los tres jobs en verde. Los pasos 1–2 (Docker y la migración sobre PostgreSQL 16, incluido el `downgrade` de los ENUM) también se ejecutaron de verdad; ver `docs/evidencias/docker-*.txt`.
- **Service Worker en el navegador:** el build genera `sw.js` y `manifest.webmanifest` válidos y se sirven bien, pero el registro en tiempo de ejecución no se pudo comprobar en el navegador embebido usado en el desarrollo. Verificar en Chrome: DevTools → *Application* → *Service Workers* y *Manifest*, o Lighthouse → PWA.
- **Aspecto visual:** hay capturas reales de escritorio y móvil en `docs/evidencias/capturas/`; conviene igualmente revisarlas a ojo en un teléfono físico.

## Evidencias que aún debe producir el equipo (no se inventan)

Ya hay capturas y salidas reales de Docker, PostgreSQL, la PWA, Swagger y las pruebas (`docs/evidencias/`, Anexo A de la Guía), y la infografía (`docs/infografia/`). Faltan:

1. ~~Captura del pipeline de GitHub Actions~~: **hecha** (`docs/evidencias/capturas/github-actions-ci.png`, Anexo A.6 de la Guía). Para la demo en vivo, abrir la ejecución más reciente en la pestaña *Actions*.
2. **Acta o captura de la Review + Retrospectiva** (Guía §6): el texto de la retrospectiva ya está redactado en la Guía a partir de los hechos del proyecto (incluido HERIS); falta el respaldo de la reunión del equipo.
3. Recomendado: una captura de *su propia* ejecución de `docker compose ps` y de `pytest --cov`.
