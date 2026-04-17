import pandas as pd

from apply_cad_dict import apply_cad_dict
from post_translate_fix import cleanup_translation, has_chinese
from translator_batch import ollama_batch
from translator_deepseek import deepseek_available, deepseek_translate


def _translate_one(source_text, model_text):
    source_text = str(source_text)
    candidate = cleanup_translation(model_text)

    if not candidate:
        candidate = source_text

    if not has_chinese(candidate):
        return candidate

    dict_fallback = cleanup_translation(apply_cad_dict(source_text))
    if dict_fallback != source_text and not has_chinese(dict_fallback):
        return dict_fallback

    if deepseek_available():
        try:
            deepseek_text = cleanup_translation(deepseek_translate(source_text))
            if deepseek_text:
                return deepseek_text
        except Exception as e:
            print("deepseek error:", e)

    if dict_fallback != source_text:
        return dict_fallback

    return candidate


def translate_df(df):
    texts = df["text"].astype(str).tolist()
    texts = [t[:200] for t in texts]

    batch_size = 20
    translated = []
    total = len(texts)

    for i in range(0, total, batch_size):
        print(f"batch {i} / {total}")

        batch = texts[i : i + batch_size]

        try:
            result = ollama_batch(batch)
        except Exception as e:
            print("ollama error:", e)
            result = batch

        if len(result) != len(batch):
            result = batch

        fixed = []
        for source_text, model_text in zip(batch, result):
            fixed.append(_translate_one(source_text, model_text))

        translated.extend(fixed)

    if len(translated) != len(df):
        translated = translated[: len(df)]

        while len(translated) < len(df):
            translated.append(df["text"].iloc[len(translated)])

    df["translated"] = translated
    return df
