import pandas as pd

from translator_batch import ollama_batch
from apply_cad_dict import apply_cad_dict
from post_translate_fix import fix_chinese


def translate_df(df):

    texts = df["text"].astype(str).tolist()

    # 🔥 ограничение длины (очень важно)
    texts = [t[:200] for t in texts]

    batch_size = 20
    translated = []

    total = len(texts)

    for i in range(0, total, batch_size):

        print(f"batch {i} / {total}")

        batch = texts[i:i+batch_size]

        try:
            result = ollama_batch(batch)
        except Exception as e:
            print("ollama error:", e)
            result = batch

        # FIX длины
        if len(result) != len(batch):
            result = batch

        # постобработка
        fixed = []

        for j, t in enumerate(result):

            t = apply_cad_dict(t)

            # если остался китайский → добиваем
            if fix_chinese(t):
                t = apply_cad_dict(batch[j])

            fixed.append(t)

        translated.extend(fixed)

    # финальная защита
    if len(translated) != len(df):

        translated = translated[:len(df)]

        while len(translated) < len(df):
            translated.append(df["text"].iloc[len(translated)])

    df["translated"] = translated

    return df