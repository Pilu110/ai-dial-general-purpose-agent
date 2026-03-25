#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

key="$(grep '^DIAL_API_KEY=' ./.env | head -n1 | cut -d'=' -f2- | tr -d '\r')"
if [[ -z "$key" ]]; then
  echo "DIAL_API_KEY is missing in .env" >&2
  exit 1
fi

tmp_body="$(mktemp)"
http_code="$(curl -sS --max-time 40 -o "$tmp_body" -w '%{http_code}' -H "api-key: $key" "https://ai-proxy.lab.epam.com/openai/models" || true)"
head -c 2000 "$tmp_body"
echo
echo "HTTP:$http_code"
rm -f "$tmp_body"

