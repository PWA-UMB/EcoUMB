# ml/ — modelo de clasificación de residuos

Entrenamiento, evaluación y versiones del modelo de clasificación por imagen. **En uso: v3** (MobileNetV3-Large sobre TrashNet + RealWaste, 8 clases con orgánicos). La API **no** depende de PyTorch: solo carga el `model.onnx` de la versión elegida con `onnxruntime`, en CPU.

```
ml/
├── src/common.py         rutas de los datos, clases, particiones 70/15/15 con semilla, transformaciones
├── src/augment.py        aumentos de campo (--robust): fondos aleatorios, oclusiones tipo mano
├── src/train.py          transfer learning: cabeza → ajuste fino; guarda la mejor época de validación
├── src/evaluate.py       evaluación única en test, exportación ONNX, métricas y matriz de confusión
├── src/select_views.py   elige con validación qué vistas promediar y escribe inference.json
├── models/v1, v2, v3/    lo que se despliega (v3 por defecto): model.onnx, labels.json, class_map.json,
│                         metrics.json, matriz de confusión, splits.json, train_log.csv, inference.json
│                         (v2, v3), config.json (v3), MODEL_CARD.md (v1, v3)
├── data/                 datos (NO se versionan; ver «Datos»)
└── requirements.txt      dependencias de entrenamiento
```

- **Ficha del modelo en uso:** [models/v3/MODEL_CARD.md](models/v3/MODEL_CARD.md) (datos, entrenamiento, resultados por clase y limitaciones). Léela antes de citar cifras: el modelo reconoce 8 clases, no los 15 objetos del catálogo UMB. La ficha de v1 sigue en [models/v1/MODEL_CARD.md](models/v1/MODEL_CARD.md); la v2 no tiene ficha propia (sus cifras están en `models/v2/metrics.json`). Evolución y decisiones (ADR 015–026): [docs/07](../docs/07-modelo-ia-y-modulo-educativo-sprint3.md).
- **Contrato con el backend:** el modelo predice clases (`labels.json`); `class_map.json` las asocia con objetos del catálogo (`waste_items.code`), y la bolsa la decide la base de datos (`waste_items → waste_categories`). Cambiar la asociación o la normativa no obliga a reentrenar.

## Versiones

| Versión | Arquitectura | Datos y clases | Entrenamiento | Macro F1 en test | Macro F1 por bolsa | ONNX |
|---|---|---|---|---|---|---|
| v1 | MobileNetV3-Small | TrashNet; 6 materiales, sin orgánicos | 5 + 12 épocas, CPU | 0,8707 (380 fotos) | 0,9035 (solo 2 bolsas) | 6,1 MB |
| v2 | MobileNetV3-Small | TrashNet + RealWaste; 8 clases | 3 + 15 épocas, CPU | 0,8378 (1 093 fotos) | 0,8928 (3 bolsas, no cumple) | 6,1 MB |
| **v3** | **MobileNetV3-Large** | TrashNet + RealWaste; 8 clases | 3 + 25 épocas, todo el extractor, GPU | **0,9235** (1 093 fotos) | **0,9428** (3 bolsas) | 16,8 MB |

Metas del SAD: Macro F1 ≥ 0,80 y Macro F1 por bolsa ≥ 0,90. Las cifras de v1 salen de otro conjunto de test (solo TrashNet) y no se comparan directamente con las de v2 y v3, que comparten particiones.

**v3 en test** (1 093 fotos, una sola evaluación, sobre el ONNX con el preprocesado de la API): Macro F1 0,9235 · exactitud 0,9167 · top-3 0,9817 · Macro F1 por bolsa 0,9428 · exactitud 0,8892 en las fotos de TrashNet y 0,9314 en las de RealWaste · 85,9 % de las fotos con confianza ≥ 0,65 (exactitud 0,970 en ellas). Latencia del modelo en CPU: mediana 3,65 ms, p95 7,16 ms. Fuente: [models/v3/metrics.json](models/v3/metrics.json).

## Datos (no están en git)

Los datasets **no se versionan**: `.gitignore` excluye `ml/data/*` (salvo `.gitkeep`), los pesos `ml/models/*/weights.pt` y los entornos `ml/.venv*/`. De cada versión sí se versiona lo que se despliega y su trazabilidad: `model.onnx`, `labels.json`, `class_map.json`, `metrics.json` (con el SHA-256 de cada ZIP), `splits.json`, `train_log.csv` e `inference.json` (v2 y v3).

| Dataset | Fuente | Contenido |
|---|---|---|
| TrashNet | Yang y Thung (2016), <https://github.com/garythung/trashnet> | 2 527 fotos, 6 materiales sobre fondo blanco |
| RealWaste | Single, Iranmanesh y Raad (2023), repositorio UCI, licencia CC BY 4.0 | 4 752 fotos de residuos reales en un relleno sanitario, 9 carpetas |

