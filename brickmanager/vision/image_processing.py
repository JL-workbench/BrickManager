def rotate_image(image, rotation):
    import cv2
    codes = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
             270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(image, codes[rotation]) if rotation in codes else image
