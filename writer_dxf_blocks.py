import logging
import re

import ezdxf

from dxf_utils import pick_output_text
from parser_dxf_block import clean_mtext


LOGGER = logging.getLogger(__name__)
RU_TEXT_STYLE = "RU_TRANSLATION"
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
MEANINGFUL_RE = re.compile(r"[А-Яа-яЁёA-Za-z\u4e00-\u9fff]")
PUNCT_ONLY_RE = re.compile(r"^[\s\d,.;:()/%×\-–—_+\\[\]{}<>|]+$")


def _ensure_ru_text_style(doc):
    if RU_TEXT_STYLE not in doc.styles:
        style = doc.styles.new(RU_TEXT_STYLE)
    else:
        style = doc.styles.get(RU_TEXT_STYLE)

    # TrueType font is critical: many Chinese SHX/BigFont styles do not render Cyrillic.
    try:
        style.dxf.font = "arial.ttf"
    except Exception:
        pass
    try:
        style.dxf.bigfont = ""
    except Exception:
        pass
    return RU_TEXT_STYLE


def _apply_ru_style(entity, style_name):
    if not style_name:
        return
    if not hasattr(entity, "dxf"):
        return
    if not hasattr(entity.dxf, "style"):
        return
    try:
        entity.dxf.style = style_name
    except Exception:
        pass


def _safe_output_text(new_text, original_text):
    candidate = str(new_text or "").strip()
    original = str(original_text or "").strip()

    if not candidate:
        return original
    if PUNCT_ONLY_RE.match(candidate) and MEANINGFUL_RE.search(original):
        return original
    if CHINESE_RE.search(candidate) and not CHINESE_RE.search(original):
        return original
    return candidate


def _set_entity_text(entity, new_text, *, style_name=""):
    entity_type = entity.dxftype()
    if CYRILLIC_RE.search(str(new_text)):
        _apply_ru_style(entity, style_name)

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
    ru_style = _ensure_ru_text_style(doc)
    handle_map = {}

    for _, row in df.iterrows():
        handle = row.get("handle")
        if handle is None:
            continue
        handle_map[str(handle)] = {
            "output": pick_output_text(row),
            "original": str(row.get("raw_text", row.get("text", "")) or ""),
        }

    updated = 0
    skipped = 0
    for entity in doc.entitydb.values():
        handle = str(getattr(entity.dxf, "handle", ""))
        if handle not in handle_map:
            continue

        try:
            payload = handle_map[handle]
            output_text = _safe_output_text(payload["output"], payload["original"])
            if not output_text:
                skipped += 1
                continue
            if _set_entity_text(entity, output_text, style_name=ru_style):
                updated += 1
        except Exception as exc:
            LOGGER.warning("Failed to update DXF entity %s: %s", handle, exc)

    LOGGER.info("DXF writer updated %s entities, skipped %s empty outputs", updated, skipped)
    doc.saveas(output_path)
