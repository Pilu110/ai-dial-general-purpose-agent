#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Read DIAL_API_KEY from .env, tolerating CRLF line endings.
DIAL_API_KEY="$(grep '^DIAL_API_KEY=' ./.env | head -n1 | cut -d'=' -f2- | tr -d '\r')"
if [[ -z "$DIAL_API_KEY" ]]; then
  echo "DIAL_API_KEY is missing in .env" >&2
  exit 1
fi

candidates=(
  "dall-e-3"
  "gpt-image-1"
  "openai.dall-e-3"
  "openai.gpt-image-1"
  "dalle-3"
  "imagegen"
)

for dep in "${candidates[@]}"; do
  echo "DEP:$dep"
  tmp_body="$(mktemp)"
  http_code="$(curl -sS --max-time 40 -o "$tmp_body" -w '%{http_code}' -X POST "https://ai-proxy.lab.epam.com/openai/deployments/$dep/chat/completions" \
    -H "Content-Type: application/json" \
    -H "api-key: $DIAL_API_KEY" \
    -d '{"messages":[{"role":"user","content":"Generate smiling cat"}]}' || true)"
  head -c 240 "$tmp_body"
  echo
  echo "HTTP:$http_code"
  rm -f "$tmp_body"
  echo
  echo "---"
done

