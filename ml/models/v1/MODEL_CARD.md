# Ficha del modelo — EcoUMB v1

Modelo de clasificación de residuos por imagen, entrenado el 18 de septiembre de 2026 (Sprint 3). Todas las cifras de este documento salen de `metrics.json` y `train_log.csv`, generados por `ml/src/train.py` y `ml/src/evaluate.py`.

## Resumen

| | |
|---|---|
| Arquitectura | MobileNetV3-Small preentrenada en ImageNet + cabeza de 6 clases (transfer learning, SAD §7.2) |
| Datos | TrashNet (`dataset-resized`, 2 527 fotos, 6 clases de material) |
| Entrada / salida | Imagen RGB 224 × 224 → probabilidades de 6 materiales |
| Formato desplegado | ONNX (opset 17), 6,1 MB, inferencia con `onnxruntime` en CPU |
| Latencia | mediana 1,7 ms, p95 2,6 ms por imagen (solo el modelo, CPU; la API suma decodificar y guardar la foto) |
| Semilla | 42 (particiones y entrenamiento) |

## Qué predice (y qué no)

TrashNet solo distingue **materiales**: `cardboard`, `glass`, `metal`, `paper`, `plastic`, `trash`. El catálogo UMB tiene 15 objetos en 3 bolsas. `class_map.json` asocia cada material con el objeto del catálogo que mejor lo representa; **esta asociación es provisional** y se puede cambiar sin reentrenar:

| Material del modelo | Objeto UMB que se muestra | Bolsa (la decide la base de datos) |
|---|---|---|
| cardboard | Cartón limpio | blanca |
| glass | Botella de vidrio | blanca |
| metal | Lata de aluminio | blanca |
| paper | Papel limpio | blanca |
| plastic | Botella PET | blanca |
| trash | Empaque de comida con residuos | negra |

Consecuencias que hay que decir en voz alta:

- **Solo 6 de los 15 objetos del catálogo son alcanzables.** No puede devolver vaso de café contaminado, colilla, servilleta sucia, empaque metalizado ni ningún residuo **orgánico** (la bolsa verde). Para esos casos se equivocará con seguridad aparente o bajará la confianza.
- «Plástico» se muestra como «Botella PET» aunque la foto sea de otro plástico (una bolsa, un vaso): el modelo no distingue entre plásticos.
- La app lo declara en cada resultado real («aún no reconoce residuos orgánicos»).

## Datos y particiones

- Fuente: TrashNet (Yang y Thung, 2016), descargado de <https://github.com/garythung/trashnet>; SHA-256 del ZIP en `metrics.json`.
- Partición estratificada por clase, 70 / 15 / 15 con semilla fija (`splits.json`): 1 768 entrenamiento, 379 validación, 380 test. Una foto está en un solo conjunto.
- Conjunto de test (380 fotos): cardboard 60, glass 76, metal 62, paper 89, plastic 73, trash 20.
- **Sin fotos tomadas en la UMB.** El SAD prevé combinarlas con TrashNet; aún no existen.

## Entrenamiento

- Fase 1 (5 épocas): solo la cabeza, `AdamW` lr 1e-3. Fase 2 (12 épocas): además los bloques 8–12 del extractor, lr 2e-4 con coseno.
- Pérdida: entropía cruzada con pesos inversos a la frecuencia de clase (`trash` tiene ~4 veces menos fotos) y *label smoothing* 0,05.
- Aumentos: recorte aleatorio (60–100 %), espejo horizontal, rotación ±20°, brillo/contraste/saturación.
- Se conservó la época con mejor Macro F1 de **validación** (época 15: 0,8486). El test no se usó para decidir nada y se evaluó una sola vez.

## Resultados en test (380 fotos)

Medidos sobre el modelo ONNX con el mismo preprocesado que usa la API (NumPy + Pillow). El clasificador de la API se probó por separado sobre las mismas 380 fotos y reproduce las cifras exactas.

| Métrica | Valor | Meta del SAD |
|---|---|---|
| **Macro F1 (6 materiales)** | **0,8707** | ≥ 0,80 |
| Accuracy top-1 | 0,8763 | — |
| Accuracy top-3 | 0,9842 | — |
| Macro F1 por categoría de bolsa | 0,9035 | ≥ 0,90 (ver limitación) |
| Fotos con confianza ≥ 0,65 | 78,9 % | — |
| Accuracy en esas fotos | 0,960 | — |

| Clase | Precisión | Exhaustividad | F1 | Fotos |
|---|---|---|---|---|
| cardboard | 0,931 | 0,900 | 0,915 | 60 |
| glass | 0,812 | 0,908 | 0,857 | 76 |
| metal | 0,864 | 0,919 | 0,891 | 62 |
| paper | 0,917 | 0,865 | 0,890 | 89 |
| plastic | 0,921 | 0,795 | 0,853 | 73 |
| trash | 0,750 | 0,900 | 0,818 | 20 |

Confusión principal (`confusion_matrix.png`): 8 de 73 plásticos se leen como vidrio; 2 de 20 «trash» se leen como otro material y 6 fotos de otras clases se leen como «trash».

## Limitaciones — leer antes de citar estas cifras

1. **La meta de Macro F1 ≥ 0,80 se cumple para 6 materiales, no para las 15 clases del catálogo UMB.** No es la misma medición que fija el SAD; sigue pendiente evaluar las 15 clases con fotos propias.
2. **El «Macro F1 por categoría» (0,9035) solo promedia 2 categorías** (aprovechable y no aprovechable): TrashNet no tiene residuos orgánicos, así que la bolsa verde no está medida. Cumplir esa meta con dos categorías no demuestra que se cumpla con tres.
3. **TrashNet contiene fotos casi duplicadas** (el mismo objeto fotografiado varias veces) y las particiones aleatorias pueden dejar versiones parecidas en entrenamiento y test. Las cifras probablemente son **optimistas** frente a fotos reales.
4. **Condiciones controladas:** objetos aislados sobre fondo blanco. En una caneca, con mala luz o varios residuos juntos el rendimiento no está medido y se espera peor.
5. Solo 20 fotos de «trash» en test: su F1 (0,818) tiene un margen de error grande.
6. No hay intervalos de confianza ni validación cruzada; es una sola corrida con una sola semilla.

## Cómo reproducirlo

```bash
cd ml
py -m venv .venv
.venv/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
.venv/Scripts/python -m pip install scikit-learn onnx onnxruntime pillow numpy matplotlib
# descargar TrashNet a ml/data/raw/dataset-resized.zip y descomprimir en ml/data/raw/
.venv/Scripts/python src/train.py       # ~10 min en CPU; escribe models/v1/weights.pt y train_log.csv
.venv/Scripts/python src/evaluate.py    # evalúa en test una vez; escribe model.onnx, metrics.json, matriz
```

## Siguiente versión (v2)

Fotos tomadas en la UMB con las 15 clases (incluidos los orgánicos), reevaluar con particiones que separen objetos (no solo fotos), medir sobre las 15 clases y por categoría con las tres bolsas, y comparar contra este v1 antes de reemplazarlo (SAD §7.6).
