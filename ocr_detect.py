import os
import shutil
import subprocess
import tempfile
from io import StringIO

import cv2
import numpy as np
import pandas as pd


os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_OCR = None


def _build_ocr_instance():
    from paddleocr import PaddleOCR

    attempts = [
        {"use_textline_orientation": True, "lang": "ch", "ocr_version": "PP-OCRv5"},
        {"use_textline_orientation": True, "lang": "ch"},
        {"use_angle_cls": True, "lang": "ch"},
    ]

    last_error = None
    for kwargs in attempts:
        for candidate in (dict(kwargs, show_log=False), dict(kwargs)):
            try:
                return PaddleOCR(**candidate)
            except (TypeError, ValueError) as exc:
                last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("Unable to initialize PaddleOCR.")


def _get_ocr():
    global _OCR
    if _OCR is None:
        _OCR = _build_ocr_instance()
    return _OCR


def _bbox_to_polygon(bbox):
    arr = np.array(bbox, dtype=float)
    if arr.ndim == 1 and arr.size >= 4:
        x0, y0, x1, y1 = arr[:4].tolist()
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    if arr.ndim == 2 and arr.shape[1] >= 2:
        return arr[:, :2].tolist()
    raise ValueError(f"Unsupported bbox shape: {arr.shape}")


def _bbox_bounds(bbox):
    polygon = _bbox_to_polygon(bbox)
    xs = [float(point[0]) for point in polygon]
    ys = [float(point[1]) for point in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_iou(a, b):
    ax0, ay0, ax1, ay1 = _bbox_bounds(a)
    bx0, by0, bx1, by1 = _bbox_bounds(b)
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(ix1 - ix0, 0), max(iy1 - iy0, 0)
    intersection = iw * ih
    if intersection <= 0:
        return 0.0
    area_a = max((ax1 - ax0) * (ay1 - ay0), 1.0)
    area_b = max((bx1 - bx0) * (by1 - by0), 1.0)
    return intersection / max(area_a + area_b - intersection, 1.0)


def _dedupe_raw_lines(lines):
    deduped = []

    for bbox, text, score in sorted(lines, key=lambda item: (-float(item[2]), len(str(item[1])))):
        text = str(text).strip()
        if not text:
            continue

        duplicate = False
        for existing_bbox, existing_text, existing_score in deduped:
            same_text = text == existing_text or text in existing_text or existing_text in text
            if same_text and _bbox_iou(bbox, existing_bbox) >= 0.35:
                duplicate = True
                break

        if not duplicate:
            deduped.append((bbox, text, score))

    return deduped


def _merge_lines(lines):
    if not lines:
        return []

    ordered = sorted(lines, key=lambda item: (item["bounds"][1], item["bounds"][0]))
    merged = []

    for item in ordered:
        if not merged:
            merged.append(item)
            continue

        prev = merged[-1]
        px0, py0, px1, py1 = prev["bounds"]
        x0, y0, x1, y1 = item["bounds"]

        prev_height = max(py1 - py0, 1.0)
        same_row = abs(y0 - py0) <= prev_height * 0.55
        near_horizontally = x0 - px1 <= prev_height * 2.5

        if same_row and near_horizontally:
            prev["text"] = f'{prev["text"]} {item["text"]}'.strip()
            prev["score"] = min(prev["score"], item["score"])
            prev["bounds"] = (min(px0, x0), min(py0, y0), max(px1, x1), max(py1, y1))
            prev["bbox"] = [
                [prev["bounds"][0], prev["bounds"][1]],
                [prev["bounds"][2], prev["bounds"][1]],
                [prev["bounds"][2], prev["bounds"][3]],
                [prev["bounds"][0], prev["bounds"][3]],
            ]
        else:
            merged.append(item)

    return merged


def _extract_old_style_lines(result):
    if not isinstance(result, list) or not result:
        return []

    first = result[0]
    if not isinstance(first, list):
        return []

    extracted = []
    for line in first:
        try:
            bbox = line[0]
            text = str(line[1][0]).strip()
            score = float(line[1][1])
        except Exception:
            continue
        extracted.append((bbox, text, score))
    return extracted


def _extract_new_style_lines(result):
    if not isinstance(result, list) or not result:
        return []

    extracted = []
    for item in result:
        if not isinstance(item, dict):
            continue

        polys = item.get("rec_polys") or item.get("dt_polys") or item.get("rec_boxes") or []
        texts = item.get("rec_texts") or []
        scores = item.get("rec_scores") or [1.0] * len(texts)

        for bbox, text, score in zip(polys, texts, scores):
            try:
                extracted.append((bbox, str(text).strip(), float(score)))
            except Exception:
                continue

    return extracted


def _extract_lines(result):
    lines = _extract_old_style_lines(result)
    if lines:
        return lines
    return _extract_new_style_lines(result)


def _prepare_images(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    variants = [img, cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR), cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)]
    return variants


