from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np
import pandas as pd

from ocr_detect import detect_text_boxes
from post_translate_fix import has_chinese


LOGGER = logging.getLogger(__name__)
LATIN_NOISE_RE = r"^[A-Za-z0-9\s,.;:()/%×\-–—_?]{1,18}$"


@dataclass
class PdfTextBlock:
    page_index: int
    bbox: tuple[float, float, float, float]
    text: str
    font_size: float
    color: tuple[float, float, float]
    align: int
    source: str = "text"


def open_pdf_document(source):
    if isinstance(source, (str, bytes, bytearray)):
        return fitz.open(source)

    if hasattr(source, "read"):
        current_pos = None
        if hasattr(source, "tell"):
            try:
                current_pos = source.tell()
            except Exception:
                current_pos = None

        data = source.read()
        if hasattr(source, "seek"):
            try:
                source.seek(0 if current_pos is None else current_pos)
            except Exception:
                pass

        return fitz.open(stream=data, filetype="pdf")

    raise TypeError(f"Unsupported PDF source: {type(source)!r}")


def _int_to_rgb(color_value):
    return (((color_value >> 16) & 255) / 255, ((color_value >> 8) & 255) / 255, (color_value & 255) / 255)


def _block_alignment(block_bbox, line_bbox):
    bx0, _by0, bx1, _by1 = block_bbox
    lx0, _ly0, lx1, _ly1 = line_bbox
    left_gap = abs(lx0 - bx0)
    right_gap = abs(bx1 - lx1)
    center_gap = abs(((lx0 + lx1) / 2) - ((bx0 + bx1) / 2))
    width = max(bx1 - bx0, 1)

    if center_gap <= width * 0.08:
        return fitz.TEXT_ALIGN_CENTER
    if right_gap < left_gap and right_gap <= width * 0.08:
        return fitz.TEXT_ALIGN_RIGHT
    return fitz.TEXT_ALIGN_LEFT


def _normalize_text(text):
    return " ".join(str(text).split()).strip().lower()


