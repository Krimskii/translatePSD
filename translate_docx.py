from docx import Document
import pandas as pd
import re

from translator_hybrid import translate_df


# словарь ПСД fallback
DICT = {
    "设备":"оборудование",
    "布置":"расстановка",
    "工艺":"технология",
    "流程":"схема",
    "车间":"цех",
    "铝材":"алюминиевый профиль",
    "说明":"описание",
    "结构":"конструкции",
    "总平面":"генеральный план",
    "目录":"содержание",
    "电气":"электрика",
    "给排水":"водоснабжение и канализация"
}


def has_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', str(text))


def fallback(text):

    t = str(text)

    for k,v in DICT.items():
        t = t.replace(k,v)

    return t


def fix_spaced_text(text):

    t = str(text)

    parts = t.split(" ")

    if len(parts) > 8:
        short = [p for p in parts if len(p) <= 2]

        if len(short) > len(parts) * 0.6:
            return "".join(parts)

    return t


def collect(doc):

    texts = []

    for p in doc.paragraphs:
        texts.append(fix_spaced_text(p.text))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.append(fix_spaced_text(cell.text))

    return texts


def apply(doc, translated):

    i = 0

    for p in doc.paragraphs:

        if i < len(translated):
            p.text = translated[i]

        i += 1

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:

                if i < len(translated):
                    cell.text = translated[i]

                i += 1


def translate_docx(src, dst):

    print("translate:", src)

    doc = Document(src)

    texts = collect(doc)

    df = pd.DataFrame({"text": texts})

    # первый проход
    df = translate_df(df)

    translated = df["translated"].tolist()

    # второй проход — добить китайский
    fixed = []

    for i,t in enumerate(translated):

        if has_chinese(t):

            t = fallback(t)

            # если всё еще китайский — ещё раз через модель
            if has_chinese(t):

                df2 = pd.DataFrame({"text":[t]})
                df2 = translate_df(df2)

                t = df2["translated"][0]

        fixed.append(t)

    apply(doc, fixed)

    doc.save(dst)

    print("saved:", dst)