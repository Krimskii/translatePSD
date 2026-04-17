import pandas as pd
from docx import Document

from dxf_utils import pick_output_text
from parser_docx import iter_docx_text_containers
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
    return [fix_spaced_text(container.text) for container in iter_docx_text_containers(doc)]


def _replace_in_primary_run(runs, visible_indices, text):
    primary_idx = visible_indices[0]
    runs[primary_idx].text = text

    for idx in visible_indices[1:]:
        runs[idx].text = ""


def _apply_to_runs(paragraph, text):
    runs = paragraph.runs
    text = cleanup_translation(text)

    if not runs:
        paragraph.text = text
        return

    run_texts = [run.text for run in runs]
    visible_indices = [i for i, value in enumerate(run_texts) if value]

    if not visible_indices:
        runs[0].text = text
        return

    total_len = sum(len(run_texts[i]) for i in visible_indices)
    if total_len <= 0:
        _replace_in_primary_run(runs, visible_indices, text)
        return

    fragmented_layout = len(visible_indices) >= 4 and total_len / max(len(visible_indices), 1) <= 3
    expanded_translation = len(text) >= int(total_len * 1.25)
    dense_table_text = " " in text and len(text.split()) >= 3 and len(visible_indices) >= 3

    if fragmented_layout or expanded_translation or dense_table_text:
        _replace_in_primary_run(runs, visible_indices, text)
        return

    remaining = text
    consumed = 0

    for pos, idx in enumerate(visible_indices):
        original_len = len(run_texts[idx])

        if pos == len(visible_indices) - 1:
            piece = remaining
        else:
            share = round(len(text) * (original_len / total_len))
            share = max(share, 0)
            next_consumed = min(consumed + share, len(text))
            piece = text[consumed:next_consumed]
            consumed = next_consumed
            remaining = text[consumed:]

        runs[idx].text = piece

    for idx, run in enumerate(runs):
        if idx not in visible_indices:
            continue
        if idx != visible_indices[-1]:
            continue
        run.text += remaining if run.text != remaining else ""
        remaining = ""


def apply(doc, translated):
    for container, text in zip(iter_docx_text_containers(doc), translated):
        _apply_to_runs(container, text)


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
