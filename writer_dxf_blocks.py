import ezdxf


def write_translated_dxf(input_path, output_path, df):

    doc = ezdxf.readfile(input_path)

    handle_map = {}

    # строим карту handle → текст
    for i, row in df.iterrows():

        if "handle" in df.columns:
            handle = row["handle"]
        else:
            continue

        text = row.get("normalized") or row.get("translated") or row.get("text")

        handle_map[str(handle)] = str(text)

    # обход всех объектов
    for e in doc.entitydb.values():

        h = str(e.dxf.handle)

        if h not in handle_map:
            continue

        new_text = handle_map[h]

        try:

            if e.dxftype() == "TEXT":
                e.dxf.text = new_text

            elif e.dxftype() == "MTEXT":
                e.text = new_text

            elif e.dxftype() == "ATTRIB":
                e.dxf.text = new_text

        except:
            pass

    doc.saveas(output_path)