# Ficha del modelo — EcoUMB v3

Modelo de clasificación de residuos por imagen (8 clases, incluye orgánicos), entrenado el 18 de septiembre de 2026. Todas las cifras salen de `metrics.json`, `train_log.csv` y `views_selection.json` de esta carpeta, generados por `ml/src/train.py`, `evaluate.py` y `select_views.py`. La ficha de la versión anterior (solo TrashNet, 6 clases) sigue en [`../v1/MODEL_CARD.md`](../v1/MODEL_CARD.md).

## Resumen

| | |
|---|---|
| Arquitectura | MobileNetV3-Large preentrenada en ImageNet + cabeza de 8 clases; ajuste fino de **todo** el extractor |
| Datos | TrashNet (2 527 fotos) + RealWaste (4 752 fotos reales de relleno sanitario) = 7 279 fotos |
| Clases | cartón, vidrio, metal, papel, plástico, basura general, **comida orgánica**, **vegetación** |
| Entrada / salida | Imagen RGB 224 × 224 → probabilidades de 8 clases |
| Formato desplegado | ONNX (opset 17), 16,8 MB, `onnxruntime` en CPU |
| Latencia | mediana 3,7 ms, p95 7,2 ms por imagen (solo el modelo, CPU) |
| Entrenamiento | 28 épocas en una GTX 1660 Ti (~25 min), semilla 42 |

## Qué predice (y qué no)

El modelo predice **materiales**; `class_map.json` asocia cada uno con el objeto del catálogo UMB que mejor lo representa. La bolsa la decide la base de datos, no el modelo.

| Clase del modelo | Objeto UMB que se muestra | Bolsa |
|---|---|---|
| cardboard | Cartón limpio | blanca |
| glass | Botella de vidrio | blanca |
| metal | Lata de aluminio | blanca |
| paper | Papel limpio | blanca |
| plastic | Botella PET | blanca |
| trash (basura general y ropa desechada) | Empaque de comida con residuos | negra |
| organic_food | Restos de comida cocinada | **verde** |
| vegetation | Residuo de poda / hojas | **verde** |

Alcance real:

- **Alcanza 8 de los 15 objetos del catálogo.** No puede devolver: vaso plástico, colilla de cigarrillo, empaque metalizado, servilleta sucia, vaso de café contaminado, **cáscara de fruta** ni bolsa de té o filtro de café. Una cáscara de fruta sale como «Restos de comida» (misma bolsa verde, distinto nombre).
- «Plástico» se muestra como «Botella PET» aunque sea otro plástico; «basura general» como «Empaque de comida con residuos». Son asociaciones provisionales y editables sin reentrenar.
- Para lo que no reconoce baja la confianza: con confianza baja (< 0,65) la app **no afirma** un residuo y ofrece las opciones más probables.

## Datos y particiones

- **TrashNet** (Yang y Thung, 2016): objetos sueltos sobre fondo blanco. **RealWaste** (Single, Iranmanesh y Raad, 2023, CC BY 4.0, UCI): fotos de residuos reales sobre piso en un relleno, con «Food Organics» y «Vegetation». Los SHA-256 de los ZIP están en `metrics.json`.
- Partición 70 / 15 / 15 estratificada por **fuente y clase**, semilla fija (`splits.json`): 5 095 entrenamiento, 1 091 validación, 1 093 test (379 de TrashNet y 714 de RealWaste).
- Test por clase: cartón 129, vidrio 138, metal 181, papel 164, plástico 212, basura 142, comida orgánica 61, vegetación 66.
- **Sin fotos tomadas en la UMB.** Solo hay dos fotos reales de una lata etiquetadas a mano (ver abajo).

## Entrenamiento

- Fase 1 (3 épocas): cabeza, `AdamW` lr 1e-3. Fase 2 (25 épocas): todo el extractor, lr 2e-4 con coseno, lote 64, decaimiento 1e-4.
- Pérdida: entropía cruzada con pesos inversos a la frecuencia de clase y *label smoothing* 0,05.
- **Aumentos de campo** (`ml/src/augment.py`), pensados para romper atajos de TrashNet (fondo blanco, color): objeto recortado y pegado sobre fondos aleatorios (solo en fotos de TrashNet), manchas tipo mano u oclusión, cambios fuertes de matiz, escala de grises, desenfoque, borrado aleatorio y recortes de 40–100 %.
- Se conservó la época con mejor Macro F1 de **validación** (época 20: 0,9328). El test se evaluó una sola vez por modelo y no se usó para decidir arquitectura ni vistas.

## Resultados en test (1 093 fotos)

Medidos sobre el modelo ONNX con el mismo preprocesado que usa la API. Se verificó que PyTorch y ONNX difieren menos de 1 × 10⁻⁵ en los logits.

