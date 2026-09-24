# Sprint 2 — alcance, arquitectura y verificación

> **Actualización (Sprint 3):** la clasificación simulada de este documento fue reemplazada por el modelo v1 en Docker (`CLASSIFIER=onnx`); el modo simulado sigue disponible con `CLASSIFIER=simulated`. Ver [docs/07](07-modelo-ia-y-modulo-educativo-sprint3.md).

Sprint 2 del Plan de Sprints: **7–18 de septiembre de 2026**. Entregable acordado: *perfil, captura por cámara y galería, endpoint de clasificación simulada, historial básico; PWA instalable que completa el ciclo foto → resultado simulado → registro.*

Este documento describe lo que el código hace hoy. La clasificación es **simulada** (ver ADR-009): el modelo de IA real entra en el Sprint 3 y no se presenta como hecho.

## 1. Alcance frente al Plan de Sprints

| Entregable del plan | Requerimiento | Estado | Dónde está |
|---|---|---|---|
| Perfil de usuario | RF-04 | Hecho | `PATCH /api/v1/users/me` · `pages/ProfilePage.tsx` |
| Captura por cámara | RF-09 | Hecho | `hooks/useCamera.ts` (MediaDevices) · `pages/ScanPage.tsx` |
| Selección desde galería | RF-10 | Hecho | `<input type="file">` en `ScanPage`; formatos JPEG, PNG, WebP |
| Endpoint de clasificación **simulada** | — (entregable del plan) | Hecho, simulado | `POST /api/v1/classifications` · `infrastructure/ml_client/simulated.py` |
| Historial básico | RF-16, RF-17 | Hecho | `GET /api/v1/classifications/me` · `pages/HistoryPage.tsx` |
| PWA instalable y ciclo completo | RNF-12 (responsive) | Hecho | Manifiesto + Service Worker; botón «Instalar la aplicación» (`hooks/useInstallPrompt.ts`) |

**No entra en este sprint** (para no presentarlo como hecho): modelo de IA real y dataset (Sprint 3), módulo educativo (Sprint 3), puntos y logros (Sprint 5: `points_awarded` es siempre 0), correcciones del usuario a la clasificación, modo sin conexión con cola de envío, almacenamiento de fotos en la nube.

## 2. Flujo foto → resultado → registro

```
ScanPage                          API (FastAPI)                                   Datos
────────                          ─────────────                                   ─────
1. Cámara o galería
2. prepareImage(): reduce a
   1280 px, JPEG q0.85
3. POST /classifications  ───────► límite 10/min por usuario (429)
   multipart "image"              tamaño máx. 5 MB (413) · firma real JPEG/PNG/WebP (415)
                                  archivo vacío (422)
                                  ├─ ImageClassifier.predict(bytes, catálogo)     waste_items (15 clases)
                                  │    SimulatedClassifier: resultado determinista
                                  │    por SHA-256 de la imagen; simulated=true
                                  ├─ ImageStorage.save(bytes) ─────────────────►  uploads/ (volumen Docker)
                                  └─ ClassificationRepository.add ─────────────►  classifications
4. Resultado (201) ◄────────────  objeto, bolsa, mensaje, consejo, confianza, top-3
5. Historial: GET /classifications/me?limit&offset (paginado, solo lo propio)
   Miniaturas: GET /classifications/{id}/image con el token del usuario
```

Si el registro en base de datos falla, la foto ya guardada se elimina (no quedan archivos huérfanos).

## 3. Contrato de la API

| Método y ruta | Descripción | Códigos |
|---|---|---|
| `PATCH /api/v1/users/me` | Cambia el nombre visible. Cuerpo `{"full_name": "…" \| null}`; se recorta y vacío ⇒ `null`; máx. 120 caracteres. Rechaza campos extra (no se puede cambiar el rol) | 200 · 401 · 422 |
| `POST /api/v1/classifications` | Multipart, campo `image`. Devuelve la clasificación (ver abajo) | 201 · 401 · 413 · 415 · 422 · 429 · 503 |
| `GET /api/v1/classifications/me` | Historial del usuario, del más reciente al más antiguo. `limit` 1–100 (10 por defecto), `offset` ≥ 0 | 200 · 401 · 422 |
| `GET /api/v1/classifications/{id}/image` | La foto guardada. Solo su dueño; para cualquier otro usuario responde 404 (no revela que existe) | 200 · 401 · 404 |

