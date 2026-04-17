import re

import ezdxf
import pandas as pd

from cad_dict_full import DICT
from translator_hybrid import translate_df


def extract_clean_text(raw):
    if raw is None:
        return ""

    raw = str(raw)
    match = re.search(r";(.*?)\}", raw)
    if match:
        return match.group(1)

    return raw


def inject_back(raw, translated):
    raw = str(raw)
    translated = str(translated)

    if "{" in raw and ";" in raw:
        return re.sub(r";(.*?)\}", f";{translated}}}", raw)

    return translated


def apply_dict(text):
    value = str(text)
    for key, replacement in DICT.items():
        value = value.replace(key, replacement)
    return value


def _read_entity_text(entity):
    entity_type = entity.dxftype()

    if entity_type == "TEXT":
        raw = entity.dxf.text
    elif entity_type == "MTEXT":
        raw = entity.text
    elif entity_type == "ATTRIB":
        raw = entity.dxf.text
    else:
        return None

    return entity_type, raw, extract_clean_text(raw)


def translate_dxf(src, dst):
    print("DXF:", src)

    doc = ezdxf.readfile(src)
    msp = doc.modelspace()
    rows = []

    for entity in msp:
        try:
            parsed = _read_entity_text(entity)
        except AttributeError:
            continue

        if parsed is None:
            continue

        entity_type, raw, clean = parsed
        rows.append((entity, entity_type, raw, clean))

    print("entities:", len(rows))

    if not rows:
        print("no text")
        doc.saveas(dst)
        return

    texts = [row[3][:200] for row in rows]
    df = pd.DataFrame({"text": texts})
    df = translate_df(df)
    translated = [apply_dict(text) for text in df["translated"].tolist()]

    for entity, entity_type, raw, _clean in rows:
        new_text = inject_back(raw, translated.pop(0))

        try:
            if entity_type in {"TEXT", "ATTRIB"}:
                entity.dxf.text = new_text
            elif entity_type == "MTEXT":
                entity.text = new_text
        except AttributeError:
            continue

    doc.saveas(dst)
    print("saved:", dst)
