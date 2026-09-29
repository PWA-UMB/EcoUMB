# EcoUMB

PWA con inteligencia artificial para clasificar y hacer trazabilidad de residuos sólidos en la Universidad Manuela Beltrán, sede Bogotá (Resolución 2184 de 2019: bolsa blanca, negra y verde).

**Estado: Sprint 3 (a 19 sep 2026)** — perfil, captura por cámara y galería, historial, PWA instalable, **modelo de IA v3** (MobileNetV3-Large sobre TrashNet + RealWaste; 8 clases con **orgánicos**; Macro F1 0,92 en test), confirmación/corrección del resultado por el usuario (RF-29/30) y módulo educativo. El modelo alcanza **8 de los 15 objetos** del catálogo, sus cifras son optimistas (fotos de objetos sueltos) y falla con fotos de mucha escena alrededor; ver [la ficha del modelo](ml/models/v3/MODEL_CARD.md). Sprints 1 y 2 siguen vigentes.

| Documento | Contenido |
|---|---|
| [docs/01-plan-desarrollo-sprint1.md](docs/01-plan-desarrollo-sprint1.md) | Alcance, orden de trabajo, DoD y qué completa cada sección de la Guía 5 |
| [docs/02-arquitectura-implementada.md](docs/02-arquitectura-implementada.md) | Capas, flujo de autenticación, seguridad, ADR y trazabilidad RF/RNF |
| [docs/03-guion-demo.md](docs/03-guion-demo.md) | Guion de la demostración del Sprint 1 (Guía 5 §5) y lista de evidencias |
| [docs/05-alcance-y-arquitectura-sprint2.md](docs/05-alcance-y-arquitectura-sprint2.md) | Sprint 2: alcance frente al plan, flujo, contrato de la API, ADR 009–014, seguridad y verificación |
| [docs/06-guion-demo-sprint2.md](docs/06-guion-demo-sprint2.md) | Guion de la demostración del Sprint 2 |
| [docs/07-modelo-ia-y-modulo-educativo-sprint3.md](docs/07-modelo-ia-y-modulo-educativo-sprint3.md) | Sprint 3: modelo v1 → v2 → v3, métricas y limitaciones, corrección del usuario y exportación, módulo educativo, ADR 015–026 |
| [ml/models/v3/MODEL_CARD.md](ml/models/v3/MODEL_CARD.md) | Ficha del modelo en uso (v3): datos, entrenamiento, resultados por clase y limitaciones (v1 y v2 siguen en `ml/models/`; la v2 no tiene ficha propia) |
| [docs/evidencias/](docs/evidencias/) | Salidas reales de pruebas, cobertura, migraciones y prueba de humo |

## Qué hace la PWA hoy

| Pantalla | Ruta | Requerimiento |
|---|---|---|
| Registro e inicio de sesión | `/registro`, `/login` | RF-01, RF-02 |
| Inicio: puntos, últimas clasificaciones, instalar la app | `/` | — |
| Escanear: cámara o galería → clasificar → resultado con bolsa y consejo → confirmar o corregir | `/escanear` | RF-09, RF-10, RF-29, RF-30 |
| Historial paginado con miniaturas | `/historial` | RF-16, RF-17 |
| Aprende: código de colores, guía por bolsa y buenas prácticas | `/aprende` | RF-26, RF-27, RF-28 |
| Perfil: datos de la cuenta y nombre editable | `/perfil` | RF-04 |

API (Swagger en `/docs`): `/auth/register`, `/auth/login`, `/auth/refresh`, `GET|PATCH /users/me`, `POST /classifications`, `GET /classifications/me`, `PUT /classifications/{id}/feedback`, `GET /classifications/{id}/image`, `GET /education`.

## Modelo de IA (v3 por defecto)

| Versión | Arquitectura | Datos y clases | Macro F1 en test | Uso |
|---|---|---|---|---|
| v1 | MobileNetV3-Small | TrashNet; 6 materiales, sin orgánicos | 0,8707 (380 fotos) | disponible |
| v2 | MobileNetV3-Small | TrashNet + RealWaste; 8 clases con orgánicos | 0,8378 (1 093 fotos) | disponible |
| v3 | MobileNetV3-Large | TrashNet + RealWaste; 8 clases con orgánicos | **0,9235** (1 093 fotos) | **por defecto** |

- v3 en test: exactitud 0,9167 y Macro F1 por bolsa (blanca, negra, verde) 0,9428. Las cifras de v1 salen de otro conjunto de test y no se comparan directamente con las de v2 y v3. Detalle en [`metrics.json`](ml/models/v3/metrics.json) y la [ficha del modelo](ml/models/v3/MODEL_CARD.md).
- **Cambiar de versión:** `MODEL_VERSION=v1`, `v2` o `v3` en `.env` y volver a levantar la API (`docker compose up -d api`). Docker monta `./ml/models` en solo lectura y la API carga `ml/models/<MODEL_VERSION>` al arrancar.
- **Límites:** reconoce 8 de los 15 objetos del catálogo; las cifras son optimistas (fotos de objetos sueltos sobre fondo blanco o piso liso); no hay fotos tomadas en la UMB en el entrenamiento ni en el test (solo 2 fotos reales de una lata, como prueba anecdótica), y falla con fotos de escenas complejas (mano, rostro, habitación). Con confianza baja (< 0,65) la app no afirma un residuo y ofrece las opciones más probables.
- Las respuestas de los usuarios (confirmar o corregir) quedan guardadas y se exportan como fotos etiquetadas para medir y reentrenar el modelo: `docker compose exec api python -m scripts.export_feedback --out /tmp/umb_dataset`.

