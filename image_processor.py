"""
Crack image preprocessing and feature extraction using OpenCV.
Returns: crack_type, orientation_label, estimated width class, processed image bytes.
"""

import cv2
import numpy as np
from PIL import Image
import io


def preprocess(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")
    return img


def extract_crack_mask(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Stage 1: isolate very dark pixels (crack is 30–60, texture is 130+) ──
    # Use raw gray (no CLAHE) so absolute darkness is preserved
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Threshold: keep pixels below the 3rd percentile — captures only the crack
    thresh_val = int(np.percentile(blurred, 3))
    thresh_val = min(thresh_val, 100)          # cap so we never threshold out everything
    _, dark = cv2.threshold(blurred, thresh_val, 255, cv2.THRESH_BINARY_INV)

    # ── Stage 2: filter — keep only elongated connected components ──
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k_close, iterations=2)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    for i in range(1, n_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 30:
            continue
        # Use rotated min-area rect — correct elongation for diagonal cracks
        component_pts = np.column_stack(np.where(labels == i))
        if len(component_pts) < 5:
            continue
        # minAreaRect expects (x,y) points
        xy_pts = component_pts[:, ::-1].astype(np.float32)
        rect = cv2.minAreaRect(xy_pts)
        rw, rh = rect[1]
        long_side  = max(rw, rh)
        short_side = min(rw, rh) + 1e-6
        elongation = long_side / short_side
        # Cracks: long (>= 60px in rotated frame) and elongated (>= 3×)
        if long_side >= 60 and elongation >= 3.0:
            mask[labels == i] = 255

    # Dilate 3px so the crack is visible in the overlay
    k_vis = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.dilate(mask, k_vis, iterations=1)

    # Blank image border
    b = 8
    mask[:b, :] = 0;  mask[-b:, :] = 0
    mask[:, :b] = 0;  mask[:, -b:] = 0
    return mask


def detect_orientation(mask: np.ndarray) -> tuple[str, float]:
    """Returns (orientation_label, dominant_angle_degrees)"""
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30,
                             minLineLength=20, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return "Vertical (flexural)", 90.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        angles.append(angle)

    mean_angle = float(np.mean(angles))

    if mean_angle < 20 or mean_angle > 160:
        label = "Horizontal"
    elif 70 <= mean_angle <= 110:
        label = "Vertical (flexural)"
    else:
        label = "Diagonal (shear/joint)"

    return label, round(mean_angle, 1)


def estimate_crack_width(mask: np.ndarray) -> str:
    """Estimate width class from skeleton perpendicular distance."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return "Hairline (<0.1 mm)"

    total_area = sum(cv2.contourArea(c) for c in contours)
    total_len = sum(cv2.arcLength(c, False) for c in contours)

    if total_len == 0:
        return "Hairline (<0.1 mm)"

    avg_width_px = total_area / (total_len + 1e-6) * 2
    h, w = mask.shape
    width_fraction = avg_width_px / min(h, w)

    if width_fraction < 0.005:
        return "Hairline (<0.1 mm)"
    elif width_fraction < 0.015:
        return "Fine (0.1–0.3 mm)"
    elif width_fraction < 0.030:
        return "Moderate (0.3–0.5 mm)"
    else:
        return "Wide (>0.5 mm)"


def classify_crack(orientation: str, mask: np.ndarray) -> str:
    """
    Rule-based crack type classifier using orientation and mask geometry.
    Maps to the 5 classes in the report.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "Uncertain / Mixed"

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    aspect = h / (w + 1e-6)

    if orientation == "Vertical (flexural)" and aspect > 2.0:
        return "Flexural"
    elif orientation == "Diagonal (shear/joint)" and aspect < 3.0:
        return "Shear"
    elif orientation == "Diagonal (shear/joint)" and aspect >= 3.0:
        return "Joint-diagonal"
    elif orientation == "Horizontal":
        return "Bond / Boundary"
    else:
        return "Uncertain / Mixed"


def render_overlay(img: np.ndarray, mask: np.ndarray) -> bytes:
    """Grayscale base with crack pixels painted red, bounding box and label."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)   # pure grayscale base

    # Paint crack pixels bright red directly — nothing else is coloured
    out[mask > 0] = [0, 0, 230]

    # Thin red contour border around each crack region
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, (0, 0, 255), 1)

    # Cyan bounding box + label on largest crack
    if contours:
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        cv2.rectangle(out, (x - 4, y - 4), (x + w + 4, y + h + 4), (200, 200, 0), 2)

        label = "CRACK DETECTED"
        font  = cv2.FONT_HERSHEY_SIMPLEX
        scale, thick = 0.55, 2
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        tag_x = max(x - 4, 0)
        tag_y = max(y - 10, th + 6)
        cv2.rectangle(out, (tag_x, tag_y - th - 4), (tag_x + tw + 6, tag_y + 2), (0, 0, 180), -1)
        cv2.putText(out, label, (tag_x + 3, tag_y - 2), font, scale,
                    (255, 255, 255), thick, cv2.LINE_AA)

    _, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return buf.tobytes()


def classification_confidence(mask: np.ndarray, orientation: str,
                               crack_type: str) -> float:
    """
    Estimates classifier confidence (0–1) based on image quality signals.
    Low confidence triggers the uncertainty flag in the app.
    """
    score = 1.0

    # Signal 1: crack fill ratio — too sparse or too dense → ambiguous
    fill = cv2.countNonZero(mask) / mask.size
    if fill < 0.002:
        score -= 0.40   # barely any crack visible
    elif fill > 0.35:
        score -= 0.25   # image too noisy / not a crack photo

    # Signal 2: orientation line count — few lines → poor image
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30,
                             minLineLength=20, maxLineGap=10)
    n_lines = len(lines) if lines is not None else 0
    if n_lines < 3:
        score -= 0.25
    elif n_lines > 60:
        score -= 0.10   # very noisy

    # Signal 3: uncertain type gets penalty
    if crack_type == "Uncertain / Mixed":
        score -= 0.20

    return round(max(0.0, min(score, 1.0)), 2)


def process_image(image_bytes: bytes) -> dict:
    img = preprocess(image_bytes)
    mask = extract_crack_mask(img)
    orientation, angle = detect_orientation(mask)
    width_class = estimate_crack_width(mask)
    crack_type = classify_crack(orientation, mask)
    overlay_bytes = render_overlay(img, mask)
    confidence = classification_confidence(mask, orientation, crack_type)

    crack_detected = cv2.countNonZero(mask) > (mask.size * 0.002)

    return {
        "crack_detected": crack_detected,
        "crack_type": crack_type,
        "orientation": orientation,
        "width_class": width_class,
        "angle_degrees": angle,
        "overlay_bytes": overlay_bytes,
        "confidence": confidence,
        "low_confidence": confidence < 0.60,
    }
