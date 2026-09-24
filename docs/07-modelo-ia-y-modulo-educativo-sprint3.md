# Sprint 3 — modelo de IA v1 y módulo educativo

Entregable del Plan de Sprints (Sprint 3): *dataset (+ capturas UMB) y modelo v1 con métricas reportadas (meta Macro F1 ≥ 0,80) + módulo educativo (RF-26, RF-27, RF-28) publicado en la PWA.* Este documento dice qué se construyó, cómo se midió y **qué no cubre**. La ficha completa del modelo está en [`ml/models/v1/MODEL_CARD.md`](../ml/models/v1/MODEL_CARD.md).

## 1. Estado frente al plan

| Entregable | Estado | Observación |
|---|---|---|
| Dataset bootstrap | **Parcial** | TrashNet (2 527 fotos, 6 materiales), partición 70/15/15 estratificada con semilla. **Faltan las capturas tomadas en la UMB** y los residuos orgánicos |
| Modelo v1 entrenado y desplegado | **Hecho, con alcance reducido** | MobileNetV3-Small + transfer learning, exportado a ONNX (6,1 MB), sirviendo en la API dentro de Docker |
| Métrica Macro F1 ≥ 0,80 | **0,8707 en 6 materiales** (test, 380 fotos) | **No** es la medición de 15 clases del SAD; ver §4 |
| Módulo educativo RF-26 / RF-27 / RF-28 | **Hecho** | Pestaña «Aprende», datos desde la base de datos |

## 2. El modelo, en concreto

| | |
|---|---|
| Arquitectura | MobileNetV3-Small preentrenada en ImageNet + cabeza de 6 clases; fase 1 (cabeza, 5 épocas) y fase 2 (ajuste fino de los bloques 8–12, 12 épocas) |
| Datos | TrashNet: cartón, vidrio, metal, papel, plástico y basura general |
| Test (380 fotos, una sola evaluación) | Macro F1 **0,8707** · accuracy 0,8763 · top-3 0,9842 · latencia del modelo 1,7 ms (mediana, CPU) |
| Con confianza ≥ 0,65 | 78,9 % de las fotos, con 96,0 % de aciertos |
| Reproducible | `ml/src/train.py` y `ml/src/evaluate.py`, semilla 42; métricas en `ml/models/v1/metrics.json` |

**Qué significa para el usuario:** si escanea una botella de vidrio, una lata, un cartón, un papel o un plástico, la app ahora los identifica con el modelo (no al azar) y la base de datos dice la bolsa. Lo probamos con una foto real de cada material del conjunto de test a través de la PWA en Docker: las 6 se clasificaron bien (una con confianza media y una plástico con confianza baja, que la app presenta como «No logramos identificar con seguridad»; ver `evidencias/sprint3-resultados-modelo.txt`).

## 3. Cómo encaja en la arquitectura

```
Foto ─► POST /classifications ─► OnnxClassifier (puerto ImageClassifier)
                                   ├─ preprocesa (256 px → recorte 224 → normalización ImageNet)
                                   ├─ onnxruntime → 6 probabilidades
                                   └─ class_map.json: material → objeto del catálogo UMB
        catálogo (BD) ◄────────────  la bolsa se lee de waste_categories, no del modelo
        ml_model_versions ◄────────  la versión se registra al usarla; classifications.model_version_id la enlaza
```

- El clasificador sigue siendo un **puerto**: `CLASSIFIER=onnx` (Docker) o `simulated` (por defecto en desarrollo y pruebas). Si se pide `onnx` y no hay modelo, la API **no arranca** (falla rápido, no degrada en silencio a resultados falsos).
- `simulated` en la respuesta ahora se deriva de la base de datos (`model_version_id` vacío ⇒ simulado). Con el modelo real la API devuelve `"simulated": false` y `"model_version": "v1"`; el historial conserva la versión.
- Una foto corrupta con firma válida devuelve **422** (antes habría sido un error 500) y no deja archivo huérfano.
- El modelo se monta en Docker como volumen de solo lectura (`./ml/models/v1 → /srv/models/v1`): cambiar de versión (RNF-17) es cambiar la carpeta y reiniciar, sin reconstruir la imagen.

