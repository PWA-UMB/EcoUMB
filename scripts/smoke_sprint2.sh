#!/usr/bin/env bash
# Prueba de humo del Sprint 2 contra la API en marcha: perfil, clasificación simulada, historial y
# privacidad de las fotos (RF-04, RF-09, RF-10, RF-16, RF-17).
# Uso:  bash scripts/smoke_sprint2.sh [URL_BASE]      (por defecto http://localhost:8000)
#
# Crea dos usuarios nuevos en cada ejecución (4 llamadas a /auth/*; el límite es 10 por minuto e IP).
set -u
BASE="${1:-http://localhost:8000}"
STAMP="$(date +%s)"
PASS="Clave-Segura-2026"
JSON='Content-Type: application/json'
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# curl de Windows (Git Bash) no entiende rutas /tmp/...: se le entrega la ruta en formato de Windows.
WORK_FOR_CURL="$(cygpath -m "$WORK" 2>/dev/null || printf "%s" "$WORK")"
FAILS=0

check() { # descripción, esperado, obtenido
  local shown="$3"
  case "$3" in [0-9][0-9][0-9]) shown="HTTP $3" ;; esac
  if [ "$2" = "$3" ]; then
    printf 'OK    %-64s -> %s\n' "$1" "$shown"
  else
    printf 'FALLA %-64s -> esperado %s, obtenido %s\n' "$1" "$2" "$3"
    FAILS=$((FAILS + 1))
  fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
field() { sed -n "s/.*\"$1\":\"\([^\"]*\)\".*/\1/p"; }

# Imágenes de prueba: dos PNG reales de 8x8 (con el modelo de IA la API decodifica la foto, así que deben ser válidas).
echo iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGM8YWPEgA0wYRUdtBIA92IBRkMQziEAAAAASUVORK5CYII= | base64 -d > "$WORK/a.png"
echo iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGPUiDrBgA0wYRUdtBIABbMBWhzDM6AAAAAASUVORK5CYII= | base64 -d > "$WORK/c.png"
printf 'esto no es una imagen' > "$WORK/falsa.jpg"
: > "$WORK/vacia.jpg"
head -c 6000000 /dev/zero > "$WORK/grande.bin" && printf '\xff\xd8\xff' | dd of="$WORK/grande.bin" conv=notrunc 2>/dev/null

register_and_login() { # correo -> imprime access token
  curl -s -o /dev/null -X POST "$BASE/api/v1/auth/register" -H "$JSON" -d "{\"email\":\"$1\",\"password\":\"$PASS\",\"full_name\":\"Prueba Sprint 2\"}"
  curl -s -X POST "$BASE/api/v1/auth/login" -H "$JSON" -d "{\"email\":\"$1\",\"password\":\"$PASS\"}" | field access_token
}

echo "API: $BASE   ejecución: $STAMP"
TOKEN_A="$(register_and_login "s2.a.$STAMP@umb.edu.co")"
TOKEN_B="$(register_and_login "s2.b.$STAMP@umb.edu.co")"
AUTH_A="Authorization: Bearer $TOKEN_A"
AUTH_B="Authorization: Bearer $TOKEN_B"
check "Usuarios A y B con sesión iniciada" "yes" "$([ -n "$TOKEN_A" ] && [ -n "$TOKEN_B" ] && echo yes || echo no)"

echo "--- Perfil (RF-04)"
# La ó va escapada (\u00f3): la consola de Windows no envía UTF-8 en los argumentos de curl.
check "PATCH /users/me cambia el nombre" "Laura Gómez" \
  "$(curl -s -X PATCH "$BASE/api/v1/users/me" -H "$AUTH_A" -H "$JSON" -d '{"full_name":"  Laura G\u00f3mez  "}' | field full_name)"
