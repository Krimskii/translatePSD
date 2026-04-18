import logging
import re
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)
MTEXT_INLINE_RE = re.compile(r"\{\\.*?;")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class DxfTextRecord:
    handle: str
    entity_type: str
    owner: str
    text: str
    raw_text: str
    layer: str
    block_name: str = ""
    layout_name: str = ""
    notes: str = ""


def clean_mtext(text):
    value = str(text or "")
    value = MTEXT_INLINE_RE.sub("", value)
    value = value.replace("}", "")
    value = value.replace("\\P", " ")
    value = value.replace("\\~", " ")
    value = re.sub(r"\\[A-Za-z0-9]+;?", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _safe_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _dimension_text(entity):
    override = _safe_text(getattr(entity.dxf, "text", ""))
    if override and override != "<>":
        return override
    return ""


def _multileader_text(entity):
    candidates = []
    for attr in ("text", "context", "block_attribs"):
        if hasattr(entity, attr):
            try:
                value = getattr(entity, attr)
                if attr == "context" and hasattr(value, "mtext"):
                    mtext = getattr(value, "mtext", None)
                    if mtext and hasattr(mtext, "default_content"):
                        candidates.append(clean_mtext(mtext.default_content))
                else:
                    candidates.append(_safe_text(value))
            except Exception:
                continue
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def _iter_text_candidates(entity):
    entity_type = entity.dxftype()
    layer = str(getattr(entity.dxf, "layer", ""))
    handle = str(getattr(entity.dxf, "handle", ""))
    owner = str(getattr(entity.dxf, "owner", ""))

    if entity_type == "TEXT":
        yield DxfTextRecord(handle, entity_type, owner, _safe_text(entity.dxf.text), str(entity.dxf.text), layer)
    elif entity_type == "MTEXT":
        raw = str(entity.text)
        yield DxfTextRecord(handle, entity_type, owner, clean_mtext(raw), raw, layer)
    elif entity_type == "ATTRIB":
        raw = str(entity.dxf.text)
        yield DxfTextRecord(handle, entity_type, owner, _safe_text(raw), raw, layer)
    elif entity_type == "ATTDEF":
        raw = str(entity.dxf.text)
        yield DxfTextRecord(handle, entity_type, owner, _safe_text(raw), raw, layer)
    elif entity_type == "DIMENSION":
        text = _dimension_text(entity)
        if text:
            yield DxfTextRecord(handle, entity_type, owner, text, text, layer)
    elif entity_type in {"MULTILEADER", "MLEADER"}:
        text = _multileader_text(entity)
        if text:
            yield DxfTextRecord(handle, entity_type, owner, text, text, layer)


def _add_context(record, *, block_name="", layout_name="", notes=""):
    return DxfTextRecord(
        handle=record.handle,
        entity_type=record.entity_type,
        owner=record.owner,
        text=record.text,
        raw_text=record.raw_text,
        layer=record.layer,
        block_name=block_name,
        layout_name=layout_name,
        notes=notes,
    )


def extract_text_records(doc):
    records = []

    for layout in doc.layouts:
        layout_name = layout.name
        for entity in layout:
            for record in _iter_text_candidates(entity):
                records.append(_add_context(record, layout_name=layout_name))

    for block in doc.blocks:
        if block.name.startswith("*"):
            continue
        for entity in block:
            for record in _iter_text_candidates(entity):
                records.append(_add_context(record, block_name=block.name))

    deduped = []
    seen = set()
    for record in records:
        key = (record.handle, record.entity_type, record.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)

    LOGGER.info("DXF extractor found %s text records", len(deduped))
    return deduped


def extract_texts(doc):
    return [(record.handle, record.text) for record in extract_text_records(doc)]


def count_untranslated_records(records):
    return sum(1 for record in records if CHINESE_RE.search(record.text))
