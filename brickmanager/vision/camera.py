import cv2


class CameraService:
    def open(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class OpenCVCamera(CameraService):
    def __init__(self, camera_index=0):
        self.camera_index = int(camera_index)
        self.capture = None

    def open(self):
        self.close()
        try:
            self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if self.capture is None or not self.capture.isOpened():
                self.close()
                return False
            return True
        except Exception:
            self.close()
            return False

    def read(self):
        if self.capture is None:
            return False, None
        try:
            ok, frame = self.capture.read()
            if not ok or frame is None:
                return False, None
            return True, frame
        except Exception:
            self.close()
            return False, None

    def close(self):
        if self.capture is not None:
            try:
                self.capture.release()
            except Exception:
                pass
            self.capture = None

    @staticmethod
    def enumerate_devices(max_index=9):
        found = []
        for index in range(max_index + 1):
            capture = None
            try:
                capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if capture is not None and capture.isOpened():
                    found.append(index)
            except Exception:
                pass
            finally:
                if capture is not None:
                    try:
                        capture.release()
                    except Exception:
                        pass
        return found
