# Sprint 3 — modelo de IA (v1 → v3) y módulo educativo

Entregable del Plan de Sprints (Sprint 3): *dataset (+ capturas UMB) y modelo v1 con métricas reportadas (meta Macro F1 ≥ 0,80) + módulo educativo (RF-26, RF-27, RF-28) publicado en la PWA.* Este documento dice qué se construyó, cómo se midió y **qué no cubre**. Durante el sprint el modelo pasó por tres versiones; la que usa la API por defecto es la **v3**. Fichas completas: [`ml/models/v3/MODEL_CARD.md`](../ml/models/v3/MODEL_CARD.md) (en uso) y [`ml/models/v1/MODEL_CARD.md`](../ml/models/v1/MODEL_CARD.md). La v2 no tiene ficha propia: sus cifras están en `ml/models/v2/metrics.json`.

## 1. Estado frente al plan

| Entregable | Estado | Observación |
|---|---|---|
| Dataset bootstrap | **Parcial** | TrashNet (2 527 fotos) + RealWaste (4 752 fotos) = 7 279 fotos, 8 clases con orgánicos; partición 70/15/15 estratificada por fuente y clase, con semilla. **Faltan las capturas tomadas en la UMB** |
| Modelo entrenado y desplegado | **Hecho: v3 en uso** | MobileNetV3-Large + transfer learning, exportado a ONNX (16,8 MB), sirviendo en la API dentro de Docker. v1 y v2 siguen disponibles con `MODEL_VERSION` |
| Métrica Macro F1 ≥ 0,80 | **0,9235 en 8 clases** (test, 1 093 fotos) | **No** es la medición de 15 clases del SAD; ver §4 |
| Módulo educativo RF-26 / RF-27 / RF-28 | **Hecho** | Pestaña «Aprende», datos desde la base de datos |
| Confirmación o corrección del resultado RF-29 / RF-30 | **Hecho** | `PUT /classifications/{id}/feedback` y panel en la pantalla de resultado; ver §3.2 |
| Reentrenamiento con fotos de usuarios (RF-31) | **Parcial** | La exportación de fotos etiquetadas existe; `train.py` todavía no las usa para entrenar |

## 2. Evolución del modelo: v1 → v2 → v3

| | v1 | v2 | v3 (en uso) |
|---|---|---|---|
| Arquitectura | MobileNetV3-Small | MobileNetV3-Small | **MobileNetV3-Large** |
| Datos | TrashNet (2 527 fotos) | TrashNet + RealWaste (7 279 fotos) | TrashNet + RealWaste (7 279 fotos) |
| Clases | 6 materiales, sin orgánicos | 8: los 6 materiales + `organic_food` y `vegetation` | 8, igual que v2 |
| Entrenamiento | 5 épocas de cabeza + 12 de ajuste fino (bloques 8–12), CPU | 3 + 15 épocas, CPU | 3 + 25 épocas, ajuste fino de **todo** el extractor, lote 64, **GPU** (GTX 1660 Ti, ~25 min) |
| Test | 380 fotos | 1 093 fotos | 1 093 fotos (mismas particiones que v2) |
| **Macro F1** | 0,8707 | 0,8378 | **0,9235** |
| Exactitud top-1 / top-3 | 0,8763 / 0,9842 | 0,8262 / 0,9607 | 0,9167 / 0,9817 |
| Macro F1 por bolsa (meta ≥ 0,90) | 0,9035 (solo 2 bolsas) | 0,8928 (3 bolsas, **no** cumple) | **0,9428** (3 bolsas) |
| Fotos con confianza ≥ 0,65 / exactitud en ellas | 78,9 % / 0,960 | 73,8 % / 0,927 | 85,9 % / 0,970 |
| ONNX (tamaño) | 6,1 MB | 6,1 MB | 16,8 MB (16 839 130 bytes) |
| Latencia del modelo en CPU (mediana / p95) | 1,66 / 2,61 ms | 1,69 / 2,72 ms | 3,65 / 7,16 ms |

Fuentes: `metrics.json` y `train_log.csv` de cada carpeta de `ml/models/`, `config.json` de v3 y las fichas del modelo; el tamaño del ONNX v3 se midió con `ls -l`. Las cifras de v1 salen de otro conjunto de test (solo TrashNet) y **no se comparan directamente** con las de v2 y v3, que comparten particiones.

