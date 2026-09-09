def apply_roi(image, roi):
    h, w = image.shape[:2]
    x = max(0, min(max(w - 1, 0), int(roi.get("x", 0) * w)))
    y = max(0, min(max(h - 1, 0), int(roi.get("y", 0) * h)))
    right = max(x + 1, min(w, x + int(roi.get("width", 1) * w)))
    bottom = max(y + 1, min(h, y + int(roi.get("height", 1) * h)))
    return image[y:bottom, x:right]
