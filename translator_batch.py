import requests

MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"


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

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 256,
                    "top_p": 1,
                    "repeat_penalty": 1.1
                }
            },
            timeout=60
        )

        result = response.json()["response"]

        translations = [t.strip() for t in result.split("@@@")]

        fixed = []

        for i, t in enumerate(texts):

            if i < len(translations) and translations[i]:
                fixed.append(translations[i])
            else:
                fixed.append(t)

        return fixed

    except Exception as e:
        print("Ошибка:", e)
        return texts