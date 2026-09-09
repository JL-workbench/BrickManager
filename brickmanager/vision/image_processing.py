import cv2


def rotate_image(image, rotation):
    codes = {
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }
    return cv2.rotate(image, codes[rotation]) if rotation in codes else image


def prepare_frame_for_kivy(frame, rotation=0):
    if frame is None:
        return None

    rotated = rotate_image(frame, rotation)
    return cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