```json
{
  "id": "…", "created_at": "2026-09-18T23:56:26Z", "simulated": true,
  "confidence": 0.75, "confidence_band": "medium",
  "item": {"code": "restos_comida", "display_name": "Restos de comida cocinada"},
  "category": {"code": "organico", "bag_color": "verde"},
  "message": "Va en la bolsa verde porque los restos de comida se descomponen.",
  "tip": "Escurre los líquidos antes de depositarlos.",
  "points_awarded": 0,
  "top3": [{"code": "…", "display_name": "…", "bag_color": "negra", "confidence": 0.15}],
  "image_url": "/api/v1/classifications/…/image"
}
```

**Bandas de confianza** (`domain/confidence.py`): `high` ≥ 0.85 · `medium` ≥ 0.65 · `low` por debajo. Con confianza baja la interfaz **no afirma** un residuo: dice «No logramos identificar este residuo con seguridad» y muestra las opciones más probables.

## 4. Arquitectura: qué se añadió a cada capa

| Capa | Añadido |
|---|---|
| `domain` | `confidence.py`, `entities/classification.py`, errores de imagen y catálogo; puertos `WasteCatalog`, `ImageClassifier`, `ImageStorage`, `ClassificationRepository` |
| `application` | `classification/images.py` (validación por firma), `classification/use_cases.py` (`classify_waste`, `list_history`, `get_classification_image`), `users/use_cases.py` (`update_profile`) |
| `infrastructure` | `ml_client/simulated.py`, `storage/local.py`, `persistence/catalog.py`, `persistence/classification_repository.py` |
| `interfaces` | `api/v1/classifications.py`, `PATCH /users/me`, esquemas Pydantic, manejadores de error 413/415/422/503/404 |

El clasificador es un **puerto**: reemplazar `SimulatedClassifier` por el cliente del servicio de ML (Sprint 3–4) no toca casos de uso, rutas ni frontend. La prueba `tests/unit/test_architecture.py` sigue garantizando que `domain` y `application` no importan FastAPI, SQLAlchemy, etc.

Frontend: `AppShell` (cabecera + navegación: barra inferior en móvil, pestañas en escritorio), páginas `Home`, `Escanear`, `Historial` y `Perfil`; `features/classification` (API, tarjeta de resultado, mensajes de error); `lib/image.ts` (reducción de la foto); `AuthedImage` (descarga la foto protegida con el token).

## 5. Decisiones de arquitectura (continúan la numeración del Sprint 1)

| # | Decisión | Alternativa | Razón |
|---|---|---|---|
| 009 | **Clasificador simulado, determinista por SHA-256 de la imagen**, tras el puerto `ImageClassifier` | Aleatorio en cada llamada; devolver siempre el mismo resultado | La misma foto da siempre la misma respuesta (demostración creíble, pruebas repetibles); reparte 70/20/10 % de confianza alta/media/baja para ejercitar los tres casos de la interfaz. La API declara `simulated: true` y la interfaz lo muestra |
| 010 | **Almacenamiento local en un volumen Docker** (`STORAGE_DIR`) tras el puerto `ImageStorage` | S3/Cloudflare R2 desde ya | Sin cuenta ni costo para el sprint; la interfaz del puerto (`save/read/delete`) permite pasar a S3/R2/MinIO sin tocar el resto. La clave de almacenamiento (`<id de usuario>/<uuid>.<ext>`) se valida contra *path traversal* |
| 011 | **Fotos privadas**: solo el dueño las descarga; el frontend las pide con `fetch` + token y las muestra con `URL.createObjectURL` | URL pública o firmada | Las fotos son datos personales (RNF-05). Un `<img src>` directo no envía el token, por eso `AuthedImage`. Cuesta una petición por miniatura (aceptable en 10 por página) |
| 012 | **Validación de la imagen por firma (magic bytes)**, no por extensión ni `Content-Type` | Confiar en el tipo declarado | El cliente controla ambos; un `.jpg` que no es JPEG recibe 415. Límite de 5 MB antes de leer todo el cuerpo (middleware antes de CORS, para que el 413 lleve cabeceras CORS) |
| 013 | **La foto se reduce en el navegador** (1280 px, JPEG 0,85) antes de subirla | Enviar el original | Una foto de celular pesa 4–12 MB: superaría el límite y tardaría en subir (tiempo de respuesta). Si el navegador no puede decodificarla, se envía la original y decide el servidor |
| 014 | **Límite de clasificaciones: 10/min por usuario** (en memoria, como ADR-008) | Sin límite | Protege el servicio de ML futuro (costo/CPU); es por usuario y no por IP porque hay redes universitarias compartidas |

