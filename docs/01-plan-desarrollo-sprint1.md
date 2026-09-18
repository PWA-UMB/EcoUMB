# Plan de desarrollo — Sprint 1 (EcoUMB)

**Base:** SAD v1.0 (`ARQUITECTURA.md`) y Plan de Sprints — Entrega 2. Este plan no reemplaza esos documentos: los aterriza en tareas construibles y en evidencia para la Guía de Laboratorio 5.

## 1. Objetivo del sprint (del Plan de Sprints)

> Entorno reproducible con CI en verde, y un usuario que se registra e inicia sesión desde la PWA contra el backend real.

## 2. Alcance construido

| ID | Prioridad | Qué se construye | Dónde vive | Verificación |
|---|---|---|---|---|
| S1-01 | P0 | Estructura backend / frontend / ml, Git Flow, hooks pre-commit | raíz, `.pre-commit-config.yaml` | `pre-commit run --all-files` |
| S1-02 | P0 | CI (lint + pruebas) en cada PR | `.github/workflows/ci.yml` | pipeline en verde en GitHub |
| S1-03 | P0 | `docker compose up` con PostgreSQL 16, Redis 7, API y frontend | `docker-compose.yml`, `.env.example` | `docker compose ps` |
| S1-04 | P0 | Esquema completo SAD §5 con Alembic + seed (3 categorías, 15 clases) | `backend/alembic/`, `app/seed.py` | `alembic upgrade head` / `downgrade base` |
| S1-05 | P0 | API base: healthcheck, CORS, config por entorno, logging JSON, OpenAPI | `backend/app/main.py` | `GET /health`, `/docs` |
| S1-06 | P0 | `/auth/register`, `/auth/login`, `/auth/refresh` (JWT RS256 + bcrypt 12) + pytest | `backend/app/application/auth`, `interfaces/api/v1/auth.py` | `pytest --cov` |
| S1-07 | P0 | Scaffolding PWA: Vite, React 18, TS, Tailwind, manifest, Workbox, router, cliente HTTP con JWT | `frontend/` | `npm run build` |
| S1-08 | P0 | Pantallas de registro e inicio de sesión + Home placeholder | `frontend/src/features/auth`, `pages/` | `npm test`, demo |
| S1-09 | P1 | RBAC por rol (dependencia `require_roles`) | `interfaces/api/deps.py` | pruebas unitarias |
| — | soporte | `GET /users/me` (necesario para hidratar la sesión tras recargar) | `interfaces/api/v1/users.py` | prueba de integración |

**Fuera de alcance (P2 del plan):** S1-10 dataset/EDA, S1-11 recuperación de contraseña, S1-12 hook `useCamera`. La carpeta `ml/` existe con su estructura pero sin código.

## 3. Orden de ejecución

1. **Cimientos:** estructura, dependencias, configuración por entorno.
2. **Núcleo de auth con pruebas primero:** se escriben CP-01…CP-05 (más casos límite) → se ven fallar → se implementa → pasan.
3. **Persistencia:** modelos SQLAlchemy de las 10 tablas, migración Alembic, seed.
4. **Frontend:** scaffolding, cliente HTTP, store de sesión, formularios, Home.
5. **Infraestructura:** Dockerfiles, compose, CI, pre-commit.
6. **Verificación end-to-end y captura de evidencia** (sección 5).

## 4. Definición de terminado (DoD, del Plan de Sprints)

- Lint limpio: `ruff`, `mypy` (backend) y `eslint` + `tsc` (frontend).
- Pruebas automatizadas en verde; cobertura ≥ 80 % en el módulo de autenticación.
- Documentación al día (README, OpenAPI generado, decisiones en `02-arquitectura-implementada.md`).
- Criterios de aceptación de S1-04, S1-06 y S1-08 verificados y con evidencia.

## 5. Mapa hacia la Guía 5 (qué completa cada cosa)

