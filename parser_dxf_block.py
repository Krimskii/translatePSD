import re


def clean_mtext(text):

    t = str(text)

    # удалить формат AutoCAD
    t = re.sub(r'{\\.*?;', '', t)

    # убрать закрывающую }
    t = t.replace('}', '')

    # перенос строки MTEXT
    t = t.replace('\\P', ' ')

    return t.strip()


def extract_texts(doc):

    texts = []

    msp = doc.modelspace()

    for e in msp:

        if e.dxftype() == "TEXT":

            texts.append(
                (e.dxf.handle, e.dxf.text)
            )

        elif e.dxftype() == "MTEXT":

            cleaned = clean_mtext(e.text)

            texts.append(
                (e.dxf.handle, cleaned)
            )

        elif e.dxftype() == "ATTRIB":

            texts.append(
                (e.dxf.handle, str(e.dxf.text).strip())
            )

    return texts