**Qué cambió y por qué:**

- **v1 → v2: datos y clases.** v1 no podía devolver ningún residuo de la bolsa verde y su «F1 por bolsa» promediaba solo dos bolsas. Se añadió RealWaste (§2.1), que trae comida orgánica y vegetación y fotos con fondo real. Con 8 clases y un test más variado (distinto del de v1), la v2 obtuvo 0,8378 de Macro F1 y 0,8928 por bolsa, por debajo de la meta de 0,90; en las fotos de TrashNet del test su exactitud fue 0,7599. La orden de uso de `train.py` para v2 incluye `--robust` (aumentos de campo), pero la v2 no guardó `config.json`, así que no queda registro de sus argumentos exactos.
- **v2 → v3: capacidad del modelo.** Con las mismas particiones se pasó a MobileNetV3-Large, se ajustó todo el extractor (`--unfreeze-from 0`) con aumentos de campo (`--robust`, `ml/src/augment.py`) y se entrenó en GPU. Resultado: Macro F1 0,9235 y 0,9428 por bolsa (ambas metas cumplidas para 8 clases); exactitud 0,8892 en las fotos de TrashNet y 0,9314 en las de RealWaste. El costo: el ONNX pasa de 6,1 a 16,8 MB y la latencia mediana del modelo, de 1,7 a 3,7 ms.
- Se conservó siempre la época con mejor Macro F1 de **validación** (v1: época 15, 0,8486; v2: época 16, 0,8458; v3: época 20, 0,9328). El test se evaluó una sola vez por modelo y no se usó para decidir arquitectura ni vistas.

### 2.1 Datos: TrashNet y RealWaste

- **TrashNet** (Yang y Thung, 2016): objetos sueltos sobre fondo blanco, 6 materiales.
- **RealWaste** (Single, Iranmanesh y Raad, 2023; repositorio UCI, licencia **CC BY 4.0**, que permite reutilizarlo citando la fuente): fotos de residuos reales sobre el piso de un relleno sanitario. Sus carpetas se asocian a las clases del modelo en `ml/src/common.py`: «Food Organics» → `organic_food`, «Vegetation» → `vegetation`, «Textile Trash» y «Miscellaneous Trash» → `trash`, y el resto a su material.
- Los SHA-256 de ambos ZIP están en `metrics.json`. Partición de v2 y v3: 5 095 entrenamiento, 1 091 validación y 1 093 test (379 de TrashNet y 714 de RealWaste).
- Las dos clases nuevas se muestran como «Restos de comida cocinada» y «Residuo de poda / hojas», ambas en la **bolsa verde** (`class_map.json`). En test, la v3 acierta 59 de 61 fotos de comida y 65 de 66 de vegetación.

### 2.2 El modelo en uso (v3), en concreto

| | |
|---|---|
| Arquitectura | MobileNetV3-Large preentrenada en ImageNet + cabeza de 8 clases; fase 1 (cabeza, 3 épocas, lr 1e-3) y fase 2 (todo el extractor, 25 épocas, lr 2e-4 con coseno) |
| Pérdida | Entropía cruzada con pesos inversos a la frecuencia de clase y *label smoothing* 0,05 |
| Aumentos de campo | Objeto de TrashNet recortado y pegado sobre fondos aleatorios, manchas tipo mano u oclusión, cambios fuertes de matiz, escala de grises, desenfoque, borrado aleatorio y recortes de 40–100 % |
| Entrenamiento | GTX 1660 Ti con PyTorch 2.14 + CUDA 12.6 (`metrics.json`), ~25 min, semilla 42 |
| Despliegue | ONNX opset 17, 16,8 MB, `onnxruntime` en CPU; diferencia máxima de logits PyTorch ↔ ONNX: 7 × 10⁻⁶ |
| Test (1 093 fotos, una sola evaluación) | Macro F1 **0,9235** · exactitud 0,9167 · top-3 0,9817 · Macro F1 por bolsa **0,9428** |
| Reproducible | `ml/src/train.py`, `evaluate.py` y `select_views.py` con los argumentos de `ml/models/v3/config.json` (orden completa en la ficha) |

