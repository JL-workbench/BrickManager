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
    """Windows camera backend using OpenCV."""

    def __init__(self, camera_index=0):
        self.camera_index = int(camera_index)
        self.capture = None
        self.last_error = None

    def open(self):
        self.close()
        self.last_error = None

        try:
            self.capture = cv2.VideoCapture(
                self.camera_index,
                cv2.CAP_DSHOW,
            )

            if self.capture is None or not self.capture.isOpened():
                self.last_error = (
                    f"Kamera {self.camera_index} konnte nicht geöffnet werden."
                )
                self.close()
                return False
            return True

        except Exception as exc:
            self.last_error = (
                f"Kamera {self.camera_index} konnte nicht geöffnet werden: {exc}"
            )
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

        except Exception as exc:
            self.last_error = f"Kameraframe konnte nicht gelesen werden: {exc}"
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
        """Find available Windows cameras."""
        found = []
        for index in range(max_index + 1):
            capture = None
            try:
                capture = cv2.VideoCapture(
                    index,
                    cv2.CAP_DSHOW,
                )

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
    """
    Android camera backend.

    Uses Kivy's Android camera provider for the normal
    smartphone camera and converts the resulting RGBA
    texture into a BGR NumPy array so that the rest of
    BrickManager can continue using OpenCV unchanged.
    """

    def __init__(self, camera_index=0):
        self.camera_index = int(camera_index)

        # Kivy Core Camera object
        self.capture = None

        # Android permission state
        self.permission_pending = False

        # Diagnostic information
        self.last_error = None

        # Prevent excessive log messages
        self._logged_first_frame = False

    def open(self):
        self.close()

        self.permission_pending = False
        self.last_error = None
        self._logged_first_frame = False

        # ---------------------------------------------------------
        # Android camera permission
        # ---------------------------------------------------------
        if not self._request_camera_permission():
            self.permission_pending = True
            self.last_error = (
                "Kameraberechtigung wird angefordert. "
                "Bitte den Zugriff auf die Kamera erlauben."
            )
            self._log("Kameraberechtigung noch nicht vorhanden.")
            return False

        # ---------------------------------------------------------
        # Open Kivy Android camera
        # ---------------------------------------------------------
        try:
            from kivy.core.camera import Camera as CoreCamera

            self._log(f"Öffne Android-Kamera index={self.camera_index}")

            self.capture = CoreCamera(
                index=self.camera_index,
                resolution=(1280, 720),
                play=True,
            )

            # Some Kivy versions use start(), others start
            # automatically when play=True.
            try:
                self.capture.start()
            except Exception:
                # Ignore this if the provider already started.
                pass

            self._log("Android-Kameraobjekt erfolgreich erstellt.")

            return True

        except Exception as exc:
            self.last_error = f"Android-Kamera konnte nicht geöffnet werden: {exc}"

            self._log(f"FEHLER beim Öffnen der Android-Kamera: {exc!r}")

            self.close()
            return False

    @staticmethod
    def _request_camera_permission():
        """
        Check and request Android CAMERA permission.

        Returns:
            True  -> permission already granted
            False -> permission must still be granted/requested
        """
        try:
            from android.permissions import (
                Permission,
                check_permission,
                request_permissions,
            )

            if check_permission(Permission.CAMERA):
                return True

            request_permissions([Permission.CAMERA])

            return False

        except ImportError:
            # This happens when running outside Android,
            # e.g. on Windows.
            return False

        except Exception:
            return False

    def read(self):
        """
        Return the current Android camera frame as BGR NumPy array.

        Returns:
            (True, frame)  when a valid frame is available
            (False, None) otherwise
        """

        if self.capture is None:
            return False, None

        try:
            texture = self.capture.texture

            if texture is None:
                return False, None

            width, height = texture.size

            if width <= 0 or height <= 0:
                return False, None

            pixels = texture.pixels

            if pixels is None or len(pixels) == 0:
                return False, None

            expected_size = width * height * 4

            if len(pixels) != expected_size:
                self.last_error = (
                    "Ungültige Android-Kameratextur: "
                    f"{len(pixels)} Bytes statt {expected_size}."
                )

                self._log(self.last_error)

                return False, None

            # Kivy texture is RGBA.
            rgba = np.frombuffer(
                pixels,
                dtype=np.uint8,
            ).reshape(
                height,
                width,
                4,
            )

            # Kivy texture origin is bottom-left.
            rgba = np.flipud(rgba)

            # Convert to OpenCV BGR.
            frame = cv2.cvtColor(
                rgba,
                cv2.COLOR_RGBA2BGR,
            )

            if not self._logged_first_frame:
                self._logged_first_frame = True

                self._log(f"Erster Android-Kameraframe empfangen: {width}x{height}")

            return True, frame

        except Exception as exc:
            self.last_error = f"Android-Kameraframe konnte nicht gelesen werden: {exc}"

            self._log(f"FEHLER beim Lesen des Android-Kameraframe: {exc!r}")

            return False, None

    def close(self):
        """Stop and release the Android camera."""

        if self.capture is not None:
            try:
                self.capture.stop()
            except Exception:
                pass

            try:
                self.capture.play = False
            except Exception:
                pass

            self.capture = None

        self._logged_first_frame = False

    @staticmethod
    def enumerate_devices(max_index=9):
        """
        Android normally exposes the smartphone camera through
        Kivy as camera index 0.

        We deliberately return only index 0 here.
        """
        return [0]

    @staticmethod
    def _log(message):
        """Write diagnostic messages to the Kivy Android log."""
        try:
            from kivy.logger import Logger

            Logger.info(f"BRICKMANAGER CAMERA: {message}")

        except Exception:
            pass


def get_camera_factory(platform_name=None):
    """
    Select the platform-specific camera backend.

    Windows:
        OpenCV + DirectShow

    Android:
        Kivy Android camera provider
    """

    current_platform = platform_name or sys.platform

    if current_platform == "android":
        return AndroidKivyCamera

    return OpenCVCamera
