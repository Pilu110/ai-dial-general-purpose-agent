import json
from urllib import request, error

URL = "http://localhost:8080/openai/deployments/general-purpose-agent/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "api-key": "dial_api_key",
}

CASES = [
    ("smoke-cont-web", "Search what is the weather in Kyiv now and provide a short answer with source."),
    ("smoke-cont-image", "Generate picture with smiling cat."),
    ("smoke-cont-math", "What is the sin of 5682936329203?"),
]


def run_case(conv_id: str, prompt: str) -> None:
    payload = {"messages": [{"role": "user", "content": prompt}]}
    body = json.dumps(payload).encode("utf-8")

    headers = dict(HEADERS)
    headers["x-conversation-id"] = conv_id

    req = request.Request(URL, data=body, headers=headers, method="POST")

    print("=" * 80)
    print(f"PROMPT: {prompt}")
    try:
        with request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP: {resp.status}")
            data = json.loads(raw)
            message = data["choices"][0]["message"]
            content = message.get("content", "")
            print(f"CONTENT: {content[:260].replace(chr(10), ' ')}")

            history = (
                message.get("custom_content", {})
                .get("state", {})
                .get("tool_call_history", [])
            )
            tool_names = []
            for item in history:
                for tc in item.get("tool_calls", []) or []:
                    fn = tc.get("function", {}).get("name")
                    if fn:
                        tool_names.append(fn)
            print(f"TOOL_CALLS: {','.join(tool_names) if tool_names else '(none)'}")
    except error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP: {e.code}")
        print(f"ERROR: {err_body[:300]}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    for conv, prompt in CASES:
        run_case(conv, prompt)

