from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from brickmanager.ui.camera_widget import CameraWidget


class ScanScreen(Screen):
    def __init__(self, settings, camera_factory=None, **kwargs):
        super().__init__(name="scan", **kwargs)
        self.settings = settings
        self.camera_widget = CameraWidget(
            camera_factory=camera_factory, size_hint=(1, 1)
        )
        self.camera_widget.set_status_callback(self._set_status)

        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(
            Label(text="Scan", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        root.add_widget(self.camera_widget)
        self.status = Label(text="Bereit.")
        root.add_widget(self.status)
        self.add_widget(root)

    def _set_status(self, message):
        self.status.text = message

    def on_enter(self, *args):
        self.camera_widget.start(
            self.settings.get("camera_index", 0),
            self.settings.get("rotation", 0),
        )
        return super().on_enter(*args)

    def on_leave(self, *args):
        self.stop_camera()
        return super().on_leave(*args)

    def stop_camera(self):
        self.camera_widget.stop()
