import ezdxf

from dxf_utils import pick_output_text


def write_translated_dxf(input_path, output_path, df):
    doc = ezdxf.readfile(input_path)
    handle_map = {}

    for _, row in df.iterrows():
        handle = row.get("handle")
        if handle is None:
            continue
        handle_map[str(handle)] = pick_output_text(row)

    for entity in doc.entitydb.values():
        handle = str(entity.dxf.handle)
        if handle not in handle_map:
            continue

        new_text = handle_map[handle]

        try:
            if entity.dxftype() == "TEXT":
                entity.dxf.text = new_text
            elif entity.dxftype() == "MTEXT":
                entity.text = new_text
            elif entity.dxftype() == "ATTRIB":
                entity.dxf.text = new_text
        except AttributeError:
            continue

    doc.saveas(output_path)
