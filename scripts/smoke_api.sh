#!/usr/bin/env bash
# Prueba de humo de la API en marcha: verifica los criterios de aceptación de S1-06 de la Guía 5.
# Uso:  bash scripts/smoke_api.sh [URL_BASE]      (por defecto http://localhost:8000)
#
# Cada ejecución usa un correo nuevo, así que puede repetirse sin limpiar la base.
# Ojo: hace 7 llamadas a /auth/* y el límite es de 10 por minuto e IP (RNF-04). Si la repites
# en menos de un minuto puedes recibir 429: espera 60 s. Las validaciones 422 las cubre pytest.
set -u
BASE="${1:-http://localhost:8000}"
EMAIL="demo.$(date +%s)@umb.edu.co"
PASS="Clave-Segura-2026"
JSON='Content-Type: application/json'
FAILS=0
RATE_LIMITED=0

check() { # descripción, esperado, obtenido
  local shown="$3"
  case "$3" in [0-9]*) shown="HTTP $3" ;; esac
  [ "$3" = "429" ] && RATE_LIMITED=1
  if [ "$2" = "$3" ]; then
    printf 'OK    %-62s -> %s\n' "$1" "$shown"
  else
    printf 'FALLA %-62s -> esperado %s, obtenido %s\n' "$1" "$2" "$3"
    FAILS=$((FAILS + 1))
  fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
field() { sed -n "s/.*\"$1\":\"\([^\"]*\)\".*/\1/p"; }

echo "API: $BASE   usuario de prueba: $EMAIL"
check "GET /health"                                   200 "$(code "$BASE/health")"
check "GET /health/ready (base de datos alcanzable)"  200 "$(code "$BASE/health/ready")"
check "GET /docs (Swagger UI)"                        200 "$(code "$BASE/docs")"

check "POST /auth/register correo nuevo"              201 "$(code -X POST "$BASE/api/v1/auth/register" -H "$JSON" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"full_name\":\"Demo UMB\"}")"
UPPER="$(echo "$EMAIL" | tr '[:lower:]' '[:upper:]')"
check "POST /auth/register mismo correo (otra capitalización)" 409 "$(code -X POST "$BASE/api/v1/auth/register" -H "$JSON" -d "{\"email\":\"$UPPER\",\"password\":\"$PASS\"}")"

LOGIN="$(curl -s -X POST "$BASE/api/v1/auth/login" -H "$JSON" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")"
ACCESS="$(echo "$LOGIN" | field access_token)"
REFRESH="$(echo "$LOGIN" | field refresh_token)"
check "POST /auth/login credenciales correctas (devuelve tokens)" yes "$([ -n "$ACCESS" ] && [ -n "$REFRESH" ] && echo yes || echo no)"

WRONG="$(curl -s -w ' %{http_code}' -X POST "$BASE/api/v1/auth/login" -H "$JSON" -d "{\"email\":\"$EMAIL\",\"password\":\"Otra-Clave-9\"}")"
UNKNOWN="$(curl -s -w ' %{http_code}' -X POST "$BASE/api/v1/auth/login" -H "$JSON" -d '{"email":"nadie@umb.edu.co","password":"Otra-Clave-9"}')"
check "POST /auth/login contraseña incorrecta"        401 "${WRONG##* }"
check "POST /auth/login correo inexistente"           401 "${UNKNOWN##* }"
check "  mismo mensaje en ambos casos (no revela el campo)" same "$([ "$WRONG" = "$UNKNOWN" ] && echo same || echo different)"

check "GET /users/me con access token"                200 "$(code "$BASE/api/v1/users/me" -H "Authorization: Bearer $ACCESS")"
check "GET /users/me sin token"                       401 "$(code "$BASE/api/v1/users/me")"
check "GET /users/me usando el refresh token"         401 "$(code "$BASE/api/v1/users/me" -H "Authorization: Bearer $REFRESH")"
check "GET /users (solo admin) con usuario normal"    403 "$(code "$BASE/api/v1/users" -H "Authorization: Bearer $ACCESS")"
check "POST /auth/refresh con refresh token válido"   200 "$(code -X POST "$BASE/api/v1/auth/refresh" -H "$JSON" -d "{\"refresh_token\":\"$REFRESH\"}")"
check "POST /auth/refresh con el access token"        401 "$(code -X POST "$BASE/api/v1/auth/refresh" -H "$JSON" -d "{\"refresh_token\":\"$ACCESS\"}")"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "Todas las verificaciones pasaron."
else
  echo "$FAILS verificación(es) fallaron."
  [ "$RATE_LIMITED" -eq 1 ] && echo "Hubo respuestas 429: el límite de 10 solicitudes/min a /auth/* estaba agotado. Espera 60 s y repite."
  exit 1
fi
