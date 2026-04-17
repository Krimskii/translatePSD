import pandas as pd

def validate_df(df):
    report = []

    for i, row in df.iterrows():
        text = str(row.get("normalized", row.get("translated", "")))
        report.append({
            "text": text,
            "status": "OK"
        })

    return pd.DataFrame(report)
