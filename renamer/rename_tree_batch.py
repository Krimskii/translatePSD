import os
import requests
import re

MODEL = "qwen2.5:7b"


def has_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text)


DICT = {
"设备布置图":"План расстановки оборудования",
"工艺流程图":"Технологическая схема",
"车间":"Цех",
"铝材":"Алюминиевый профиль",
"目录":"Содержание",
"总平面":"Генеральный план",
"电气":"Электрика",
"给排水":"ВК"
}


def rule_translate(text):

    t = text

    for k,v in DICT.items():
        t = t.replace(k, v)

    return t


def clean_filename(name):

    # убрать объяснения LLM
    name = name.split("\n")[0]
    name = name.split("which")[0]
    name = name.split("Translate")[0]

    # убрать запрещенные символы
    name = re.sub(r'[\\/:*?"<>|]', '', name)

    # убрать двойные пробелы
    name = re.sub(r'\s+', ' ', name)

    return name.strip()


def translate_one(text):

    if not has_chinese(text):
        return text

    try:

        prompt = f"""
Translate Chinese file name to Russian.
Return ONLY translated file name.
No explanation.

{text}
"""

        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 40
                }
            },
            timeout=60
        )

        out = r.json()["response"].strip()

        # если модель начала объяснять
        if len(out) > 80:
            out = rule_translate(text)

        # если китайский остался
        if has_chinese(out):
            out = rule_translate(text)

        return clean_filename(out)

    except Exception:
        return clean_filename(rule_translate(text))


def translate_tree(root):

    items = []

    for path, dirs, files in os.walk(root):
        for d in dirs:
            items.append(("dir", path, d))
        for f in files:
            items.append(("file", path, f))

    print("Найдено:", len(items))
    print()

    renamed = 0

    for i, item in enumerate(items):

        typ, path, name = item

        print(f"{i+1}/{len(items)}")
        print("OLD:", name)

        new_name = translate_one(name)

        print("NEW:", new_name)

        old = os.path.join(path, name)
        new = os.path.join(path, new_name)

        if old == new:
            print("skip\n")
            continue

        try:
            os.rename(old, new)
            print("RENAMED\n")
            renamed += 1
        except Exception as e:
            print("ERROR:", e, "\n")

    print("Готово")
    print("Переименовано:", renamed)
