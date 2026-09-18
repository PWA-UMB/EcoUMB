# Arquitectura implementada — Sprint 1

Este documento describe **lo que el código de este sprint realmente hace**, y se apoya en el SAD v1.0 para lo que aún no se construye. Donde el código se aparta del SAD, se declara en la sección 6.

## 1. Vista general

Cliente-servidor de tres capas. El backend sigue **arquitectura hexagonal**: el dominio no importa nada de FastAPI, SQLAlchemy, bcrypt ni JWT.

```
 Navegador (PWA React)                       Backend (FastAPI)                               Datos
┌───────────────────────┐   HTTPS/JSON   ┌───────────────────────────────────────┐      ┌────────────┐
│ pages / features/auth │ ─────────────► │ interfaces/api   (routers, schemas)    │      │ PostgreSQL │
│ Zustand + TanStack Q. │                │        │ depende de                    │      │     16     │
│ Service Worker        │ ◄───────────── │ application/auth (casos de uso)        │ ───► │            │
└───────────────────────┘                │        │ depende de                    │      └────────────┘
                                         │ domain (entidades, puertos, errores)   │      ┌────────────┐
                                         │        ▲ implementan los puertos       │ ───► │  Redis 7   │
                                         │ infrastructure (SQLAlchemy, bcrypt,    │      │ (reservado)│
                                         │                 JWT RS256)             │      └────────────┘
                                         └───────────────────────────────────────┘
```

**Regla de dependencia:** `interfaces → application → domain ← infrastructure`. `domain` no depende de nadie. Se verifica con una prueba (`tests/unit/test_architecture.py`) que falla si `app/domain` o `app/application` importan `fastapi`, `sqlalchemy`, `bcrypt` o `jwt`.

## 2. Estructura de carpetas

```
EcoUMB/
├── backend/
│   ├── app/
│   │   ├── core/            config, logging JSON, rate limiting
│   │   ├── domain/          entidades, roles, errores, puertos (Protocol)
│   │   ├── application/auth casos de uso: registrar, iniciar sesión, refrescar
│   │   ├── infrastructure/  persistence (modelos, repos, sesión) · security (bcrypt, JWT)
│   │   ├── interfaces/      api (routers v1, deps, RBAC) · schemas (Pydantic)
│   │   ├── seed.py          3 categorías + 15 clases (idempotente)
│   │   └── main.py          create_app()
│   ├── alembic/             migración 0001 con las 10 tablas del SAD §5
│   └── tests/               unit · integration
├── frontend/                Vite + React 18 + TS + Tailwind + Workbox (vite-plugin-pwa)
├── ml/                      estructura reservada (Sprint 3)
├── docs/                    plan, arquitectura, guion de demo, evidencias
├── docker-compose.yml       postgres · redis · api · web
└── .github/workflows/ci.yml
```

## 3. Flujo de autenticación

```
Registro:   POST /api/v1/auth/register {email, password, full_name}
            └► valida (Pydantic) → repo.get_by_email → bcrypt(cost 12) → repo.add → 201 {id,email,...}
               correo repetido → 409 · contraseña débil/correo inválido → 422

Login:      POST /api/v1/auth/login {email, password}
            └► repo.get_by_email → verify (siempre se ejecuta un hash, exista o no el usuario)
               → access JWT (15 min) + refresh JWT (7 días), RS256   ·   fallo → 401 genérico

Refresh:    POST /api/v1/auth/refresh {refresh_token}
            └► valida firma, exp y claim typ="refresh" → nuevo access token   ·   inválido → 401

Sesión web: al recargar, el frontend usa el refresh token guardado → obtiene access token
            → GET /api/v1/users/me → pinta Home.  Un 401 con refresh inválido limpia la sesión.
```

Contrato completo y ejemplos: OpenAPI en `/docs` (generado por FastAPI).

## 4. Controles de seguridad implementados

| Control (SAD §8) | Implementación en este sprint |
|---|---|
| Contraseñas | `bcrypt`, cost factor 12, mínimo 8 caracteres con letra y número |
| Tokens | JWT **RS256**; access 15 min, refresh 7 días; claim `typ` impide usar un refresh como access |
| Enumeración de usuarios | Mismo 401 y mismo trabajo criptográfico para correo inexistente y contraseña errónea |
| Rate limiting | 10 solicitudes/min por IP en `/auth/*` (ventana deslizante en memoria; por proceso — Redis en sprint posterior) |
| RBAC | `require_roles(...)`; el rol se lee de la base de datos, no del token, así que un cambio de rol o una baja surte efecto de inmediato (hay prueba); roles `user`, `cleaner`, `admin` |
| CORS | Lista blanca por variable de entorno |
| Secretos | Solo por variables de entorno; `.env` ignorado por git; en producción las claves JWT son obligatorias |
| Validación de entrada | Pydantic v2 (`EmailStr`, longitudes máximas) |

