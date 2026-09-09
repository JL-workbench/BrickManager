import sys

import cv2
import numpy as np


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


class AndroidKivyCamera(CameraService):
    """Android camera adapter that returns BGR NumPy frames to CameraWidget."""

    def __init__(self, camera_index=0):
        self.camera_index = int(camera_index)
        self.capture = None
        self.permission_pending = False
        self.last_error = None

    def open(self):
        self.close()
        if not self._camera_permission_granted():
            self.permission_pending = True
            self.last_error = "Kameraberechtigung wird angefordert."
            return False
        try:
            from kivy.core.camera import Camera as CoreCamera

            self.capture = CoreCamera(index=self.camera_index, resolution=(640, 480))
            self.capture.start()
            return True
        except Exception as exc:
            self.last_error = f"Android-Kamera konnte nicht geöffnet werden: {exc}"
            self.close()
            return False

    @staticmethod
    def _camera_permission_granted():
        try:
            from android.permissions import Permission, check_permission, request_permissions

            if check_permission(Permission.CAMERA):
                return True
            request_permissions([Permission.CAMERA])
            return False
        except ImportError:
            return False

    def read(self):
        if self.capture is None or self.capture.texture is None:
            return False, None
        try:
            texture = self.capture.texture
            width, height = texture.size
            rgba = np.frombuffer(texture.pixels, dtype=np.uint8).reshape(height, width, 4)
            rgba = np.flipud(rgba)
            return True, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        except Exception as exc:
            self.last_error = f"Android-Kameraframe konnte nicht gelesen werden: {exc}"
            return False, None

    def close(self):
        if self.capture is not None:
            try:
                self.capture.stop()
            except Exception:
                pass
            self.capture = None

    @staticmethod
    def enumerate_devices(max_index=9):
        return [0]


def get_camera_factory(platform_name=None):
    """Select the platform camera backend without leaking it into UI screens."""
    return AndroidKivyCamera if (platform_name or sys.platform) == "android" else OpenCVCamera
