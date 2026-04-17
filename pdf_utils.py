from __future__ import annotations

import tempfile
from dataclasses import dataclass

import fitz


@dataclass
class PdfTextBlock:
    page_index: int
    bbox: tuple[float, float, float, float]
    text: str
    font_size: float
    color: tuple[float, float, float]
    align: int


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
    r = ((color_value >> 16) & 255) / 255
    g = ((color_value >> 8) & 255) / 255
    b = (color_value & 255) / 255
    return (r, g, b)


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


def _ocr_blocks_from_page(page: fitz.Page, page_index: int):
    try:
        from ocr_detect import detect_text_boxes
    except Exception:
        return []

    matrix = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(pix.tobytes("png"))
        image_path = tmp.name

    try:
        try:
            ocr_boxes = detect_text_boxes(image_path)
        except Exception:
            return []
    finally:
        try:
            import os

            os.unlink(image_path)
        except Exception:
            pass

    blocks = []
    scale_x = max(pix.width / max(page.rect.width, 1), 1)
    scale_y = max(pix.height / max(page.rect.height, 1), 1)

    for item in ocr_boxes:
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        x0, y0, x1, y1 = item["bbox"][0][0], item["bbox"][0][1], item["bbox"][2][0], item["bbox"][2][1]
        bbox = (
            float(x0) / scale_x,
            float(y0) / scale_y,
            float(x1) / scale_x,
            float(y1) / scale_y,
        )
        height = max(bbox[3] - bbox[1], 6.0)

        blocks.append(
            PdfTextBlock(
                page_index=page_index,
                bbox=bbox,
                text=text,
                font_size=max(height * 0.65, 7.0),
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
            )
        )

    return blocks


def extract_pdf_blocks(src) -> list[PdfTextBlock]:
    doc = open_pdf_document(src)
    blocks: list[PdfTextBlock] = []

    try:
        for page_index, page in enumerate(doc):
            page_dict = page.get_text("dict")
            page_blocks: list[PdfTextBlock] = []

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

                bbox = tuple(float(v) for v in block.get("bbox"))
                font_size = max(sum(sizes) / len(sizes), 6.0) if sizes else 10.0
                color = colors[0] if colors else (0, 0, 0)

                page_blocks.append(
                    PdfTextBlock(
                        page_index=page_index,
                        bbox=bbox,
                        text=clean_text,
                        font_size=font_size,
                        color=color,
                        align=align,
                    )
                )

            if not page_blocks:
                page_blocks.extend(_ocr_blocks_from_page(page, page_index))

            blocks.extend(page_blocks)
    finally:
        doc.close()

    return blocks


def fit_textbox(page: fitz.Page, rect: fitz.Rect, text: str, *, fontname: str = "helv", preferred_size: float | None = None) -> float:
    """Find a font size that fits the target rectangle."""
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