El repositorio no registra el enlace de descarga de RealWaste; para confirmar que tienes la misma copia de ambos datasets, compara `sha256sum ml/data/raw/*.zip` con `dataset.zip_sha256` de `models/v3/metrics.json`. Colócalos así (rutas fijas en `src/common.py`):

```
ml/data/raw/
├── dataset-resized.zip                          ZIP de TrashNet, descomprimido en ml/data/raw/
├── dataset-resized/<material>/*.jpg             cardboard, glass, metal, paper, plastic, trash
├── realwaste.zip                                ZIP de RealWaste, descomprimido en ml/data/raw/realwaste/
└── realwaste/realwaste-main/RealWaste/<carpeta>/*.jpg
        Cardboard, Food Organics, Glass, Metal, Miscellaneous Trash, Paper, Plastic, Textile Trash, Vegetation
```

- Deja también los ZIP en `ml/data/raw/`: `evaluate.py` calcula su SHA-256 y falla si no los encuentra.
- Carpetas de RealWaste → clases del modelo (`REALWASTE_TO_CLASS` en `common.py`): «Food Organics» → `organic_food`, «Vegetation» → `vegetation`, «Textile Trash» y «Miscellaneous Trash» → `trash`, y el resto a su material.
- Opcional: `ml/data/umb/<código del objeto>/*.jpg` con fotos reales de la UMB. `evaluate.py` las mide aparte y las lista una por una; **no se usan para entrenar** (RF-31 pendiente). Se exportan desde la app (desde la raíz del repo):

  ```bash
  docker compose exec api python -m scripts.export_feedback --out /tmp/umb_dataset   # --only-corrected: solo las corregidas
  docker compose cp api:/tmp/umb_dataset ml/data/umb
  ```

## Entorno

La v3 se entrenó en GPU NVIDIA (GTX 1660 Ti, ~25 min) con un entorno `.venv-gpu`:

```bash
cd ml
py -m venv .venv-gpu
.venv-gpu/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch torchvision   # GPU NVIDIA
.venv-gpu/Scripts/python -m pip install scikit-learn onnx onnxruntime pillow numpy matplotlib
```

v1 y v2 se entrenaron en CPU con `.venv` y `--index-url https://download.pytorch.org/whl/cpu` (ver la [ficha de v1](models/v1/MODEL_CARD.md)); `requirements.txt` lista las mismas dependencias. `train.py` usa CUDA si está disponible (imprime `dispositivo: cuda`) y, si no, la CPU; `evaluate.py` y `select_views.py` corren en CPU.

## Particiones, entrenamiento, evaluación y exportación

Desde `ml/`, la orden completa de la v3 (argumentos de [models/v3/config.json](models/v3/config.json)):

```bash
.venv-gpu/Scripts/python src/train.py --version v3 --dataset combined --robust --arch mobilenet_v3_large \
    --head-epochs 3 --fine-tune-epochs 25 --unfreeze-from 0 --fine-tune-lr 2e-4 --batch-size 64 --workers 10
.venv-gpu/Scripts/python src/evaluate.py --version v3 --dataset combined
.venv-gpu/Scripts/python src/select_views.py --version v3 --dataset combined
```

1. **Particiones:** no hay un paso aparte; `train.py` las genera al empezar (`make_splits` en `common.py`): 70/15/15 estratificado por fuente y clase, semilla 42, escritas en `data/splits_combined.json` (`--dataset combined`) o `data/splits.json` (`--dataset trashnet`). Con las mismas fotos se obtiene la misma partición (archivos ordenados y semilla fija); `evaluate.py` la copia a `models/<versión>/splits.json`, que sí se versiona. v2 y v3: 5 095 entrenamiento, 1 091 validación y 1 093 test.
2. **Entrenamiento (`train.py`):** fase 1 solo la cabeza (lr 1e-3); fase 2 ajuste fino desde el bloque `--unfreeze-from` (0 = todo el extractor) con `AdamW` y coseno; pérdida con pesos inversos a la frecuencia de clase y *label smoothing* 0,05. Guarda la época con mejor Macro F1 de **validación** en `weights.pt` (no versionado), junto con `train_log.csv` y `config.json`. El test no se usa.
3. **Evaluación y exportación ONNX (`evaluate.py`):** carga `weights.pt` con la arquitectura de `config.json`, exporta `model.onnx` (opset 17), mide la diferencia de logits entre PyTorch y ONNX, evalúa **una sola vez** en test con el preprocesado de la API y escribe `metrics.json`, `labels.json`, `class_map.json`, `splits.json` y la matriz de confusión.
4. **Vistas (`select_views.py`):** escribe `inference.json` y `views_selection.json` (ver «Vistas múltiples»).