def _find_tesseract():
    candidates = [
        os.getenv("TESSERACT_EXE"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _tesseract_tsv_lines(img_path):
    tesseract = _find_tesseract()
    if not tesseract:
        return []

    attempts = [
        ("chi_sim+eng", "11"),
        ("chi_sim+eng", "6"),
        ("eng", "11"),
    ]

    best_lines = []
    for lang, psm in attempts:
        command = [
            tesseract,
            img_path,
            "stdout",
            "--psm",
            psm,
            "-l",
            lang,
            "tsv",
        ]

        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        try:
            table = pd.read_csv(StringIO(completed.stdout), sep="\t")
        except Exception:
            continue

        if table.empty or "text" not in table.columns:
            continue

        table = table.fillna("")
        table["text"] = table["text"].astype(str).str.strip()
        table = table[table["text"] != ""]
        if table.empty:
            continue

        if "conf" in table.columns:
            table["conf"] = pd.to_numeric(table["conf"], errors="coerce").fillna(-1)
            table = table[table["conf"] >= 20]
            if table.empty:
                continue

        line_groups = []
        group_cols = [col for col in ["block_num", "par_num", "line_num"] if col in table.columns]
        grouped = table.groupby(group_cols) if group_cols else [(None, table)]

        for _key, group in grouped:
            if group.empty:
                continue

            text = " ".join(group["text"].tolist()).strip()
            if not text:
                continue

            left = float(group["left"].min())
            top = float(group["top"].min())
            right = float((group["left"] + group["width"]).max())
            bottom = float((group["top"] + group["height"]).max())
            score = float(group["conf"].mean()) / 100.0 if "conf" in group.columns else 0.7

            line_groups.append(
                (
                    [
                        [left, top],
                        [right, top],
                        [right, bottom],
                        [left, bottom],
                    ],
                    text,
                    score,
                )
            )

        if len(line_groups) > len(best_lines):
            best_lines = line_groups

    return best_lines


def _tesseract_tsv_lines_from_image(image):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        cv2.imwrite(tmp.name, image)
        tmp_path = tmp.name

    try:
        return _tesseract_tsv_lines(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _run_ocr(image):
    ocr = _get_ocr()

    if hasattr(ocr, "predict"):
        try:
            return ocr.predict(
                image,
                use_textline_orientation=True,
                text_rec_score_thresh=0.2,
            )
        except TypeError:
            pass

    return ocr.ocr(image, cls=True)


def detect_text_boxes(img_path, *, merge=True, min_score=0.2, min_size=6):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Image not found or unreadable: {img_path}")

    scale = 1.0
    max_side = max(img.shape[:2])
    if max_side < 2600:
        scale = min(2600 / max_side, 2.0)
        if scale > 1.05:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    raw_lines = []
    for prepared in _prepare_images(img):
        try:
            result = _run_ocr(prepared)
            raw_lines.extend(_extract_lines(result))
        except Exception:
            pass

    for prepared in _prepare_images(img):
        raw_lines.extend(_tesseract_tsv_lines_from_image(prepared))

    if not raw_lines:
        return []

    raw_lines = _dedupe_raw_lines(raw_lines)

    lines = []
    for bbox, text, score in raw_lines:
        bbox = _bbox_to_polygon(bbox)
        if scale != 1.0:
            bbox = (np.array(bbox, dtype=float) / scale).tolist()

        if score < min_score or not text:
            continue

        bounds = _bbox_bounds(bbox)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]

        if width < min_size or height < min_size:
            continue

        lines.append({"bbox": bbox, "bounds": bounds, "text": text, "score": score})

    if merge:
        lines = _merge_lines(lines)

    for item in lines:
        item.pop("bounds", None)

    return lines
