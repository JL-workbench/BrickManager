def mean_rgb(image):
    if image is None or image.size == 0:
        return None
    import cv2
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return tuple(int(round(v)) for v in rgb.reshape(-1,3).mean(axis=0))