## 6. Controles de seguridad añadidos

| Control | Implementación | Prueba |
|---|---|---|
| Autorización de fotos | `get_for_user` filtra por dueño; otro usuario recibe 404 | `test_classifications_api.py` (y verificación por mutación: quitar el filtro rompe la prueba) |
| Subidas | Firma real del archivo, máx. 5 MB, vacío rechazado | `test_image_validation.py`; mutación: aceptar cualquier archivo rompe 7 pruebas |
| *Path traversal* en el almacenamiento | Se rechazan claves absolutas, con `..`, `` o `:`, y toda ruta que no quede dentro de la carpeta raíz; la clave real es `<id de usuario>/<uuid>.<ext>` | `test_local_storage.py` |
| Mass assignment en el perfil | `extra="forbid"`: `role` en el cuerpo ⇒ 422 | `test_profile_api.py` |
| Respuesta con `Cache-Control: private` | La foto no se guarda en cachés compartidas | `test_classifications_api.py` |
| Service Worker | Las rutas `/api/` son `NetworkOnly`: nunca se cachean respuestas ni fotos de la API | `vite.config.ts` |
| CSP | `img-src 'self' data: blob:` (blob: solo para la vista previa local) | `frontend/nginx.conf.template` |

## 7. Verificación realizada

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Backend: pytest + cobertura | **124 pruebas**, 98 % de cobertura; ruff, formato y mypy estricto limpios | `evidencias/sprint2-backend-pytest.txt` |
| Frontend: Vitest + cobertura | **72 pruebas**, 97,9 % de líneas; `tsc`, ESLint y `vite build` limpios | `evidencias/sprint2-frontend-vitest.txt` |
| API real en Docker (PostgreSQL 16) | **22 comprobaciones** (perfil, clasificación, errores 413/415/422, historial, privacidad de fotos) | `evidencias/sprint2-smoke-api.txt` (`scripts/smoke_sprint2.sh`) |
| PWA real en Edge (cámara de prueba del navegador, subida por galería, historial, perfil) | Recorrido completo sin errores; 6 clasificaciones (1 por cámara, 5 por galería, incluido un caso de confianza baja) creadas y listadas con miniatura | `capturas/s2-*.png`, `evidencias/red-navegador-sprint2.txt`, `evidencias/sprint2-resultados.txt` (`scripts/capture_sprint2.mjs`) |
| PWA instalable | `Page.getInstallabilityErrors` ⇒ **ninguno**; Service Worker activo; manifiesto válido | `evidencias/pwa-instalabilidad.txt` |

**Límites de esta verificación (se declaran, no se ocultan):**

- La cámara del recorrido en navegador es la **cámara de prueba de Edge** (`--use-fake-device-for-media-stream`): demuestra el flujo `getUserMedia → captura → clasificación`, no la calidad de una cámara real. Falta probarlo en un teléfono físico (Android/Chrome e iOS/Safari).
- La instalación (clic en «Instalar») y el modo *standalone* dependen del navegador y no se pueden automatizar aquí; se comprobó que **no hay errores de instalabilidad**, que es lo que el navegador exige para ofrecerla.
- El resultado es simulado: no hay precisión que medir todavía. La métrica del modelo (≥ 80 % *top-1*) corresponde a los sprints 3–4.
- El limitador de tasa sigue siendo por proceso (memoria); con varias réplicas de la API hay que pasarlo a Redis.

## 8. Cómo se usa el flujo

1. `docker compose up -d --build` (los volúmenes de base de datos y fotos se conservan).
2. Abrir <http://localhost:5173>, iniciar sesión → **Escanear** → *Abrir la cámara* o *Elegir de la galería* → **Clasificar**.
3. Ver el registro en **Historial** y editar el nombre en **Perfil**.
4. Swagger: <http://localhost:8000/docs> → botón *Authorize* con el `access_token` del login → probar `POST /classifications` subiendo una imagen.
