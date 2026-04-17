import fitz
import pandas as pd

from pdf_utils import extract_pdf_blocks, fit_textbox
from translator_hybrid import translate_df


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
        for block, translated in zip(blocks, translations):
            page = doc[block.page_index]
            rect = fitz.Rect(block.bbox)
            text = str(translated).strip()

            if not text:
                continue

            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            fontsize = fit_textbox(page, rect, text)
            inserted = page.insert_textbox(
                rect,
                text,
                fontname="helv",
                fontsize=fontsize,
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
            )

            if inserted < 0:
                page.insert_textbox(
                    rect,
                    text,
                    fontname="helv",
                    fontsize=max(fontsize - 1.5, 5),
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )

        doc.save(dst)
    finally:
        doc.close()

    return dst
