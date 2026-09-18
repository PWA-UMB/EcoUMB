# ml/ — servicio de Machine Learning (reservado)

Sin código en el Sprint 1. La estructura existe para cumplir S1-01 y para que el resto del sistema ya conozca el contrato del modelo.

Plan (SAD §7 y Plan de Sprints, Sprint 3–4):

- `data/` — dataset bootstrap (TrashNet + TACO, mapeado a las 15 clases del catálogo UMB) y capturas propias. **No se versiona en git.**
- `notebooks/` — análisis exploratorio (EDA) y entrenamiento inicial (S1-10, prioridad P2).
- `src/` — pipeline de entrenamiento con MobileNetV3-Small (transfer learning), seguimiento con MLflow y evaluación con F1 por objeto y por categoría.

Contrato con el backend: el modelo predice una de las 15 clases (`waste_items.class_id` 0..14, ya sembradas en la base de datos) y la categoría/bolsa se obtiene por mapeo en `waste_items → waste_categories`. Cambiar la normativa no obliga a reentrenar.
