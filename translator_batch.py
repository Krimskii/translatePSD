import os

import requests


MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "240"))


def _generate(prompt, *, num_predict=256):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": num_predict,
                "top_p": 1,
                "repeat_penalty": 1.1,
            },
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response", ""))


def ollama_batch(texts):
    if not texts:
        return []

    joined = "\n@@@\n".join(texts)

    prompt = f"""
Translate Chinese construction / CAD terms to Russian.

Rules:
- translate technical meaning
- keep abbreviations
- no explanations
- same number of lines
- separator @@@

{joined}
"""

    try:
        result = _generate(prompt, num_predict=512)
        translations = [t.strip() for t in result.split("@@@")]
        fixed = []

        for i, text in enumerate(texts):
            if i < len(translations) and translations[i]:
                fixed.append(translations[i])
            else:
                fixed.append(text)

        return fixed

    except Exception as e:
        print("Ошибка Ollama:", e)
        return texts


def ollama_translate_one(text):
    source_text = str(text)
    prompt = f"""
Translate the following Chinese engineering text into Russian.

Rules:
- keep paragraph structure when possible
- keep numbers, units, abbreviations and section numbering
- translate all Chinese text fully
- do not add comments
- return only the translated Russian text

Text:
{source_text}
"""

    try:
        return _generate(prompt, num_predict=1024).strip()
    except Exception as e:
        print("Ошибка Ollama single:", e)
        return source_text