**Qué significa para el usuario:** si escanea cartón, vidrio, metal, papel, plástico, basura general, restos de comida o residuos de poda, la app los identifica con el modelo y la base de datos dice la bolsa; si la confianza es baja (< 0,65), no afirma un residuo y ofrece las opciones más probables. La prueba a través de la PWA en Docker guardada en `evidencias/sprint3-resultados-modelo.txt` (y las capturas `s3-*`) se hizo **con v1**: 6 fotos de test de TrashNet, las 6 con el objeto correcto en primer lugar (un metal con confianza media y un plástico con confianza baja, que la app presenta como incierto). **Con v3 no hay todavía evidencia guardada de la PWA**; queda pendiente capturarla.

## 3. Cómo encaja en la arquitectura

```
Foto ─► POST /classifications ─► OnnxClassifier (puerto ImageClassifier)
                                   ├─ preprocesa (256 px → recorte 224 → normalización ImageNet)
                                   ├─ vistas según inference.json (v3: solo el recorte central)
                                   ├─ onnxruntime → 8 probabilidades (6 con v1)
                                   └─ class_map.json: clase del modelo → objeto del catálogo UMB
        catálogo (BD) ◄────────────  la bolsa se lee de waste_categories, no del modelo
        ml_model_versions ◄────────  la versión se registra al usarla; classifications.model_version_id la enlaza
Respuesta del usuario ─► PUT /classifications/{id}/feedback ─► final_item_id + was_corrected
Exportación ─► scripts/export_feedback.py ─► <objeto>/<id>.<ext> + manifest.csv (sin datos del usuario)
```

- El clasificador sigue siendo un **puerto**: `CLASSIFIER=onnx` (Docker) o `simulated` (por defecto en desarrollo y pruebas). Si se pide `onnx` y no hay modelo, la API **no arranca** (falla rápido, no degrada en silencio a resultados falsos).
- `simulated` en la respuesta se deriva de la base de datos (`model_version_id` vacío ⇒ simulado). Con el modelo real la API devuelve `"simulated": false` y `"model_version"` con el nombre de la carpeta cargada (`"v3"` por defecto); el historial conserva la versión.
- Una foto corrupta con firma válida devuelve **422** (antes habría sido un error 500) y no deja archivo huérfano.
- Docker monta `./ml/models` completo como volumen de solo lectura (`./ml/models → /srv/models`) y la API carga `MODEL_DIR=/srv/models/${MODEL_VERSION:-v3}`. Cambiar de versión (RNF-17) es poner `MODEL_VERSION=v1`, `v2` o `v3` en `.env` y reiniciar la API, sin reconstruir la imagen. Sin Docker hay que dar `MODEL_DIR` explícito: el valor por defecto de `app/core/config.py` sigue siendo `../ml/models/v1`.

### 3.1 Vistas múltiples: implementadas, no adoptadas

La API puede promediar varias vistas de la misma foto (recorte central, espejo y foto completa), según `inference.json` de la carpeta del modelo. `ml/src/select_views.py` elige las vistas por Macro F1 de **validación** y solo las adopta si mejoran al menos 0,005:

| Opción | v2: F1 validación | v3: F1 validación |
|---|---|---|
| Recorte central | 0,8458 | 0,9328 |
| Central + espejo | 0,8405 | 0,9294 |
| Central + espejo + foto completa | 0,8474 (+0,0016) | 0,9370 (+0,0042) |

Ninguna llega a +0,005, así que v2 y v3 usan solo el recorte central (`inference.json`: `{"views": ["center"]}`): una inferencia por foto en vez de tres. Las cifras de test de cada opción se guardan en `views_selection.json` solo por transparencia (en v3, 0,9243 frente a 0,9235) y no se usaron para decidir.

### 3.2 Confirmación o corrección del usuario y exportación (RF-29, RF-30)

- En la pantalla de resultado el usuario confirma el residuo o elige el correcto; la PWA avisa que su respuesta y la foto pueden usarse para mejorar el modelo, y el historial muestra «Corregido: era …».
- `PUT /api/v1/classifications/{id}/feedback` con `{"item_code": "<código del objeto>"}` guarda el objeto real (`final_item_id`, `final_category_id`) y `was_corrected` (si difiere de la predicción). **La predicción original no se modifica**: sirve para medir al modelo. La última respuesta prevalece; solo el dueño puede responder (para otro usuario, 404); un objeto desconocido da 422 y los campos extra se rechazan.
Exportación para medir y reentrenar:

