import pandas as pd
from translator_hybrid import translate_df


def translate_excel(src, dst):

    df = pd.read_excel(src)

    df = df.astype(str)

    df["text"] = df.apply(lambda r: " ".join(r.values), axis=1)

    df = translate_df(df)

    df.to_excel(dst, index=False)