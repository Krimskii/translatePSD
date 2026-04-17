def pick_output_text(row):
    for key in ("normalized", "translated", "text"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""