```bash
docker compose exec api python -m scripts.export_feedback --out /tmp/umb_dataset   # --only-corrected: solo las corregidas
docker compose cp api:/tmp/umb_dataset ml/data/umb
```

Genera `<objeto>/<id>.<ext>` y un `manifest.csv` **sin identificadores de usuario** (RNF-08). Si existe `ml/data/umb/`, `evaluate.py` mide también sobre esas fotos y las lista una por una. **`train.py` todavía no las usa para entrenar** (RF-31 pendiente).

## 4. Limitaciones que hay que decir al presentar

1. **Solo 8 de los 15 objetos son alcanzables.** No puede devolver vaso plástico, colilla de cigarrillo, empaque metalizado, servilleta sucia, vaso de café contaminado, cáscara de fruta ni bolsa de té o filtro de café. Una cáscara de fruta sale como «Restos de comida» (misma bolsa verde, distinto nombre).
2. **La meta ≥ 0,80 se midió en 8 clases**, no en las 15 del SAD.
3. **Las cifras son optimistas frente al uso real.** Ambos datasets son fotos de objetos sueltos (fondo blanco o piso liso), sin manos, personas ni canecas llenas, y las particiones aleatorias pueden dejar fotos casi idénticas en entrenamiento y test.
4. **Sin fotos tomadas en la UMB.** Solo se midieron 2 fotos reales de una lata sostenida con la mano (no usadas para entrenar): una acertada con confianza 0,68 y otra leída como «Papel limpio» con confianza baja (0,35). Es anecdótico (n = 2), pero confirma que **el modelo falla con fotos de escenas complejas** (mano, rostro, habitación); ahora lo hace con confianza baja y la app pide corregir.
5. RealWaste es un solo relleno sanitario y una sola cámara.
6. «Plástico» se muestra como «Botella PET» aunque sea otro plástico, y «basura general» como «Empaque de comida con residuos» (asociaciones provisionales en `class_map.json`, editables sin reentrenar).
7. Una corrida por arquitectura, sin intervalos de confianza ni validación cruzada. Alrededor del 14 % de las predicciones de test tiene confianza < 0,65 y ahí la exactitud cae.

## 5. Módulo educativo (RF-26, RF-27, RF-28)

`GET /api/v1/education` (requiere sesión) y la pestaña **Aprende**:

| Requerimiento | Qué muestra | De dónde sale |
|---|---|---|
| RF-27 código de colores | Resolución 2184 de 2019: blanca / negra / verde, con la aclaración de que es una guía y la norma oficial prevalece | `application/education/content.py` |
| RF-26 información educativa | Cada bolsa con su descripción, su texto y **los objetos del catálogo con su consejo** | Tablas `waste_categories` y `waste_items` (la guía cambia con un `UPDATE`, sin tocar código; los objetos inactivos no se muestran) |
| RF-28 buenas prácticas | Seis prácticas (separar, limpio y seco, reducir volumen, evitar desechables, aprovechar lo orgánico, consultar) | `application/education/content.py` |

El resumen de la norma es una guía de estudio redactada a partir de lo que ya documentaba el proyecto; **debe cotejarse con el texto oficial** antes de citarlo en la tesis.

## 6. Decisiones de arquitectura (continúan la numeración)

