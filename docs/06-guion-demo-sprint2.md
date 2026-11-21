# Guion de la demostración — Sprint 2

> **Actualización (Sprint 3):** con el modelo v1 activo el aviso «Resultado simulado» ya no aparece; en su lugar el resultado dice «Modelo v1» y su alcance (6 materiales, sin orgánicos). Lo que se dice sobre la exactitud cambió: ver [docs/07](07-modelo-ia-y-modulo-educativo-sprint3.md) §4. Para la demo usa fotos de un objeto **sobre fondo liso**.

Ensayarlo completo antes de la clase. Es el ciclo que pide el Plan de Sprints: **foto → resultado simulado → registro**, con la PWA instalable.

**Preparación:** Docker Desktop encendido; `docker compose up -d --build` ya ejecutado (los datos se conservan); dos cuentas listas (un usuario normal y, si se quiere mostrar RBAC, un administrador); una foto de un residuo real en el teléfono o en el computador. **Aclarar desde el inicio que el resultado es simulado** (el modelo de IA real es el Sprint 3): la interfaz lo dice en cada resultado.

| # | Paso | Acción | Qué debe verse | Evidencia real ya generada |
|---|---|---|---|---|
| 1 | Entorno | `docker compose ps` | `postgres`, `redis`, `api` y `web` sanos | `capturas/term-01-docker-compose-ps.png` |
| 2 | Inicio de sesión | <http://localhost:5173/login> | Home con saludo, puntos, botón «Escanear un residuo» y últimas clasificaciones | `capturas/s2-01-inicio-escritorio.png` |
| 3 | Captura por cámara (RF-09) | **Escanear → Abrir la cámara** (aceptar el permiso) → **Tomar foto** | Vista en vivo y luego la vista previa de la foto | `capturas/s2-03…`, `s2-04…` |
| 4 | Clasificación simulada | **Clasificar** | Objeto, **bolsa** (blanca/negra/verde), consejo y confianza; aviso «Resultado simulado» | `capturas/s2-05-resultado-camara-movil.png` |
| 5 | Selección desde galería (RF-10) | **Escanear otro residuo → Elegir de la galería** | Vista previa y resultado; **la misma foto da siempre el mismo resultado**; con confianza baja la app no afirma un residuo y ofrece opciones | `capturas/s2-06…`, `s2-07…`, `s2-08…` (confianza baja) |
| 6 | Historial (RF-16/17) | Pestaña **Historial** | Lista con miniatura, objeto, bolsa, confianza y fecha; «Cargar más» si hay más de 10 | `capturas/s2-09…`, `s2-10…` |
| 7 | Perfil (RF-04) | Pestaña **Perfil** → cambiar el nombre → **Guardar cambios** | «Perfil actualizado»; el nombre nuevo aparece en Inicio y persiste al recargar | `capturas/s2-11…`, `s2-12…` |
| 8 | PWA instalable | En Edge/Chrome, ícono de instalar en la barra de direcciones (o botón «Instalar la aplicación» en Inicio) | Se instala y abre en ventana propia | `evidencias/pwa-instalabilidad.txt` (0 errores de instalabilidad) |
| 9 | API y privacidad (Swagger) | <http://localhost:8000/docs> → *Authorize* → `POST /classifications` con una imagen | 201 con el JSON; con un `.txt` renombrado a `.jpg` ⇒ **415**; la foto con el token de otro usuario ⇒ **404** | `evidencias/sprint2-smoke-api.txt` |
| 10 | Pruebas | `cd backend && pytest --cov=app` y `cd frontend && npm test` | 124 y 72 pruebas en verde | `evidencias/sprint2-backend-pytest.txt`, `sprint2-frontend-vitest.txt` |

**Comandos de apoyo**

```bash
bash scripts/smoke_sprint2.sh             # 22 comprobaciones contra la API viva (usa 4 llamadas a /auth/*; espera 60 s entre corridas)
node scripts/capture_sprint2.mjs          # recorre la PWA real en Edge y regenera las capturas s2-*.png
docker compose logs -f api                # logs JSON estructurados de la API
```

## Si algo falla en vivo

- **No hay permiso de cámara o el equipo no tiene:** la pantalla lo explica en español y deja la galería disponible; úsala (es un flujo válido, RF-10).
- **HTTP 429:** se superó el límite (10 clasificaciones por minuto por usuario, 10 llamadas a `/auth/*` por minuto por IP). Esperar 60 s.
- **No aparece el botón de instalar:** el navegador solo lo ofrece si la PWA no está instalada ya y se abre en `localhost` o HTTPS; probar en una ventana nueva o revisar *DevTools → Application → Manifest*.

## Lo que hay que decir con honestidad

- La clasificación es **simulada** y determinista por foto; no hay precisión que medir todavía.
- La cámara se probó automáticamente con la cámara de prueba de Edge; conviene mostrar además un teléfono real.
- Puntos, logros y módulo educativo son de los sprints 3 y 5: hoy `points_awarded` es 0.