**Pendiente (no implementado en este sprint, para no presentarlo como hecho):** revocación de refresh tokens/logout server-side, HSTS/TLS (los aplica el hosting), cifrado en reposo, `audit_logs` poblado, Redis como backend del limitador.

## 5. Modelo de datos

Las 10 tablas del SAD §5 existen en el modelo y en la migración `0001`: `users`, `waste_categories`, `waste_items`, `ml_model_versions`, `classifications`, `rewards`, `reward_redemptions`, `achievements`, `user_achievements`, `audit_logs`. Solo `users` tiene lógica en este sprint; el resto se crea y se siembra (`waste_categories`, `waste_items`) para que los siguientes sprints no requieran migraciones de base.

Tipos portables: `Uuid` genérico, `JSON` con variante `JSONB` en PostgreSQL, `String` con variante `INET`.

## 6. Decisiones de arquitectura (ADR)

| # | Decisión | Alternativa del SAD | Razón |
|---|---|---|---|
| 001 | **Monorepo** con `backend/`, `frontend/`, `ml/` | Tres repositorios | Un solo CI y un solo `docker compose` para un equipo de 3. Se puede separar con `git subtree split` sin tocar el código |
| 002 | **SQLAlchemy 2.0 síncrono** (`psycopg` 3) con endpoints `def` (hilos de FastAPI) | Motor asíncrono | Mismo modelo mental para Alembic y pruebas; 100 usuarios concurrentes del piloto no lo exigen. El puerto de repositorio permite migrar a async después |
| 003 | **PyJWT** | `python-jose` | `python-jose` tiene mantenimiento escaso y CVEs conocidos; PyJWT ya es dependencia estándar |
| 004 | **`bcrypt` directo** | `passlib` | `passlib` no es compatible con `bcrypt` ≥ 4.1 sin parches |
| 005 | **Refresh token en `localStorage`, access token en memoria** | Cookie httpOnly | El SAD y los criterios de aceptación definen tokens en el cuerpo JSON. Riesgo aceptado: exposición ante XSS; mitigado con access de 15 min y sanitización de React. Alternativa futura: cookie httpOnly + CSRF |
| 006 | **Pruebas de API sobre SQLite en memoria**; migraciones y compose sobre PostgreSQL 16 | Todo en PostgreSQL | Las pruebas corren sin Docker y en segundos; el riesgo de divergencia se cubre en CI con PostgreSQL real |
| 007 | **Componentes UI propios con estilo shadcn** (Tailwind + `cva`) | `shadcn/ui` vía CLI | El CLI es interactivo y añade dependencias que hoy no se usan; los 4 componentes necesarios se escriben directamente |
| 008 | **Límite de tasa en memoria** | Redis + limiter | Redis aún no tiene consumidores; se deja detrás de una función para cambiarlo |

## 7. Trazabilidad RF/RNF → código (Sprint 1)

| Requerimiento | Código |
|---|---|
| RF-01 registro | `application/auth/use_cases.py::register_user` · `POST /auth/register` |
| RF-02 login | `login_user` · `POST /auth/login` (cierre de sesión en el cliente; server-side pendiente) |
| RF-05/06/08 roles y permisos | `domain/roles.py`, `interfaces/api/deps.py::require_roles` |
| RNF-04 autenticación segura | `infrastructure/security/` |
| RNF-05 protección de datos sensibles | hash bcrypt; contraseña nunca en respuestas ni logs |
| RNF-06 RBAC | `require_roles` |
| RNF-09/11 usabilidad | validación en cliente, mensajes claros (`features/auth`) |
| RNF-10 máx. 3 pasos | registro en 1 pantalla, login en 1 pantalla |
| RNF-12 responsive | Tailwind mobile-first |
| RNF-16 modularidad | capas hexagonales + prueba de arquitectura |
| RNF-18 documentación | OpenAPI + docs/ |

## 8. Notas operativas

- **IP del cliente tras un proxy:** el limitador de tasa usa la IP de la conexión. Detrás de un proxy inverso (Render, Railway, nginx) todos los clientes parecerían tener la IP del proxy. Al desplegar hay que arrancar uvicorn con `--proxy-headers` y `--forwarded-allow-ips=<IP del proxy>` (nunca `*`, o cualquiera podría falsificar `X-Forwarded-For` y esquivar el límite).
- **CORS en desarrollo:** el valor por defecto admite `http://localhost:5173` y `http://127.0.0.1:5173`. En producción `CORS_ORIGINS` debe listarse explícitamente y `*` está prohibido (lo valida `Settings`).
- **Refresh token en `localStorage`:** ver ADR-005. Es la decisión de menor costo y la que exigen los criterios de aceptación del sprint, pero es el punto más débil de la sesión; migrarlo a cookie `httpOnly` es la mejora de seguridad prioritaria.