| # | Decisión | Alternativa / desviación del SAD | Razón |
|---|---|---|---|
| 015 | **PyTorch para entrenar y ONNX Runtime para servir** | SAD: TensorFlow 2.15/Keras + TF Serving | El equipo trabaja con Python 3.14, sin ruedas de TensorFlow; ONNX Runtime es ligero (la API no instala PyTorch) y el mismo `.onnx` sirve luego en otros entornos (SAD lo menciona como formato de despliegue). MobileNetV3-Small y transfer learning se mantienen |
| 016 | **`class_map.json`: material del modelo → objeto del catálogo** | Reentrenar con las 15 clases | Con TrashNet no hay datos para 15 clases; la asociación es datos editables, no código, y se reemplaza cuando existan fotos UMB |
| 017 | **`simulated` derivado de `model_version_id`** y versión registrada al primer uso | Bandera en configuración | La respuesta no puede mentir: si un modelo real clasificó, queda enlazado en `classifications` y `ml_model_versions` |
| 018 | **Modelo como volumen de solo lectura**, con arranque que falla si falta | Modelo dentro de la imagen | Actualizar el modelo (RNF-17) sin reconstruir; un despliegue sin modelo se detecta al arrancar |
| 019 | **Guía educativa leída de la base de datos** | Textos fijos en el frontend | La normativa vive en datos (SAD §7.1): cambiar bolsa o consejo no exige reentrenar ni republicar |
| 020 | **Añadir RealWaste y dos clases orgánicas** (`organic_food`, `vegetation`) | Esperar las fotos de la UMB; seguir con los 6 materiales de TrashNet | Contexto: v1 no podía devolver residuos de la bolsa verde y su F1 por bolsa promediaba solo 2 bolsas. RealWaste (UCI, CC BY 4.0) trae comida orgánica, vegetación y fondos reales. Consecuencias: 8 clases, 7 279 fotos y la bolsa verde medida; la ropa y la basura miscelánea se agrupan en `trash`; RealWaste es un solo sitio y una sola cámara, y siguen faltando fotos de la UMB |
| 021 | **Aumentos de campo** (`ml/src/augment.py`, opción `--robust`) | Solo los aumentos clásicos de v1 (recorte, espejo, rotación, color) | Contexto: TrashNet son objetos sobre fondo blanco y el modelo puede aprender «fondo blanco + color» en vez del objeto. Los fondos aleatorios se aplican solo a TrashNet (RealWaste ya trae fondo real). Consecuencias: no hay una corrida sin estos aumentos con la misma arquitectura, así que su efecto aislado no está medido; no sustituyen fotos reales de uso |
| 022 | **MobileNetV3-Large con ajuste fino de todo el extractor** (v3) | SAD y ADR-015: MobileNetV3-Small (v1, v2). `train.py` admite también EfficientNet-B0, sin métricas guardadas | Contexto: con 8 clases, la v2 quedó en Macro F1 0,8378 y 0,8928 por bolsa, bajo la meta de 0,90. Consecuencias: v3 llega a 0,9235 y 0,9428 con las mismas particiones; el ONNX pasa de 6,1 a 16,8 MB y la latencia mediana del modelo en CPU de 1,7 a 3,7 ms |
| 023 | **Entrenar en GPU y seguir sirviendo en CPU con ONNX** | Entrenar en CPU, como v1 y v2 | Contexto: ajustar todo el extractor de MobileNetV3-Large cuesta más que entrenar la cabeza y los últimos bloques de la versión Small; la v3 se entrenó en una GTX 1660 Ti (~25 min, 28 épocas). Consecuencias: la API sigue sin PyTorch ni GPU (ADR-015 vigente); las métricas se calculan sobre el ONNX con el preprocesado de la API (diferencia de logits con PyTorch: 7 × 10⁻⁶); reproducir la v3 en un tiempo similar exige una GPU NVIDIA |
| 024 | **Montar `./ml/models` completo y elegir la versión con `MODEL_VERSION`** (v3 por defecto) | ADR-018 original: montar una sola carpeta (`./ml/models/v1`) | Contexto: con tres versiones hay que poder comparar y volver atrás. Consecuencias: cambiar de versión es editar `.env` y reiniciar la API, sin tocar `docker-compose.yml` ni reconstruir; `ml_model_versions` registra cada versión y cada clasificación guarda cuál la produjo |
| 025 | **Confirmación o corrección del usuario y exportación de fotos etiquetadas** (RF-29, RF-30) | Guardar solo la etiqueta final; reentrenar leyendo la base de datos directamente | Contexto: faltan fotos reales de la UMB y la app es la forma de conseguirlas. Se conserva la predicción junto a la respuesta (para medir al modelo) y la exportación genera carpetas por objeto y un `manifest.csv` sin identificadores de usuario (RNF-08). Consecuencias: `evaluate.py` ya mide sobre `ml/data/umb/`; entrenar con esas fotos (RF-31) sigue pendiente |
| 026 | **Vistas múltiples implementadas en la API, pero no adoptadas** | Promediar siempre recorte central, espejo y foto completa | Contexto: se eligen por Macro F1 de validación con una mejora mínima de 0,005; la mejor opción ganó +0,0042 en v3 y +0,0016 en v2. Consecuencias: `inference.json` usa solo el recorte central (una inferencia por foto en vez de tres); activarlas es editar ese archivo, sin tocar código |
| — | **Sin MLflow por ahora** | SAD §7 lo prevé | Ya hay tres versiones; se comparan con `metrics.json`, `train_log.csv` y (solo en v3) `config.json` de cada carpeta, y la v2 no guardó ni `config.json` ni ficha. Incorporar MLflow sigue pendiente |

