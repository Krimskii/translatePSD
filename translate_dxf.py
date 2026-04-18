import logging
from pathlib import Path

import ezdxf
import pandas as pd

from parser_dxf_block import CHINESE_RE, extract_text_records
from translator_hybrid import translate_df
from writer_dxf_blocks import write_translated_dxf


LOGGER = logging.getLogger(__name__)


def _records_to_frame(records):
    return pd.DataFrame(
        [
            {
                "handle": record.handle,
                "entity_type": record.entity_type,
                "owner": record.owner,
                "layer": record.layer,
                "block_name": record.block_name,
                "layout_name": record.layout_name,
                "text": record.text,
                "raw_text": record.raw_text,
                "notes": record.notes,
            }
            for record in records
        ]
    )


def _build_qc_report(df, dst_path):
    report = df.copy()
    report["still_has_chinese"] = report["translated"].astype(str).str.contains(CHINESE_RE)
    report["source_has_chinese"] = report["text"].astype(str).str.contains(CHINESE_RE)
    report["needs_ocr"] = report["text"].astype(str).eq("")
    report_path = Path(dst_path).with_suffix(".report.xlsx")
    try:
        report.to_excel(report_path, index=False)
        LOGGER.info("DXF QC report written to %s", report_path)
    except Exception as exc:
        LOGGER.warning("Unable to write DXF QC report: %s", exc)


def translate_dxf(src, dst):
    LOGGER.info("Reading DXF %s", src)
    doc = ezdxf.readfile(src)
    records = extract_text_records(doc)
    LOGGER.info("DXF text records found: %s", len(records))

    if not records:
        doc.saveas(dst)
        return {"found": 0, "translated": 0, "untranslated": 0}

    frame = _records_to_frame(records)
    translated_df = translate_df(frame)
    write_translated_dxf(src, dst, translated_df)
    untranslated_count = int(translated_df["untranslated_chinese"].fillna(False).sum())
    _build_qc_report(translated_df, dst)

    summary = {
        "found": len(translated_df),
        "translated": int((translated_df["translated"].astype(str).str.strip() != "").sum()),
        "untranslated": untranslated_count,
    }
    LOGGER.info("DXF translation summary: %s", summary)
    return summary
