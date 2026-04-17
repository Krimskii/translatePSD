parser_dxf.pyimport ezdxf
import pandas as pd

def parse_dxf(file):

    doc = ezdxf.readfile(file)
    msp = doc.modelspace()

    texts = []

    for e in msp:

        if e.dxftype() == "TEXT":
            texts.append({
                "text": e.dxf.text,
                "entity": e
            })

        elif e.dxftype() == "MTEXT":
            texts.append({
                "text": e.plain_text(),
                "entity": e
            })

    return doc, texts