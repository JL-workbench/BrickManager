import cv2

class CameraService:
    def open(self): raise NotImplementedError
    def read(self): raise NotImplementedError
    def close(self): raise NotImplementedError

class OpenCVCamera(CameraService):
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.capture = None
    def open(self):
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        return self.capture.isOpened()
    def read(self):
        return (False, None) if self.capture is None else self.capture.read()
    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