| Métrica | v3 | v2 (MobileNetV3-Small) | Meta del SAD |
|---|---|---|---|
| **Macro F1 (8 clases)** | **0,9235** | 0,8378 | ≥ 0,80 |
| Accuracy top-1 | 0,9167 | 0,8262 | — |
| Accuracy top-3 | 0,9817 | 0,9607 | — |
| **Macro F1 por bolsa (3 bolsas)** | **0,9428** | 0,8928 | ≥ 0,90 |
| Solo fotos de TrashNet (accuracy) | 0,8892 | 0,7599 | — |
| Solo fotos de RealWaste (accuracy) | 0,9314 | 0,8613 | — |
| Fotos con confianza ≥ 0,65 | 85,9 % | 73,8 % | — |
| Accuracy en esas fotos | 0,970 | 0,927 | — |

| Clase | Precisión | Exhaustividad | F1 | Fotos |
|---|---|---|---|---|
| cardboard | 0,932 | 0,954 | 0,943 | 129 |
| glass | 0,935 | 0,935 | 0,935 | 138 |
| metal | 0,884 | 0,967 | 0,923 | 181 |
| paper | 0,950 | 0,927 | 0,938 | 164 |
| plastic | 0,904 | 0,844 | 0,873 | 212 |
| trash | 0,895 | 0,845 | 0,870 | 142 |
| **organic_food** | 0,894 | 0,967 | 0,929 | 61 |
| **vegetation** | 0,970 | 0,985 | 0,977 | 66 |

**Orgánicos:** 59 de 61 fotos de comida y 65 de 66 de vegetación acertadas; el único cruce con otra bolsa importante es «trash → comida» (6 de 142). La confusión más frecuente sigue siendo entre materiales blancos (plástico ↔ vidrio/metal).

**Promediar vistas** (recorte central, espejo, foto completa) se evaluó y **no se adoptó**: la mejora en validación fue de 0,004 (< 0,005 exigido) — `views_selection.json`.

## Fotos reales de la UMB (n = 2, anecdótica)

Dos fotos de una lata de cerveza sostenida a la mano frente a una habitación (etiquetadas «lata de aluminio» a partir de la descripción del usuario). **No se usaron para entrenar.**

| Foto | Resultado | Confianza | ¿Acierta? |
|---|---|---|---|
| lata de cerveza, plano lateral | Lata de aluminio | 0,68 (media) | Sí |
| lata de cerveza, con rostro y mano detrás | Papel limpio | 0,35 (**baja**) | No, pero la app lo marca como incierto |

Con solo dos fotos no hay porcentaje válido. La conclusión honesta es: **el modelo sigue fallando en fotos con mucha escena alrededor** (mano, rostro, cuarto); ahora lo hace con confianza baja, y la app pide al usuario corregir.

## Limitaciones — leer antes de citar estas cifras

1. **La meta se cumple para 8 clases, no para las 15 del catálogo UMB.** Faltan 7 objetos y todos los residuos específicos de la universidad (vasos de café, colillas, empaques metalizados…).
2. **Las cifras son optimistas frente al uso real.** Ambos datasets son fotos de objetos sueltos (fondo blanco o piso liso), sin manos, personas ni canecas llenas, y las particiones aleatorias pueden dejar fotos casi idénticas en entrenamiento y test. La única medida con fotos reales de uso es la de arriba (n = 2).
3. RealWaste es una sola ubicación (un relleno sanitario) y una sola cámara.
4. Una corrida por arquitectura, sin intervalos de confianza ni validación cruzada.
5. El 14 % de las predicciones tiene confianza < 0,65 y ahí la exactitud cae; la interfaz lo maneja mostrando opciones y pidiendo confirmación.

## Cómo reproducirlo

```bash
cd ml
py -m venv .venv-gpu
.venv-gpu/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch torchvision   # GPU NVIDIA
.venv-gpu/Scripts/python -m pip install scikit-learn onnx onnxruntime pillow numpy matplotlib
# descargar TrashNet y RealWaste a ml/data/raw/ (ver ml/README.md)
.venv-gpu/Scripts/python src/train.py --version v3 --dataset combined --robust --arch mobilenet_v3_large \
    --head-epochs 3 --fine-tune-epochs 25 --unfreeze-from 0 --fine-tune-lr 2e-4 --batch-size 64 --workers 10
.venv-gpu/Scripts/python src/evaluate.py --version v3 --dataset combined
.venv-gpu/Scripts/python src/select_views.py --version v3 --dataset combined
```

## Siguiente versión

Reentrenar con las fotos que los usuarios confirmen o corrijan en la app (`python -m scripts.export_feedback`), añadir los 7 objetos que faltan del catálogo, y medir con un conjunto de fotos tomadas en la UMB que no se use para entrenar.
