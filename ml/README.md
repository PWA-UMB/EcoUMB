# ml/ — modelo de clasificación de residuos

Entrenamiento y evaluación del modelo v1 (Sprint 3). La API **no** depende de PyTorch: solo carga el `model.onnx` con `onnxruntime`.

```
ml/
├── src/common.py        constantes, particiones 70/15/15 con semilla, transformaciones
├── src/train.py         MobileNetV3-Small + transfer learning (cabeza → ajuste fino)
├── src/evaluate.py      evaluación única en test, exportación ONNX, métricas y ficha
├── models/v1/           lo que se despliega: model.onnx, labels.json, class_map.json,
│                        metrics.json, matriz de confusión, splits.json, MODEL_CARD.md
├── data/                dataset (NO se versiona; ver la ficha del modelo)
└── requirements.txt     dependencias de entrenamiento
```

- **Ficha del modelo, resultados y limitaciones:** [models/v1/MODEL_CARD.md](models/v1/MODEL_CARD.md). Léela antes de citar cifras: el modelo reconoce 6 materiales, no las 15 clases UMB ni residuos orgánicos.
- **Contrato con el backend:** el modelo predice materiales (`labels.json`); `class_map.json` los asocia con objetos del catálogo (`waste_items.code`), y la bolsa la decide la base de datos (`waste_items → waste_categories`). Cambiar la asociación o la normativa no obliga a reentrenar.
- **Actualizar el modelo (RNF-17):** crear `models/v2/` con los mismos archivos y apuntar `MODEL_DIR` a esa carpeta. La API registra cada versión en `ml_model_versions` al usarla.
- **Reproducir:** ver «Cómo reproducirlo» en la ficha (≈ 10 min en CPU).
