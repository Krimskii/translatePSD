import io
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from normalizer import normalize_df
from output_names import build_ru_name
from parser_docx import parse_docx
from parser_pdf import parse_pdf
from translator_hybrid import translate_df
from translate_docx import apply_docx_dataframe
from translate_excel import apply_excel_dataframe, workbook_to_translation_df
from translate_pdf import apply_pdf_dataframe
from validator import validate_df
from writer_dxf_blocks import write_translated_dxf


def _dataframe_to_excel_bytes(df):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def _prepare_excel_dataframe(uploaded_file):
    return workbook_to_translation_df(uploaded_file)


def _prepare_document_dataframe(uploaded_file, suffix):
    if suffix == ".docx":
        return pd.DataFrame({"text": parse_docx(uploaded_file)})
    if suffix == ".pdf":
        return parse_pdf(uploaded_file)
    raise ValueError(f"Unsupported document suffix: {suffix}")


def _prepare_dxf_dataframe(source_path):
    import ezdxf
    from parser_dxf_block import extract_texts

    doc = ezdxf.readfile(source_path)
    texts = extract_texts(doc)
    return pd.DataFrame(texts, columns=["handle", "text"])


def _save_dxf_output(source_path, df):
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
    output.close()
    write_translated_dxf(source_path, output.name, df)
    return Path(output.name).read_bytes()


def _save_docx_output(uploaded_file, df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as source_tmp:
        source_tmp.write(uploaded_file.getvalue())
        source_path = source_tmp.name

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    output.close()
    apply_docx_dataframe(source_path, output.name, df)
    return Path(output.name).read_bytes()


def _save_excel_output(uploaded_file, df):
    source_suffix = Path(uploaded_file.name).suffix.lower() or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=source_suffix) as source_tmp:
        source_tmp.write(uploaded_file.getvalue())
        source_path = source_tmp.name

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    output.close()
    apply_excel_dataframe(source_path, output.name, df)
    return Path(output.name).read_bytes()


def _save_pdf_output(uploaded_file, df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as source_tmp:
        source_tmp.write(uploaded_file.getvalue())
        source_path = source_tmp.name

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    output.close()
    apply_pdf_dataframe(source_path, output.name, df)
    return Path(output.name).read_bytes()


def process_uploaded_file(uploaded_file, *, normalize=True, validate=True):
    original_name = uploaded_file.name
    suffix = Path(original_name).suffix.lower()

    try:
        if suffix in {".xlsx", ".xls"}:
            df = _prepare_excel_dataframe(uploaded_file)
            output_ext = ".xlsx"
        elif suffix in {".docx", ".pdf"}:
            df = _prepare_document_dataframe(uploaded_file, suffix)
            output_ext = suffix
        elif suffix == ".dxf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded_file.getvalue())
                source_tmp_path = tmp.name

            df = _prepare_dxf_dataframe(source_tmp_path)
            output_ext = ".dxf"
        else:
            raise ValueError(f"Неподдерживаемый формат: {suffix or original_name}")

        row_count = len(df)
        translated_df = translate_df(df.copy())

        if normalize:
            translated_df = normalize_df(translated_df.copy())

        report = validate_df(translated_df.copy()) if validate else pd.DataFrame()
        warn_count = 0 if report.empty else int((report["status"] != "OK").sum())

        if output_ext == ".xlsx":
            output_bytes = _save_excel_output(uploaded_file, translated_df)
        elif output_ext == ".docx":
            output_bytes = _save_docx_output(uploaded_file, translated_df)
        elif output_ext == ".pdf":
            output_bytes = _save_pdf_output(uploaded_file, translated_df)
        else:
            output_bytes = _save_dxf_output(source_tmp_path, translated_df)

        output_name = build_ru_name(original_name, output_ext=output_ext)
        return {
            "file_name": original_name,
            "output_name": output_name,
            "status": "OK" if warn_count == 0 else "WARN",
            "rows": row_count,
            "warnings": warn_count,
            "issues": "" if report.empty else "; ".join(report.loc[report["status"] != "OK", "issues"].head(5).tolist()),
            "bytes": output_bytes,
            "report": report,
        }
    except Exception as exc:
        return {
            "file_name": original_name,
            "output_name": build_ru_name(original_name),
            "status": "ERROR",
            "rows": 0,
            "warnings": 0,
            "issues": str(exc),
            "bytes": None,
            "report": pd.DataFrame(),
        }


def build_batch_zip(results):
    archive = io.BytesIO()

    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        summary_rows = []

        for result in results:
            summary_rows.append(
                {
                    "file_name": result["file_name"],
                    "output_name": result["output_name"],
                    "status": result["status"],
                    "rows": result["rows"],
                    "warnings": result["warnings"],
                    "issues": result["issues"],
                }
            )

            if result["bytes"] is not None:
                zf.writestr(result["output_name"], result["bytes"])

            if not result["report"].empty:
                report_bytes = _dataframe_to_excel_bytes(result["report"])
                report_name = build_ru_name(result["file_name"], output_ext=".report.xlsx")
                zf.writestr(report_name, report_bytes)

        summary_df = pd.DataFrame(summary_rows)
        zf.writestr("batch_report.csv", summary_df.to_csv(index=False).encode("utf-8-sig"))
        zf.writestr("batch_report.xlsx", _dataframe_to_excel_bytes(summary_df))

    archive.seek(0)
    return archive.getvalue()