## Estructura

```
backend/   FastAPI · arquitectura hexagonal · SQLAlchemy 2 · Alembic · pytest
frontend/  React 18 · TypeScript · Vite · Tailwind · Workbox (vite-plugin-pwa) · Vitest
ml/        entrenamiento, evaluación y modelos v1, v2 y v3 en ONNX (PyTorch → onnxruntime)
docs/      plan, arquitectura, guion de demo, evidencias
```

## Arranque con Docker (PostgreSQL 16 + Redis 7 + API + PWA)

```bash
cp .env.example .env        # y cambia POSTGRES_PASSWORD
docker compose up --build
```

- PWA: <http://localhost:5173> · API: <http://localhost:8000> · Swagger: <http://localhost:8000/docs>
- El contenedor de la API ejecuta `alembic upgrade head` y el seed antes de servir.
- El clasificador real se carga de `ml/models/${MODEL_VERSION:-v3}` (volumen de solo lectura); con `CLASSIFIER=simulated` la API responde sin modelo.
- Las fotos subidas viven en el volumen `uploads` (`STORAGE_DIR=/srv/uploads`); `docker compose down -v` las borra junto con la base.
- La cámara del navegador exige un contexto seguro: funciona en `localhost`; en otro equipo de la red hace falta HTTPS.

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

Sin Docker la API usa el clasificador simulado. Para el modelo real: `CLASSIFIER=onnx` y `MODEL_DIR=../ml/models/v3` (el valor por defecto de `MODEL_DIR` en `app/core/config.py` sigue siendo `../ml/models/v1`).

## Verificación

```bash
# Backend (desde backend/)
ruff check . && ruff format --check . && mypy app tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Migraciones (desde backend/)
alembic upgrade head && alembic check && alembic downgrade base

# Modelo v3 (desde ml/; requiere TrashNet y RealWaste en ml/data/raw/ y se entrenó en GPU NVIDIA;
# instalación y detalles en ml/models/v3/MODEL_CARD.md)
.venv-gpu/Scripts/python src/train.py --version v3 --dataset combined --robust --arch mobilenet_v3_large \
    --head-epochs 3 --fine-tune-epochs 25 --unfreeze-from 0 --fine-tune-lr 2e-4 --batch-size 64 --workers 10
.venv-gpu/Scripts/python src/evaluate.py --version v3 --dataset combined
.venv-gpu/Scripts/python src/select_views.py --version v3 --dataset combined

# Frontend (desde frontend/)
npm run lint && npm run typecheck && npm test && npm run build

# Pruebas de humo con la API en marcha (desde la raíz)
bash scripts/smoke_api.sh          # Sprint 1: autenticación
bash scripts/smoke_sprint2.sh      # Sprint 2: perfil, clasificación, historial, privacidad de fotos

# Recorrido real de la PWA en Edge/Chrome (cámara de prueba, galería, historial, perfil, instalabilidad)
node scripts/capture_sprint2.mjs
node scripts/capture_sprint3.mjs   # 6 fotos de test de TrashNet y la pestaña Aprende (escrito para v1; sus capturas s3-* son de v1)
```

> `smoke_api.sh` hace 7 llamadas a `/auth/*`, `smoke_sprint2.sh` hace 4 y el límite es de 10 por minuto por IP: si las repites de inmediato recibirás 429. Espera 60 s.

## Git Flow

Ramas: `main` (estable), `develop` (integración) y `feature/<historia>` (p. ej. `feature/S1-06-auth`). Todo cambio entra por *pull request* hacia `develop` con CI en verde y al menos una revisión (DoD del plan de sprints).

```bash
# (el repositorio ya está inicializado y su remoto apunta a git@github.com:PWA-UMB/EcoUMB.git)
git add -A && git commit -m "chore: estructura inicial del Sprint 1"
git branch develop && git switch -c feature/S1-06-auth develop
pip install pre-commit && pre-commit install       # hooks: ruff, prettier, eslint, detect-private-key
```

## Seguridad — lo que hay y lo que falta

Implementado: bcrypt (cost 12), JWT RS256 con `typ`/`iss`/`aud`, mismo 401 para correo inexistente y contraseña errónea, límite de 10 solicitudes/min en `/auth/*` y de 10 clasificaciones/min por usuario, fotos privadas (solo su dueño; para otro usuario, 404), subidas validadas por firma del archivo y tope de 5 MB, RBAC con rol leído de la base de datos, CORS con lista blanca, `role` no aceptado en el registro.

Pendiente (ver [arquitectura §4](docs/02-arquitectura-implementada.md)): revocación de refresh tokens en el servidor, limitador respaldado en Redis (hoy en memoria, por proceso), `audit_logs` poblado, TLS/HSTS (lo aplica el hosting) y cifrado en reposo. **El refresh token vive en `localStorage`** (ADR-005): es vulnerable a XSS; la alternativa es una cookie `httpOnly` con protección CSRF.
