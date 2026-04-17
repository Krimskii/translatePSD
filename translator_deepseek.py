import os

import requests


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def deepseek_available():
    return bool(DEEPSEEK_API_KEY)


def deepseek_translate(text):
    if not deepseek_available():
        return str(text)

    response = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "temperature": 0,
            "messages": [
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
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["choices"][0]["message"]["content"]).strip()
