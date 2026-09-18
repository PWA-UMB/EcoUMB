# EcoUMB

PWA con inteligencia artificial para clasificar y hacer trazabilidad de residuos sólidos en la Universidad Manuela Beltrán, sede Bogotá (Resolución 2184 de 2019: bolsa blanca, negra y verde).

**Estado: Sprint 1** — entorno reproducible, base de datos versionada, registro / inicio de sesión / refresh con JWT, y pantallas de acceso de la PWA. La captura por cámara y la clasificación con IA llegan en los sprints 2–4.

| Documento | Contenido |
|---|---|
| [docs/01-plan-desarrollo-sprint1.md](docs/01-plan-desarrollo-sprint1.md) | Alcance, orden de trabajo, DoD y qué completa cada sección de la Guía 5 |
| [docs/02-arquitectura-implementada.md](docs/02-arquitectura-implementada.md) | Capas, flujo de autenticación, seguridad, ADR y trazabilidad RF/RNF |
| [docs/03-guion-demo.md](docs/03-guion-demo.md) | Guion de la demostración (Guía 5 §5) y lista de evidencias |
| [docs/evidencias/](docs/evidencias/) | Salidas reales de pruebas, cobertura, migraciones y prueba de humo |

## Estructura

```
backend/   FastAPI · arquitectura hexagonal · SQLAlchemy 2 · Alembic · pytest
frontend/  React 18 · TypeScript · Vite · Tailwind · Workbox (vite-plugin-pwa) · Vitest
ml/        reservado para los sprints 3–4 (dataset, entrenamiento, MLflow)
docs/      plan, arquitectura, guion de demo, evidencias
```

## Arranque con Docker (PostgreSQL 16 + Redis 7 + API + PWA)

```bash
cp .env.example .env        # y cambia POSTGRES_PASSWORD
docker compose up --build
```

- PWA: <http://localhost:5173> · API: <http://localhost:8000> · Swagger: <http://localhost:8000/docs>
- El contenedor de la API ejecuta `alembic upgrade head` y el seed antes de servir.

## Arranque sin Docker (SQLite, para desarrollar)

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite:///./dev.db                  # PowerShell: $env:DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head && python -m app.seed
uvicorn app.main:create_app --factory --reload          # http://localhost:8000

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                             # http://localhost:5173
```

Sin `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` el API genera un par efímero (los tokens se invalidan al reiniciar). Para claves fijas: `python backend/scripts/generate_jwt_keys.py`.

## Verificación

```bash
# Backend (desde backend/)
ruff check . && ruff format --check . && mypy app tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Migraciones (desde backend/)
alembic upgrade head && alembic check && alembic downgrade base

# Frontend (desde frontend/)
npm run lint && npm run typecheck && npm test && npm run build

# Prueba de humo con la API en marcha (desde la raíz)
bash scripts/smoke_api.sh
```

> `scripts/smoke_api.sh` hace 7 llamadas a `/auth/*` y el límite es de 10 por minuto por IP: si la repites de inmediato recibirás 429. Espera 60 s.

## Git Flow

Ramas: `main` (estable), `develop` (integración) y `feature/<historia>` (p. ej. `feature/S1-06-auth`). Todo cambio entra por *pull request* hacia `develop` con CI en verde y al menos una revisión (DoD del plan de sprints).

```bash
# (el repositorio ya está inicializado y su remoto apunta a git@github.com:PWA-UMB/EcoUMB.git)
git add -A && git commit -m "chore: estructura inicial del Sprint 1"
git branch develop && git switch -c feature/S1-06-auth develop
pip install pre-commit && pre-commit install       # hooks: ruff, prettier, eslint, detect-private-key
```

## Seguridad — lo que hay y lo que falta

Implementado: bcrypt (cost 12), JWT RS256 con `typ`/`iss`/`aud`, mismo 401 para correo inexistente y contraseña errónea, límite de 10 solicitudes/min en `/auth/*`, RBAC con rol leído de la base de datos, CORS con lista blanca, `role` no aceptado en el registro.

Pendiente (ver [arquitectura §4](docs/02-arquitectura-implementada.md)): revocación de refresh tokens en el servidor, limitador respaldado en Redis (hoy en memoria, por proceso), `audit_logs` poblado, TLS/HSTS (lo aplica el hosting) y cifrado en reposo. **El refresh token vive en `localStorage`** (ADR-005): es vulnerable a XSS; la alternativa es una cookie `httpOnly` con protección CSRF.
