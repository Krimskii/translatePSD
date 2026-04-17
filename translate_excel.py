import pandas as pd

from dxf_utils import pick_output_text
from translator_hybrid import translate_df


def _read_workbook(source):
    sheets = pd.read_excel(source, sheet_name=None, header=None, dtype=object)
    normalized = {}

    for sheet_name, sheet in sheets.items():
        normalized[sheet_name] = sheet.where(sheet.notna(), "")

    return normalized


def workbook_to_translation_df(source):
    sheets = _read_workbook(source)
    rows = []

    for sheet_name, sheet in sheets.items():
        for row_idx in range(sheet.shape[0]):
            for col_idx in range(sheet.shape[1]):
                value = sheet.iat[row_idx, col_idx]
                text = str(value).strip()
                if not text or text.lower() == "nan":
                    continue

                rows.append(
                    {
                        "sheet": sheet_name,
                        "row": row_idx,
                        "col": col_idx,
                        "text": text,
                    }
                )

    return pd.DataFrame(rows)


def apply_excel_dataframe(src, dst, df):
    sheets = _read_workbook(src)
    handle_map = {}

    for _, row in df.iterrows():
        handle = (str(row.get("sheet")), int(row.get("row")), int(row.get("col")))
        handle_map[handle] = pick_output_text(row)

    for sheet_name, sheet in sheets.items():
        for row_idx in range(sheet.shape[0]):
            for col_idx in range(sheet.shape[1]):
                handle = (sheet_name, row_idx, col_idx)
                if handle in handle_map:
                    sheet.iat[row_idx, col_idx] = handle_map[handle]

    with pd.ExcelWriter(dst, engine="openpyxl") as writer:
        for sheet_name, sheet in sheets.items():
            sheet.to_excel(writer, sheet_name=sheet_name[:31], index=False, header=False)


def translate_excel(src, dst):
    df = workbook_to_translation_df(src)
    df = translate_df(df)
    apply_excel_dataframe(src, dst, df)
