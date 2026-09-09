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


def save_snapshot(frame, path, rotation=0, roi=None):
    if frame is None:
        return False

    snapshot = prepare_snapshot_frame(frame, rotation, roi)
    return bool(cv2.imwrite(str(path), snapshot))


def prepare_snapshot_frame(frame, rotation=0, roi=None):
    snapshot = rotate_image(frame, rotation)
    if roi is not None:
        from brickmanager.vision.roi import apply_roi

        snapshot = apply_roi(snapshot, roi)
    return snapshot
