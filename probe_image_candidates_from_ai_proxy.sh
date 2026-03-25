#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

key="$(grep '^DIAL_API_KEY=' ./.env | head -n1 | cut -d'=' -f2- | tr -d '\r')"
if [[ -z "$key" ]]; then
  echo "DIAL_API_KEY is missing in .env" >&2
  exit 1
fi

candidates=(
  "gpt-image-1-mini-2025-10-06"
  "gpt-image-1.5-2025-12-16"
  "gemini-2.5-flash-image"
  "gemini-3-pro-image-preview"
  "gemini-3.1-flash-image-preview"
  "stability.stable-image-core-v1:1"
)

for dep in "${candidates[@]}"; do
  echo "DEP:$dep"
  tmp_body="$(mktemp)"
  http_code="$(curl -sS --max-time 50 -o "$tmp_body" -w '%{http_code}' -X POST "https://ai-proxy.lab.epam.com/openai/deployments/$dep/chat/completions" \
    -H "Content-Type: application/json" \
    -H "api-key: $key" \
    -d '{"messages":[{"role":"user","content":"Generate a smiling cat"}]}' || true)"
  head -c 320 "$tmp_body"
  echo
  echo "HTTP:$http_code"
  rm -f "$tmp_body"
  echo
  echo "---"
done

