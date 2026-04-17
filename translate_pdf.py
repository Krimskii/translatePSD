import fitz
import pandas as pd

from pdf_utils import extract_pdf_blocks, fit_textbox
from translator_hybrid import translate_df


def _safe_insert(page, rect, text, block):
    fontsize = fit_textbox(page, rect, text, preferred_size=block.font_size)
    inserted = page.insert_textbox(
        rect,
        text,
        fontname="helv",
        fontsize=fontsize,
        color=block.color,
        align=block.align,
    )

    if inserted < 0:
        page.insert_textbox(
            rect,
            text,
            fontname="helv",
            fontsize=max(fontsize - 1.5, 5),
            color=block.color,
            align=block.align,
        )


def translate_pdf(src, dst):
    blocks = extract_pdf_blocks(src)
    if not blocks:
        doc = fitz.open(src)
        try:
            doc.save(dst)
        finally:
            doc.close()
        return dst

    df = pd.DataFrame({"text": [block.text for block in blocks]})
    df = translate_df(df)
    translations = df["translated"].tolist()

    doc = fitz.open(src)

    try:
        insert_jobs = []
        for block, translated in zip(blocks, translations):
            page = doc[block.page_index]
            rect = fitz.Rect(block.bbox)
            text = str(translated).strip()

            if not text:
                continue

            page.add_redact_annot(rect, fill=(1, 1, 1))
            insert_jobs.append((block.page_index, rect, text, block))

        for page_index in sorted({job[0] for job in insert_jobs}):
            doc[page_index].apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        for page_index, rect, text, block in insert_jobs:
            page = doc[page_index]
            _safe_insert(page, rect, text, block)

        doc.save(dst)
    finally:
        doc.close()

    return dst