## 4. Limitaciones que hay que decir al presentar

1. **Solo 6 de los 15 objetos son alcanzables.** Colilla, servilleta sucia, vaso de café contaminado, empaque metalizado y **todos los orgánicos** (bolsa verde) no pueden salir. La app lo avisa en cada resultado real.
2. **La meta ≥ 0,80 se midió en 6 materiales**, no en las 15 clases del SAD. El «Macro F1 por categoría» (0,9035) promedia solo 2 categorías: la bolsa verde no está medida.
3. **Las cifras probablemente son optimistas.** TrashNet tiene fotos casi duplicadas (un mismo objeto varias veces) y las particiones son aleatorias; además son objetos sueltos sobre fondo blanco. En una caneca real el resultado será peor y **no está medido**.
4. «Plástico» se muestra como «Botella PET» aunque sea otro plástico (asociación provisional en `class_map.json`, editable sin reentrenar).
5. **Faltan las fotos de la UMB.** Sin ellas no hay v2 ni medición en condiciones reales. Es el trabajo del equipo (capturar con la cámara de la PWA) y la ficha del modelo indica el siguiente paso.
6. Una corrida, una semilla, sin intervalos de confianza.

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
| — | **Sin MLflow por ahora** | SAD §7 lo prevé | Una sola corrida; las métricas y el registro de entrenamiento se guardan en `metrics.json`/`train_log.csv`. Se incorpora cuando haya varias versiones que comparar |

## 7. Verificación realizada

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Backend: pytest + cobertura | **154 pruebas**, 99 %; ruff, formato y mypy estricto limpios | `evidencias/sprint3-backend-pytest.txt` |
| Frontend: Vitest + cobertura | **76 pruebas**, 98,1 %; tsc y eslint limpios | `evidencias/sprint3-frontend-vitest.txt` |
| Métricas del modelo (test) | Macro F1 0,8707; matriz de confusión; ROC-AUC por clase | `evidencias/sprint3-modelo-v1-metricas.json`, `ml/models/v1/` |
| El clasificador **de la API** reproduce las métricas | Mismas 380 fotos: accuracy 0,8763 y Macro F1 0,8707 (idénticas al script de evaluación) | ejecución comprobada en la sesión |
| Equivalencia PyTorch ↔ ONNX | Diferencia máxima de los logits: 1,9 × 10⁻⁵ | `metrics.json` |
| PWA en Docker con fotos reales de TrashNet (test) | 6 materiales clasificados a través de la interfaz; historial con miniaturas; pestaña Aprende | `capturas/s3-*.png`, `evidencias/red-navegador-sprint3.txt`, `sprint3-resultados-modelo.txt` (`scripts/capture_sprint3.mjs`) |
| Pruebas de humo de la API | 22 de 22 con el modelo activo | `evidencias/sprint2-smoke-api.txt` |

Las pruebas automáticas usan un modelo ONNX diminuto construido en el propio test (rojo → cartón, verde → vidrio, azul → metal), así que **no dependen** de `ml/models/v1/model.onnx` ni de PyTorch.

## 8. Cómo usarlo

```bash
docker compose up -d --build          # la API carga ml/models/v1/model.onnx al arrancar
# PWA http://localhost:5173 → Escanear (foto de un objeto sobre fondo liso) → Aprende
node scripts/capture_sprint3.mjs      # recorrido real con fotos de test de TrashNet (requiere ml/data/raw)
```

Si el navegador muestra la versión anterior de la app, es la caché del Service Worker: *DevTools → Application → Service Workers → Unregister* y recargar con Ctrl + Shift + R.

## 9. Lo que sigue (Sprint 4 en adelante)

Capturar fotos en la UMB con las 15 clases (incluidos orgánicos), reevaluar con particiones por objeto, entrenar v2 y compararla con v1; corrección del resultado por el usuario (RF-29/30); reentrenamiento (RF-31).
