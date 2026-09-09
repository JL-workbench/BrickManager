def apply_roi(image, roi):
    h, w = image.shape[:2]
    x = max(0, min(w, int(roi.get("x",0)*w)))
    y = max(0, min(h, int(roi.get("y",0)*h)))
    rw = max(1, int(roi.get("width",1)*w))
    rh = max(1, int(roi.get("height",1)*h))
    return image[y:min(y+rh,h), x:min(x+rw,w)]