Argumentos de `train.py` (entre paréntesis, el valor por defecto, que es el de v1): `--version` (v1), `--dataset` trashnet | combined (trashnet), `--robust`, `--arch` mobilenet_v3_small | mobilenet_v3_large | efficientnet_b0 (mobilenet_v3_small), `--head-epochs` (5), `--fine-tune-epochs` (12), `--unfreeze-from` (8), `--fine-tune-lr` (2e-4), `--batch-size` (32), `--workers` (4). `evaluate.py` y `select_views.py` aceptan `--version` y `--dataset`, y **por defecto usan `trashnet`**: con v2 y v3 hay que pasar `--dataset combined`. EfficientNet-B0 está disponible, pero no hay métricas guardadas con ella.

- **v1:** `src/train.py` y `src/evaluate.py` sin argumentos (≈ 10 min en CPU; ver su ficha).
- **v2:** `train.py` documenta `--version v2 --dataset combined --robust`, pero la v2 no guardó `config.json`: sus argumentos exactos no quedaron registrados.
- **Cuidado:** los scripts escriben en `models/<versión>/` y sobrescriben lo que haya. Como los pesos no se versionan, reexportar una versión exige reentrenarla; para experimentar usa una carpeta nueva (`--version v4`).

## Usar una versión concreta en la API

La API carga una carpeta de `models/` al arrancar: necesita `model.onnx`, `labels.json` y `class_map.json` (`inference.json` y `metrics.json` son opcionales) y registra la versión (el nombre de la carpeta) en `ml_model_versions` la primera vez que clasifica.

- **Docker:** `MODEL_VERSION=v1`, `v2` o `v3` (por defecto `v3`) en `.env` y `docker compose up -d api` desde la raíz. `docker-compose.yml` monta `./ml/models` en solo lectura y fija `MODEL_DIR=/srv/models/${MODEL_VERSION:-v3}`.
- **Sin Docker:** `CLASSIFIER=onnx` y `MODEL_DIR=../ml/models/v3` (desde `backend/`). El valor por defecto de `MODEL_DIR` en `backend/app/core/config.py` sigue siendo `../ml/models/v1`.
- **Nueva versión (RNF-17):** entrenar, evaluar y elegir vistas con `--version v4` y poner `MODEL_VERSION=v4`, sin reconstruir la imagen.

## Vistas múltiples: implementadas, no adoptadas

La API puede promediar varias vistas de la misma foto según `inference.json`: `center` (recorte central), `flip` (ese recorte espejado) y `full` (la foto completa a 224 × 224). `select_views.py` compara las opciones por Macro F1 de **validación** y solo adopta una si supera al recorte central en al menos 0,005. En v3 la mejor opción (central + espejo + completa) ganó 0,0042 (0,9370 frente a 0,9328) y en v2, 0,0016, así que ambas usan `{"views": ["center"]}`: una inferencia por foto en vez de tres. Activarlas es editar `inference.json` (p. ej. `{"views": ["center", "flip", "full"]}`) y reiniciar la API, sin tocar código. Las cifras de test de cada opción están en `views_selection.json` solo por transparencia.

## Límites del modelo (v3)

1. **Alcanza 8 de los 15 objetos del catálogo UMB.** No puede devolver vaso plástico, colilla de cigarrillo, empaque metalizado, servilleta sucia, vaso de café contaminado, cáscara de fruta ni bolsa de té o filtro de café. Las metas se cumplen para 8 clases, no para las 15 del SAD.
2. **Las cifras son optimistas frente al uso real:** ambos datasets son objetos sueltos sobre fondo blanco o piso liso, y las particiones aleatorias pueden dejar fotos casi idénticas en entrenamiento y test.
3. **Sin fotos tomadas en la UMB** en entrenamiento ni en test. Solo hay 2 fotos reales de una lata (una acertada con confianza 0,68; otra leída como «Papel limpio» con 0,35): es anecdótico, pero confirma que el modelo falla con escenas complejas (mano, rostro, habitación).
4. RealWaste es un solo relleno sanitario y una sola cámara. Una corrida por arquitectura, sin intervalos de confianza ni validación cruzada.
5. El 14 % de las predicciones de test tiene confianza < 0,65 y ahí la exactitud cae; en ese caso la app no afirma un residuo y ofrece las opciones más probables.
6. «Plástico» se muestra como «Botella PET» aunque sea otro plástico, y «basura general» como «Empaque de comida con residuos» (asociaciones provisionales en `class_map.json`, editables sin reentrenar).
