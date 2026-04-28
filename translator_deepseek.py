import os

import requests


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "90"))


def deepseek_available():
    return bool(DEEPSEEK_API_KEY)


def deepseek_chat(messages, *, temperature=0, timeout=None, max_tokens=None):
    if not deepseek_available():
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": temperature,
        "messages": messages,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    response = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout or DEEPSEEK_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["choices"][0]["message"]["content"]).strip()


def deepseek_translate(text):
    if not deepseek_available():
        return str(text)

    return deepseek_chat(
        [
            {
                "role": "system",
                "content": (
                    "Translate Chinese construction and CAD text into Russian. "
                    "Return only the translated text. Keep dimensions, abbreviations, "
                    "marks, and engineering notation unchanged."
                ),
            },
            {"role": "user", "content": str(text)},
        ],
        timeout=60,
    )
