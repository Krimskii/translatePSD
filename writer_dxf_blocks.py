import logging

import ezdxf

from dxf_utils import pick_output_text
from parser_dxf_block import clean_mtext


LOGGER = logging.getLogger(__name__)


def _set_entity_text(entity, new_text):
    entity_type = entity.dxftype()

    if entity_type in {"TEXT", "ATTRIB", "ATTDEF"}:
        entity.dxf.text = new_text
        return True
    if entity_type == "MTEXT":
        entity.text = new_text
        return True
    if entity_type == "DIMENSION":
        entity.dxf.text = new_text
        return True
    if entity_type in {"MULTILEADER", "MLEADER"}:
        if hasattr(entity, "text"):
            try:
                entity.text = new_text
                return True
            except Exception:
                pass
        if hasattr(entity, "context") and hasattr(entity.context, "mtext"):
            try:
                entity.context.mtext.default_content = clean_mtext(new_text)
                return True
            except Exception:
                pass
    return False


def write_translated_dxf(input_path, output_path, df):
    doc = ezdxf.readfile(input_path)
    handle_map = {}

    for _, row in df.iterrows():
        handle = row.get("handle")
        if handle is None:
            continue
        handle_map[str(handle)] = pick_output_text(row)

    updated = 0
    for entity in doc.entitydb.values():
        handle = str(getattr(entity.dxf, "handle", ""))
        if handle not in handle_map:
            continue

        try:
            if _set_entity_text(entity, handle_map[handle]):
                updated += 1
        except Exception as exc:
            LOGGER.warning("Failed to update DXF entity %s: %s", handle, exc)

    LOGGER.info("DXF writer updated %s entities", updated)
    doc.saveas(output_path)
