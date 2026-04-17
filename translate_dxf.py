import ezdxf
import pandas as pd
import re

from translator_hybrid import translate_df
from cad_dict_full import DICT

def extract_clean_text(raw):

    if raw is None:
        return ""

    raw = str(raw)

    match = re.search(r';(.*?)\}', raw)

    if match:
        return match.group(1)

    return raw


def inject_back(raw, translated):

    if "{" in raw and ";" in raw:
        return re.sub(r';(.*?)\}', f';{translated}}}', raw)

    return translated


def apply_dict(text):

    t = str(text)

    for k, v in DICT.items():
        t = t.replace(k, v)

    return t

def translate_dxf(src, dst):

    print("DXF:", src)

    doc = ezdxf.readfile(src)
    msp = doc.modelspace()

    rows = []

    for e in msp:

        try:

            if e.dxftype() == "TEXT":

                raw = e.dxf.text
                clean = extract_clean_text(raw)

                rows.append((e, "TEXT", raw, clean))

            elif e.dxftype() == "MTEXT":

                raw = e.text
                clean = extract_clean_text(raw)

                rows.append((e, "MTEXT", raw, clean))

        except:
            pass

    print("entities:", len(rows))

    if not rows:
        print("no text")
        doc.saveas(dst)
        return

    texts = [r[3][:200] for r in rows]

    df = pd.DataFrame({"text": texts})

    df = translate_df(df)

    translated = df["translated"].tolist()

    for i, (entity, typ, raw, clean) in enumerate(rows):

        t = translated[i]

        new_text = inject_back(raw, t)

        try:

            if typ == "TEXT":
                entity.dxf.text = new_text
            else:
                entity.text = new_text

        except:
            pass

    doc.saveas(dst)

    print("saved:", dst)

    t = apply_dict(t)