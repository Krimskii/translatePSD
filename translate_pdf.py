import logging
from pathlib import Path

import fitz
import pandas as pd

from dxf_utils import pick_output_text
from pdf_utils import build_pdf_qc_report, classify_pdf_mode, extract_pdf_blocks, fit_textbox
from translator_hybrid import translate_df


LOGGER = logging.getLogger(__name__)


def _safe_insert(page, rect, text, block):
    fontsize = fit_textbox(page, rect, text, preferred_size=block.font_size)
    inserted = page.insert_textbox(
        rect,
        str(text),
        fontname="helv",
        fontsize=fontsize,
        color=block.color,
        align=block.align,
    )

    if inserted < 0:
        page.insert_textbox(
            rect,
            str(text),
            fontname="helv",
            fontsize=max(fontsize - 1.5, 5),
            color=block.color,
            align=block.align,
        )


def apply_pdf_dataframe(src, dst, df):
    blocks = extract_pdf_blocks(src)
    doc = fitz.open(src)

    try:
        if not blocks:
            doc.save(dst)
            return dst

        translations = [pick_output_text(df.iloc[i]) for i in range(min(len(blocks), len(df)))]
        if len(translations) < len(blocks):
            translations.extend([block.text for block in blocks[len(translations) :]])

        insert_jobs = []
        for block, translated in zip(blocks, translations):
            text = str(translated).strip()
            if not text:
                continue
            rect = fitz.Rect(block.bbox)
            page = doc[block.page_index]
            page.add_redact_annot(rect, fill=(1, 1, 1))
            insert_jobs.append((block.page_index, rect, text, block))

        for page_index in sorted({job[0] for job in insert_jobs}):
            doc[page_index].apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        for page_index, rect, text, block in insert_jobs:
            _safe_insert(doc[page_index], rect, text, block)

        doc.save(dst)
    finally:
        doc.close()

    qc_report = build_pdf_qc_report(src, df)
    report_path = Path(dst).with_suffix(".ocr_report.xlsx")
    try:
        qc_report.to_excel(report_path, index=False)
        LOGGER.info("PDF OCR QC report written to %s", report_path)
    except Exception as exc:
        LOGGER.warning("Unable to write PDF OCR QC report: %s", exc)
    return dst


def translate_pdf(src, dst):
    mode_info = classify_pdf_mode(src)
    LOGGER.info("PDF mode: %s", mode_info["mode"])
    blocks = extract_pdf_blocks(src)
    df = pd.DataFrame({"text": [block.text for block in blocks], "pdf_source": [block.source for block in blocks]})
    if not df.empty:
        df = translate_df(df)
    return apply_pdf_dataframe(src, dst, df)
