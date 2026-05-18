#!/usr/bin/env bash
# Цепочка SSN → DL → CR.
#
# Официальная документация USFULL: https://usfull.info/service/docs/
# Хост в примерах: https://usfull.pro
#
# Self-hosted lookup_api:
#   export LOOKUP_API_KEY="..."
#   export LOOKUP_API_BASE_URL="http://127.0.0.1:8082"
#
# USFULL (логин/пароль из ЛК — для Basic Auth на search, как в доке):
#   export LOOKUP_API_KEY="..."
#   export LOOKUP_API_BASE_URL="https://usfull.pro"
#   export LOOKUP_API_BASIC_AUTH="логин:пароль"
#
# Для USFULL нужны DOB в DL/CR — заполните последнее поле в строках PEOPLE.
#
# Нужны: curl, jq

set -euo pipefail

BASE_URL="${LOOKUP_API_BASE_URL:-http://127.0.0.1:8082}"
BASE_URL="${BASE_URL%/}"
API_KEY="${LOOKUP_API_KEY:?Задайте LOOKUP_API_KEY}"

USER_AGENT="${LOOKUP_API_USER_AGENT:-LookupBot/1.0}"

# Хост USFULL: заголовок X-API-Key для DL/CR, тело CR как в https://usfull.info/service/docs/
IS_USFULL_HOST=0
if [[ "${BASE_URL}" == *"usfull.pro"* || "${BASE_URL}" == *"usfull.info"* ]]; then
  IS_USFULL_HOST=1
fi

CURL_AUTH_SEARCH=()
if [[ -n "${LOOKUP_API_BASIC_AUTH:-}" ]]; then
  CURL_AUTH_SEARCH=(-u "${LOOKUP_API_BASIC_AUTH}")
fi

post_search() {
  curl -sS -X POST "${BASE_URL}/api/search/" \
    -H "X-API-KEY: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${USER_AGENT}" \
    "${CURL_AUTH_SEARCH[@]}" \
    -d "$1"
}

post_dl() {
  local key_h="X-API-KEY"
  [[ "${IS_USFULL_HOST}" == "1" ]] && key_h="X-API-Key"
  curl -sS -X POST "${BASE_URL}/api/dl/" \
    -H "${key_h}: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${USER_AGENT}" \
    -d "$1"
}

post_cr() {
  local key_h="X-API-KEY"
  [[ "${IS_USFULL_HOST}" == "1" ]] && key_h="X-API-Key"
  curl -sS -X POST "${BASE_URL}/api/cr/" \
    -H "${key_h}: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -H "User-Agent: ${USER_AGENT}" \
    -d "$1"
}

echo "=== Base: ${BASE_URL} (USFULL host: ${IS_USFULL_HOST}) ==="
if [[ "${IS_USFULL_HOST}" == "1" ]] && [[ -z "${LOOKUP_API_BASIC_AUTH:-}" ]]; then
  echo "!!! Для USFULL обычно нужен LOOKUP_API_BASIC_AUTH=логин:пароль для /api/search/ (см. https://usfull.info/service/docs/)"
fi
echo

# slug|firstname|middlename|lastname|city|st|zip|first_dl|last_dl|street|zip_dl|dob
# firstname — только имя; middle — отдельное поле (инициал или полное middle).
# DOB: для USFULL DL/CR обязателен (форматы — в доке). Для self-hosted можно оставить пустым.
while IFS='|' read -r slug fn mn ln city st zip fdl ldl street zipdl dob; do
  [[ -z "${slug}" || "${slug}" =~ ^# ]] && continue

  echo "────────── ${slug} ──────────"

  ssn_body=$(jq -n \
    --arg fn "$fn" --arg mn "$mn" --arg ln "$ln" \
    --arg city "$city" --arg st "$st" --arg zip "$zip" \
    '{firstname:$fn, lastname:$ln, city:$city, st:$st, zip:$zip}
     + (if ($mn|length)>0 then {middlename:$mn} else {} end)')
  echo "POST /api/search/"
  search_json=$(post_search "${ssn_body}")
  echo "${search_json}" | jq .

  ssn=$(echo "${search_json}" | jq -r '.results[0].ssn // empty' | tr -d '- ')
  if [[ -n "${ssn}" ]]; then
    echo "→ SSN из ответа: ${ssn}"
  else
    echo "→ SSN не найден."
  fi

  # DL
  if [[ "${IS_USFULL_HOST}" == "1" && -z "${dob// /}" ]]; then
    echo "POST /api/dl/ — пропуск (USFULL: укажите DOB в данных строки)"
  else
    dl_body=$(jq -n \
      --arg f "$fdl" --arg l "$ldl" --arg a "$street" --arg z "$zipdl" \
      --arg dob "${dob:-}" \
      '{first_name:$f, last_name:$l, address:$a, zipcode:$z} + (if ($dob|length)>0 then {dob:$dob} else {} end)')
    echo "POST /api/dl/"
    post_dl "${dl_body}" | jq .
  fi

  # CR
  if [[ -z "${ssn}" ]]; then
    echo "POST /api/cr/ — пропуск (нет SSN)"
  elif [[ "${IS_USFULL_HOST}" == "1" ]]; then
    if [[ -z "${dob// /}" ]]; then
      echo "POST /api/cr/ — пропуск (USFULL: нужен DOB + полный адрес; задайте в строке PEOPLE)"
    else
      cr_body=$(jq -n \
        --arg f "$fdl" --arg l "$ldl" --arg sa "$street" \
        --arg c "$city" --arg s "$st" --arg z "$zipdl" \
        --arg dob "$dob" --arg ssn "$ssn" \
        '{first_name:$f,last_name:$l,street_address:$sa,city:$c,state:$s,zip_code:$z,dob:$dob,ssn:$ssn}')
      echo "POST /api/cr/ (формат USFULL)"
      cr_resp=$(post_cr "${cr_body}")
      echo "${cr_resp}" | jq .
    fi
  else
    cr_body=$(jq -n --arg ssn "$ssn" '{ssn:$ssn, bureau:"any"}')
    echo "POST /api/cr/ (self-hosted)"
    cr_resp=$(post_cr "${cr_body}")
    echo "${cr_resp}" | jq .
    rid=$(echo "${cr_resp}" | jq -r '.results[0].id // empty')
    has_pdf=$(echo "${cr_resp}" | jq -r '.results[0].has_pdf // false')
    if [[ "${has_pdf}" == "true" && -n "${rid}" ]]; then
      echo "→ PDF: curl -sS -o cr_${slug}.pdf -H \"X-API-KEY: ***\" \"${BASE_URL}/api/cr/download/${rid}\""
    fi
  fi

  echo
done <<'PEOPLE'
# Заполните DOB в конце строки для вызовов USFULL (формат см. https://usfull.info/service/docs/)
kyle_linseman|Kyle|K|Linseman|Hampton|NH|03842|Kyle|Linseman|1070 Ocean Blvd|03842|
sean_piwowar|Sean|R|Piwowar|Fairfax|VA|22032|Sean|Piwowar|5552 Ann Peake Dr|22032|
thomas_dickson|Thomas|C|Dickson|Philadelphia|PA|19147|Thomas|Dickson|334 Earp St|19147|
stephen_rudolph|Stephen|Darwin|Rudolph|Philadelphia|PA|19147|Stephen|Rudolph|1224 S American St|19147|
PEOPLE

echo "Готово."
