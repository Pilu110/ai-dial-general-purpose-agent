#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

key="$(grep '^DIAL_API_KEY=' ./.env | head -n1 | cut -d'=' -f2- | tr -d '\r')"
if [[ -z "$key" ]]; then
  echo "DIAL_API_KEY is missing in .env" >&2
  exit 1
fi

tmp_json="$(mktemp)"
curl -sS --max-time 60 -H "api-key: $key" "https://ai-proxy.lab.epam.com/openai/models" > "$tmp_json"
export TMP_JSON_PATH="$tmp_json"
python3 - <<'PY'
import json
import os

tmp_json = os.environ['TMP_JSON_PATH']
with open(tmp_json, 'r', encoding='utf-8') as f:
    data=json.load(f)
models=data.get('data',[])
print('TOTAL',len(models))
for m in models:
    mid=(m.get('id') or '').lower()
    d=(m.get('display_name') or '').lower()
    k=(m.get('description_keywords') or [])
    kw=' '.join(k).lower() if isinstance(k,list) else str(k).lower()
    if any(x in mid for x in ['dall','image','vision']) or any(x in d for x in ['dall','image']) or 'image generation' in kw:
        print(m.get('id'))
PY
rm -f "$tmp_json"

