import os
import requests

MODEL = "qwen2.5:7b"


def translate(text):

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": f"Translate Chinese folder/file name to Russian:\n{text}",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 60
            }
        }
    )

    return r.json()["response"].strip()


def clean(name):

    bad = r'\/:*?"<>|'

    for c in bad:
        name = name.replace(c, "_")

    return name.strip()


def translate_tree(root):

    # сначала файлы
    for path, dirs, files in os.walk(root, topdown=False):

        # файлы
        for f in files:

            old = os.path.join(path, f)

            name, ext = os.path.splitext(f)

            new_name = clean(translate(name)) + ext

            new = os.path.join(path, new_name)

            try:
                os.rename(old, new)
                print("FILE:", f, "->", new_name)
            except OSError as e:
                print("FILE ERROR:", f, e)

        # папки
        for d in dirs:

            old = os.path.join(path, d)

            new_name = clean(translate(d))

            new = os.path.join(path, new_name)

            try:
                os.rename(old, new)
                print("DIR:", d, "->", new_name)
            except OSError as e:
                print("DIR ERROR:", d, e)
