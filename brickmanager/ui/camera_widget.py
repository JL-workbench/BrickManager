from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image

from brickmanager.vision.camera import get_camera_factory
from brickmanager.vision.image_processing import prepare_frame_for_kivy


class CameraWidget(Image):
    def __init__(self, camera_factory=None, **kwargs):
        super().__init__(**kwargs)
        self.camera_factory = camera_factory or get_camera_factory()
        self.camera = None
        self.camera_index = 0
        self.rotation = 0
        self._update_event = None
        self._permission_retry_event = None
        self.status_callback = None
        self.latest_frame = None
        self.allow_stretch = True
        self.keep_ratio = True

    def set_status_callback(self, callback):
        self.status_callback = callback

    def _status(self, message):
        if self.status_callback:
            self.status_callback(message)

    def start(self, camera_index=0, rotation=0):
        self.stop()
        self.camera_index = int(camera_index)
        self.rotation = int(rotation)
        camera = self.camera_factory(self.camera_index)
        if not camera.open():
            self._status(
                getattr(camera, "last_error", None)
                or f"Kamera {self.camera_index} konnte nicht geöffnet werden."
            )
            if getattr(camera, "permission_pending", False):
                self._permission_retry_event = Clock.schedule_once(
                    lambda *_: self.start(self.camera_index, self.rotation), 1.5
                )
            self.camera = None
            return False

        self.camera = camera
        self._update_event = Clock.schedule_interval(self._update_frame, 1 / 30)
        self._status(f"Kamera {self.camera_index} aktiv.")
        return True

    def _update_frame(self, dt):
        if self.camera is None:
            return

        ok, frame = self.camera.read()
        if not ok or frame is None:
            self.stop()
            self._status(f"Kamera {self.camera_index} konnte keinen Frame lesen.")
            return

        self.latest_frame = frame
        try:
            processed = prepare_frame_for_kivy(frame, self.rotation)
        except Exception:
            self.stop()
            self._status(f"Kamera {self.camera_index} konnte nicht verarbeitet werden.")
            return
        if processed is None:
            self.stop()
            self._status(f"Kamera {self.camera_index} konnte nicht verarbeitet werden.")
            return

        texture = Texture.create(
            size=(processed.shape[1], processed.shape[0]), colorfmt="rgb"
        )
        texture.blit_buffer(processed.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        texture.flip_vertical()
        self.texture = texture
        self.texture_size = texture.size

    def stop(self):
        if self._permission_retry_event is not None:
            self._permission_retry_event.cancel()
            self._permission_retry_event = None
        if self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        if self.camera is not None:
            self.camera.close()
            self.camera = None
        self.latest_frame = None

    def get_latest_frame(self):
        return self.latest_frame.copy() if self.latest_frame is not None else None

    def get_display_rect(self):
        texture_width, texture_height = self.texture_size
        if not texture_width or not texture_height or not self.width or not self.height:
            return self.x, self.y, self.width, self.height

        scale = min(self.width / texture_width, self.height / texture_height)
        display_width = texture_width * scale
        display_height = texture_height * scale
        return (
            self.x + (self.width - display_width) / 2,
            self.y + (self.height - display_height) / 2,
            display_width,
            display_height,
        )

    def on_touch_down(self, touch):
        return super().on_touch_down(touch)