check "GET /users/me conserva el cambio" "Laura Gómez" "$(curl -s "$BASE/api/v1/users/me" -H "$AUTH_A" | field full_name)"
check "PATCH /users/me no permite cambiar el rol (extra=forbid)" "422" \
  "$(code -X PATCH "$BASE/api/v1/users/me" -H "$AUTH_A" -H "$JSON" -d '{"full_name":"x","role":"admin"}')"
check "PATCH /users/me sin token" "401" "$(code -X PATCH "$BASE/api/v1/users/me" -H "$JSON" -d '{"full_name":"x"}')"

echo "--- Clasificación simulada (RF-09, RF-10, RF-13 a RF-15)"
CREATED="$(curl -s -w '\n%{http_code}' -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/a.png;type=image/png")"
STATUS="$(printf '%s' "$CREATED" | tail -n1)"
BODY="$(printf '%s' "$CREATED" | sed '$d')"
check "POST /classifications con PNG rojo" "201" "$STATUS"
check "  la respuesta declara si es simulada (true/false)" "yes" "$(printf '%s' "$BODY" | grep -Eq '"simulated":(true|false)' && echo yes || echo no)"
check "  incluye las tres mejores opciones" "yes" "$(printf '%s' "$BODY" | grep -q '"top3":\[{' && echo yes || echo no)"
CID="$(printf '%s' "$BODY" | field id)"
check "POST /classifications con otro PNG (azul)" "201" "$(code -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/c.png;type=image/png")"
R1="$(curl -s -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/a.png;type=image/png" | field code)"
R2="$(curl -s -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/a.png;type=image/png" | field code)"
check "La misma foto da el mismo resultado (determinista)" "yes" "$([ -n "$R1" ] && [ "$R1" = "$R2" ] && echo yes || echo no)"
check "Archivo que no es imagen (aunque se llame .jpg)" "415" "$(code -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/falsa.jpg;type=image/jpeg")"
check "Archivo vacío" "422" "$(code -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/vacia.jpg;type=image/jpeg")"
check "Imagen de más de 5 MB" "413" "$(code -X POST "$BASE/api/v1/classifications" -H "$AUTH_A" -F "image=@$WORK_FOR_CURL/grande.bin;type=image/jpeg")"
check "Sin token" "401" "$(code -X POST "$BASE/api/v1/classifications" -F "image=@$WORK_FOR_CURL/a.png;type=image/png")"

echo "--- Historial (RF-16, RF-17)"
check "GET /classifications/me del usuario A (4 registros)" "4" "$(curl -s "$BASE/api/v1/classifications/me" -H "$AUTH_A" | sed -n 's/.*"total":\([0-9]*\).*/\1/p')"
check "  paginación: limit=2 devuelve 2 elementos" "2" \
  "$(curl -s "$BASE/api/v1/classifications/me?limit=2" -H "$AUTH_A" | grep -o '"image_url"' | wc -l | tr -d ' ')"
check "  limit fuera de rango (0)" "422" "$(code "$BASE/api/v1/classifications/me?limit=0" -H "$AUTH_A")"
check "GET /classifications/me del usuario B (no ve lo de A)" "0" "$(curl -s "$BASE/api/v1/classifications/me" -H "$AUTH_B" | sed -n 's/.*"total":\([0-9]*\).*/\1/p')"

echo "--- Privacidad de las fotos"
check "Foto con el token del dueño" "200" "$(code "$BASE/api/v1/classifications/$CID/image" -H "$AUTH_A")"
check "Foto sin token" "401" "$(code "$BASE/api/v1/classifications/$CID/image")"
check "Foto con el token de otro usuario (no revela que existe)" "404" "$(code "$BASE/api/v1/classifications/$CID/image" -H "$AUTH_B")"
check "Cabecera Content-Type de la foto" "image/png" "$(curl -s -o /dev/null -w '%{content_type}' "$BASE/api/v1/classifications/$CID/image" -H "$AUTH_A")"

echo
if [ "$FAILS" -eq 0 ]; then echo "Resultado: todas las comprobaciones pasaron."; else echo "Resultado: $FAILS comprobación(es) fallaron."; exit 1; fi