| Sección de la Guía | Qué la completa | Estado |
|---|---|---|
| 3.3 Resultados de pruebas | Salida real de `pytest -v` y de cobertura → `docs/evidencias/` | Se genera al ejecutar; las cifras del documento deben salir de esa ejecución |
| 5 Demostración (pasos 1–8) | Código + guion de demo en `docs/03-guion-demo.md` | Depende de Docker Desktop y de un ensayo del equipo |
| Pipeline de CI en verde (paso 3 de la demo) | Requiere subir el repo a GitHub y ejecutar Actions | **Lo hace el equipo**: no hay remoto configurado |
| 6 Retrospectiva | Debe salir de la reunión real del equipo | **No se inventa**; solo se deja plantilla |
| 7 Infografía | Requiere leer el artículo de ScienceDirect | **Lo hace el equipo** |

## 6. Decisiones que se apartan del SAD (y por qué)

Ver ADR en `02-arquitectura-implementada.md`. Resumen: monorepo en lugar de tres repositorios, SQLAlchemy síncrono, PyJWT en lugar de `python-jose`, `bcrypt` directo en lugar de `passlib`, pruebas de API sobre SQLite y migraciones verificadas sobre PostgreSQL.

## 7. Riesgos de este sprint

| Riesgo | Mitigación |
|---|---|
| Docker Desktop apagado o sin recursos | Las pruebas de API corren sin Docker (SQLite); Docker solo se exige para compose y migraciones |
| Diferencias SQLite ↔ PostgreSQL ocultan errores | Migraciones y una pasada de pruebas de integración contra PostgreSQL 16 en CI |
| Claves JWT en el repositorio | Nunca se versionan; en desarrollo se generan efímeras y en producción son obligatorias |
| Evidencia presentada sin haber ejecutado | La Guía lo prohíbe: los resultados se pegan solo desde ejecuciones reales |

## 8. Estado de verificación (18/09/2026)

| Criterio de la Guía | Estado | Cómo se verificó |
|---|---|---|
| S1-06 registro / login / refresh con JWT y pruebas | **Verificado** | 56 pruebas de backend en verde, cobertura 98 % (auth ≥ 97 %); `scripts/smoke_api.sh` contra la API viva |
| S1-08 pantallas de acceso, validación, sesión persistente tras recargar | **Verificado** | 28 pruebas de frontend (96 % cobertura) + recorrido real en el navegador contra la API |
| S1-04 esquema completo y seed (3 categorías, 15 clases) | **Verificado en SQLite** | `alembic upgrade head` / `check` / `downgrade base`; seed idempotente |
| S1-04 sobre PostgreSQL 16 (incluido el borrado de tipos ENUM al hacer downgrade) | **Verificado** | PostgreSQL 16.15 en Docker: `upgrade` → `check` sin deriva → `downgrade base` (0 tablas y 0 tipos ENUM) → `upgrade` → seed dos veces (`docs/evidencias/docker-postgres*.txt`) |
| S1-03 `docker compose up` | **Verificado** | `docker compose up -d --build`: postgres, redis y api *healthy*, web sirviendo la PWA con CSP; la API migra y siembra al arrancar |
| Recorrido completo por Docker (navegador → nginx → API → PostgreSQL) | **Verificado** | Registro 201, login, `/users/me`, recarga con sesión, 409 al repetir; contraseñas guardadas como `$2b$12$` (`docs/evidencias/red-navegador.txt`, `capturas/`) |
| S1-02 CI en verde | **Verificado** | GitHub Actions, run #1 del commit `9b5d3c6` en `main` ([ver ejecución](https://github.com/PWA-UMB/EcoUMB/actions/runs/35385430484)): los 3 jobs en verde en 59 s (Backend, Migraciones sobre PostgreSQL 16 y Frontend, con Python 3.12). Captura en `docs/evidencias/capturas/github-actions-ci.png` |
| S1-01 hooks de pre-commit | **Verificado** | `pre-commit run --all-files`: 10/10 hooks en verde (detectó y se corrigieron un YAML inválido y un orden de imports no determinista) |
| Service Worker registrado en el navegador | **No verificado** | `sw.js` y manifest válidos y servidos; el navegador embebido no permitió registrarlo |
| Aspecto visual | **Verificado por captura** | Capturas reales en escritorio (1280×800) y móvil (390×844) con Edge; sin desbordamiento horizontal a 375 px (medido en el DOM) |
