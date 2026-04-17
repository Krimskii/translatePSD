from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass
class PdfTextBlock:
    page_index: int
    bbox: tuple[float, float, float, float]
    text: str


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


def extract_pdf_blocks(src) -> list[PdfTextBlock]:
    doc = open_pdf_document(src)
    blocks: list[PdfTextBlock] = []

    try:
        for page_index, page in enumerate(doc):
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text, block_no, block_type = block
                if block_type != 0:
                    continue

                clean_text = str(text).strip()
                if not clean_text:
                    continue

                blocks.append(
                    PdfTextBlock(
                        page_index=page_index,
                        bbox=(float(x0), float(y0), float(x1), float(y1)),
                        text=clean_text,
                    )
                )
    finally:
        doc.close()

    return blocks


def fit_textbox(page: fitz.Page, rect: fitz.Rect, text: str, *, fontname: str = "helv") -> float:
    """Find a font size that fits the target rectangle."""
    width = max(rect.width, 1)
    height = max(rect.height, 1)

    for fontsize in range(max(int(height), 1), 5, -1):
        text_width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        estimated_height = fontsize * 1.35

        if text_width <= width * 1.02 and estimated_height <= height * 1.15:
            return float(fontsize)

    return max(min(height * 0.8, 8), 6)