def _bbox_distance(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return max(abs(ax0 - bx0), abs(ay0 - by0), abs(ax1 - bx1), abs(ay1 - by1))


def _looks_like_ocr_noise(text):
    value = " ".join(str(text).split()).strip()
    if not value:
        return True
    if len(value) <= 1:
        return True
    if value.count("?") >= 3:
        return True
    if len(value) <= 18 and not has_chinese(value) and pd.Series([value]).str.match(LATIN_NOISE_RE).iloc[0]:
        return True
    return False


def _merge_block_sets(primary, extra):
    merged = list(primary)

    for block in extra:
        norm_text = _normalize_text(block.text)
        if not norm_text or _looks_like_ocr_noise(block.text):
            continue

        duplicate = False
        replacement_index = None

        for index, existing in enumerate(merged):
            same_spot = _bbox_distance(existing.bbox, block.bbox) <= 8.0
            existing_norm = _normalize_text(existing.text)

            if same_spot and existing_norm == norm_text:
                duplicate = True
                break

            if same_spot and existing_norm and (norm_text in existing_norm or existing_norm in norm_text):
                if len(norm_text) > len(existing_norm):
                    replacement_index = index
                else:
                    duplicate = True
                break

        if duplicate:
            continue
        if replacement_index is not None:
            merged[replacement_index] = block
        else:
            merged.append(block)

    return sorted(merged, key=lambda item: (item.page_index, item.bbox[1], item.bbox[0]))


def _page_dict_to_blocks(page_dict, page_index):
    page_blocks = []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        lines = block.get("lines", [])
        if not lines:
            continue

        parts = []
        sizes = []
        colors = []
        align = fitz.TEXT_ALIGN_LEFT

        for line in lines:
            line_parts = []
            line_bbox = tuple(line.get("bbox", block.get("bbox")))
            align = _block_alignment(block.get("bbox", line_bbox), line_bbox)

            for span in line.get("spans", []):
                span_text = str(span.get("text", ""))
                if not span_text.strip():
                    continue
                line_parts.append(span_text)
                sizes.append(float(span.get("size", 10)))
                colors.append(_int_to_rgb(int(span.get("color", 0))))

            if line_parts:
                parts.append("".join(line_parts).strip())

        clean_text = "\n".join(part for part in parts if part).strip()
        if not clean_text:
            continue

        page_blocks.append(
            PdfTextBlock(
                page_index=page_index,
                bbox=tuple(float(v) for v in block.get("bbox")),
                text=clean_text,
                font_size=max(sum(sizes) / len(sizes), 6.0) if sizes else 10.0,
                color=colors[0] if colors else (0, 0, 0),
                align=align,
                source="text",
            )
        )

    return page_blocks


def _line_blocks_from_words(words, page_index, *, source="ocr_textpage"):
    if not words:
        return []

    ordered = sorted(words, key=lambda item: (float(item[1]), float(item[0])))
    rows = []

    for word in ordered:
        x0, y0, x1, y1, text = word[:5]
        text = str(text).strip()
        if _looks_like_ocr_noise(text):
            continue

        placed = False
        for row in rows:
            row_height = max(row["bbox"][3] - row["bbox"][1], 1.0)
            if abs(y0 - row["bbox"][1]) <= row_height * 0.65:
                row["items"].append((x0, text))
                row["bbox"] = (
                    min(row["bbox"][0], float(x0)),
                    min(row["bbox"][1], float(y0)),
                    max(row["bbox"][2], float(x1)),
                    max(row["bbox"][3], float(y1)),
                )
                placed = True
                break

        if not placed:
            rows.append({"bbox": (float(x0), float(y0), float(x1), float(y1)), "items": [(float(x0), text)]})

    blocks = []
    for row in rows:
        items = sorted(row["items"], key=lambda item: item[0])
        text = " ".join(part for _x, part in items).strip()
        if _looks_like_ocr_noise(text):
            continue
        bbox = row["bbox"]
        blocks.append(
            PdfTextBlock(
                page_index=page_index,
                bbox=bbox,
                text=text,
                font_size=max((bbox[3] - bbox[1]) * 0.75, 6.0),
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
                source=source,
            )
        )

    return blocks


def _ocr_blocks_from_raster(page, page_index, *, aggressive=False):
    matrix = fitz.Matrix(4, 4) if aggressive else fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n).copy()

    def detect(image_array, *, merge, min_score, min_size):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            cv2.imwrite(tmp.name, image_array)
            path = tmp.name
        try:
            return detect_text_boxes(path, merge=merge, min_score=min_score, min_size=min_size)
        except Exception as exc:
            LOGGER.warning("Raster OCR failed on temp image: %s", exc)
            return []
        finally:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    boxes = detect(image, merge=not aggressive, min_score=0.12 if aggressive else 0.2, min_size=4 if aggressive else 6)

    if aggressive or len(boxes) < 40:
        height, width = image.shape[:2]
        zones = [
            (0, 0, width, height // 2),
            (0, height // 2, width, height),
            (0, 0, width // 2, height),
            (width // 2, 0, width, height),
            (0, 0, width // 2, height // 2),
            (width // 2, 0, width, height // 2),
            (0, height // 2, width // 2, height),
            (width // 2, height // 2, width, height),
            (0, int(height * 0.72), width, height),
            (0, 0, width, int(height * 0.28)),
        ]
        zone_boxes = []
        for x0, y0, x1, y1 in zones:
            crop = image[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            for item in detect(crop, merge=False, min_score=0.1 if aggressive else 0.18, min_size=4):
                bbox = np.array(item["bbox"], dtype=float)
                bbox[:, 0] += x0
                bbox[:, 1] += y0
                zone_boxes.append({**item, "bbox": bbox.tolist()})
        boxes.extend(zone_boxes)

    scale_x = max(pix.width / max(page.rect.width, 1), 1)
    scale_y = max(pix.height / max(page.rect.height, 1), 1)
    blocks = []
    for item in boxes:
        text = str(item.get("text", "")).strip()
        if _looks_like_ocr_noise(text):
            continue
        x0, y0 = item["bbox"][0]
        x1, y1 = item["bbox"][2]
        bbox = (float(x0) / scale_x, float(y0) / scale_y, float(x1) / scale_x, float(y1) / scale_y)
        height = max(bbox[3] - bbox[1], 6.0)
        blocks.append(
            PdfTextBlock(
                page_index=page_index,
                bbox=bbox,
                text=text,
                font_size=max(height * 0.65, 7.0),
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
                source="ocr_raster_aggressive" if aggressive else "ocr_raster",
            )
        )

    return blocks


def _ocr_blocks_from_textpage(page, page_index):
    try:
        textpage = page.get_textpage_ocr(language="chi_sim+eng", dpi=220, full=True)
    except Exception as exc:
        LOGGER.warning("PyMuPDF OCR textpage failed on page %s: %s", page_index, exc)
        return []

    try:
        try:
            page_dict = page.get_text("dict", textpage=textpage)
        except TypeError:
            page_dict = textpage.extractDICT()
        dict_blocks = _page_dict_to_blocks(page_dict, page_index)
    except Exception:
        dict_blocks = []

    try:
        words = page.get_text("words", textpage=textpage, sort=True)
    except Exception:
        words = []

    word_blocks = _line_blocks_from_words(words, page_index, source="ocr_textpage")
    return word_blocks if len(word_blocks) > len(dict_blocks) else dict_blocks


def classify_pdf_mode(source):
    doc = open_pdf_document(source)
    try:
        page_modes = []
        page_stats = []
        for page in doc:
            page_dict = page.get_text("dict")
            text_blocks = _page_dict_to_blocks(page_dict, page.number)
            total_chars = sum(len(block.text) for block in text_blocks)
            image_blocks = sum(1 for block in page_dict.get("blocks", []) if block.get("type") == 1)
            if total_chars >= 200:
                mode = "text"
            elif total_chars >= 30 or (text_blocks and image_blocks):
                mode = "hybrid"
            else:
                mode = "scanned"
            page_modes.append(mode)
            page_stats.append({"page": page.number, "text_blocks": len(text_blocks), "chars": total_chars, "images": image_blocks})

        if all(mode == "text" for mode in page_modes):
            mode = "text"
        elif all(mode == "scanned" for mode in page_modes):
            mode = "scanned"
        else:
            mode = "hybrid"
        return {"mode": mode, "page_modes": page_modes, "page_stats": page_stats}
    finally:
        doc.close()


def extract_pdf_blocks(source):
    doc = open_pdf_document(source)
    blocks = []

    try:
        for page in doc:
            page_dict = page.get_text("dict")
            text_blocks = _page_dict_to_blocks(page_dict, page.number)
            page_blocks = list(text_blocks)

            total_chars = sum(len(block.text) for block in page_blocks)
            sparse = len(page_blocks) < 30 or total_chars < 500

            if sparse:
                page_blocks = _merge_block_sets(page_blocks, _ocr_blocks_from_textpage(page, page.number))
            if sparse:
                page_blocks = _merge_block_sets(page_blocks, _ocr_blocks_from_raster(page, page.number))
            if len(page_blocks) < 40:
                page_blocks = _merge_block_sets(page_blocks, _ocr_blocks_from_raster(page, page.number, aggressive=True))

            blocks.extend(page_blocks)
    finally:
        doc.close()

    return blocks


def build_pdf_qc_report(source, translated_df=None):
    mode_info = classify_pdf_mode(source)
    blocks = extract_pdf_blocks(source)
    report_rows = []

    for block in blocks:
        row = {
            "page": block.page_index,
            "text": block.text,
            "source": block.source,
            "bbox": block.bbox,
            "has_chinese": has_chinese(block.text),
            "ocr_noise": _looks_like_ocr_noise(block.text),
        }
        report_rows.append(row)

    report = pd.DataFrame(report_rows)
    if translated_df is not None and not translated_df.empty:
        limit = min(len(report), len(translated_df))
        report.loc[: limit - 1, "translated"] = translated_df["translated"].iloc[:limit].tolist()
        report.loc[: limit - 1, "untranslated_chinese"] = translated_df["untranslated_chinese"].iloc[:limit].tolist()
    report.attrs["mode_info"] = mode_info
    return report


def fit_textbox(page, rect, text, *, fontname="helv", preferred_size=None):
    width = max(rect.width, 1)
    height = max(rect.height, 1)
    start_size = preferred_size if preferred_size is not None else height
    start_size = max(min(int(start_size), max(int(height), 6)), 6)

    for fontsize in range(start_size, 5, -1):
        text_width = fitz.get_text_length(text.replace("\n", " "), fontname=fontname, fontsize=fontsize)
        line_count = max(text.count("\n") + 1, 1)
        estimated_height = fontsize * 1.35 * line_count
        if text_width <= width * 1.03 and estimated_height <= height * 1.1:
            return float(fontsize)

    return max(min(height / max(text.count("\n") + 1, 1) * 0.8, 8), 6)
