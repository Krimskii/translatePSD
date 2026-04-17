import pandas as pd
from docx import Document

from dxf_utils import pick_output_text
from post_translate_fix import cleanup_translation, has_chinese
from translator_hybrid import translate_df


DOCX_FALLBACK_DICT = {
    "设备": "оборудование",
    "布置": "расстановка",
    "工艺": "технология",
    "流程": "схема",
    "车间": "цех",
    "铝材": "алюминиевый профиль",
    "说明": "описание",
    "结构": "конструкции",
    "总平面": "генеральный план",
    "目录": "содержание",
    "电气": "электрика",
    "给排水": "водоснабжение и канализация",
}


def fallback(text):
    value = str(text)
    for source, target in DOCX_FALLBACK_DICT.items():
        value = value.replace(source, target)
    return cleanup_translation(value)


def fix_spaced_text(text):
    value = str(text)
    parts = value.split(" ")

    if len(parts) > 8:
        short = [p for p in parts if len(p) <= 2]
        if len(short) > len(parts) * 0.6:
            return "".join(parts)

    return value


def collect(doc):
    texts = []

    for paragraph in doc.paragraphs:
        texts.append(fix_spaced_text(paragraph.text))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.append(fix_spaced_text(cell.text))

    return texts


def apply(doc, translated):
    index = 0

    for paragraph in doc.paragraphs:
        if index < len(translated):
            paragraph.text = translated[index]
        index += 1

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if index < len(translated):
                    cell.text = translated[index]
                index += 1


def apply_docx_dataframe(src, dst, df):
    doc = Document(src)
    translated = [pick_output_text(df.iloc[i]) for i in range(len(df))]
    apply(doc, translated)
    doc.save(dst)


def translate_docx(src, dst):
    print("translate:", src)

    doc = Document(src)
    texts = collect(doc)
    df = pd.DataFrame({"text": texts})
    df = translate_df(df)

    fixed = []
    for text in df["translated"].tolist():
        value = cleanup_translation(text)

        if has_chinese(value):
            value = fallback(value)

        fixed.append(value)

    apply(doc, fixed)
    doc.save(dst)

    print("saved:", dst)