ADR-022 sustituye la parte de ADR-015 que mantenía MobileNetV3-Small, y ADR-024 amplía ADR-018 (el volumen ya no es una sola versión); el resto de ambas sigue vigente.

## 7. Verificación realizada

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Métricas de v3 (test) | Macro F1 0,9235, exactitud 0,9167, F1 por bolsa 0,9428; matriz de confusión; ROC-AUC por clase | `ml/models/v3/metrics.json`, `confusion_matrix.png` |
| Métricas de v1 y v2 (test) | Macro F1 0,8707 (v1) y 0,8378 (v2) | `evidencias/sprint3-modelo-v1-metricas.json`, `ml/models/v1/`, `ml/models/v2/` |
| Equivalencia PyTorch ↔ ONNX | Diferencia máxima de los logits: 1,9 × 10⁻⁵ (v1), 3,1 × 10⁻⁵ (v2), 7 × 10⁻⁶ (v3) | `metrics.json` de cada versión |
| Selección de vistas | Ninguna combinación mejora ≥ 0,005 en validación | `views_selection.json` de v2 y v3 |
| El clasificador **de la API** reproduce las métricas (v1) | Mismas 380 fotos: exactitud 0,8763 y Macro F1 0,8707 (idénticas al script de evaluación) | ejecución comprobada en la sesión |
| Backend: pytest + cobertura (salida del 18 sep) | **154 pruebas**, 99 %; ruff, formato y mypy estricto limpios | `evidencias/sprint3-backend-pytest.txt` |
| Frontend: Vitest + cobertura (salida del 18 sep) | **76 pruebas**, 98,1 %; tsc y eslint limpios | `evidencias/sprint3-frontend-vitest.txt` |
| PWA en Docker con fotos reales de TrashNet (test), con v1 | 6 materiales clasificados a través de la interfaz; historial con miniaturas; pestaña Aprende | `capturas/s3-*.png`, `evidencias/red-navegador-sprint3.txt`, `sprint3-resultados-modelo.txt` (`scripts/capture_sprint3.mjs`) |
| Pruebas de humo de la API (con v1) | 22 de 22 con el modelo activo | `evidencias/sprint2-smoke-api.txt` |

**Pendiente de evidencia:** las salidas guardadas de pytest y Vitest son anteriores a parte de lo descrito aquí: `dataset_export.py` no aparece en la cobertura del backend ni `FeedbackPanel.tsx` en la del frontend, aunque sus pruebas están en el repositorio (`backend/tests/integration/test_feedback_api.py`, `backend/tests/unit/test_dataset_export.py`, `frontend/src/pages/ScanFeedback.test.tsx`); tampoco hay capturas de la PWA con v3. Hay que volver a ejecutar las pruebas y el recorrido de la PWA con v3 y guardar sus salidas en `docs/evidencias/`.

Las pruebas automáticas usan un modelo ONNX diminuto construido en el propio test (rojo → cartón, verde → vidrio, azul → metal), así que **no dependen** de los `model.onnx` de `ml/models/` ni de PyTorch.

## 8. Cómo usarlo

```bash
docker compose up -d --build          # la API carga ml/models/v3/model.onnx (MODEL_VERSION=v3 por defecto)
# PWA http://localhost:5173 → Escanear (foto de un objeto sobre fondo liso) → confirmar o corregir → Aprende
MODEL_VERSION=v1 docker compose up -d api   # o en .env: volver a otra versión para comparar
node scripts/capture_sprint3.mjs      # recorrido con 6 fotos de test de TrashNet (escrito para v1; requiere ml/data/raw)
```

Si el navegador muestra la versión anterior de la app, es la caché del Service Worker: *DevTools → Application → Service Workers → Unregister* y recargar con Ctrl + Shift + R.

## 9. Lo que sigue (Sprint 4 en adelante)

Capturar fotos en la UMB con la propia app (corrección del usuario + exportación), hacer que `train.py` las use para reentrenar (RF-31), añadir los 7 objetos del catálogo que faltan, medir con un conjunto de fotos de la UMB que no se use para entrenar y con particiones por objeto, y guardar la evidencia de pruebas y de la PWA con v3.
