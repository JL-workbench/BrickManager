from kivy.metrics import dp
from datetime import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from brickmanager.ui.camera_widget import CameraWidget
from brickmanager.ui.roi_overlay import RoiOverlay
from brickmanager.vision.image_processing import save_snapshot
from config import SNAPSHOT_DIR


class ScanScreen(Screen):
    def __init__(self, settings, camera_factory=None, **kwargs):
        super().__init__(name="scan", **kwargs)
        self.settings = settings
        self.camera_widget = CameraWidget(
            camera_factory=camera_factory, size_hint=(1, 1)
        )
        self.camera_widget.set_status_callback(self._set_status)
        self.current_roi = dict(
            settings.get("roi", {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0})
        )
        self.roi_overlay = RoiOverlay(roi=self.current_roi, on_change=self._roi_changed)

        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(
            Label(text="Scan", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        preview = FloatLayout()
        preview.add_widget(self.camera_widget)
        preview.add_widget(self.roi_overlay)
        self.camera_widget.bind(
            pos=self._update_roi_display_rect,
            size=self._update_roi_display_rect,
            texture_size=self._update_roi_display_rect,
        )
        root.add_widget(preview)
        actions = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save_roi = Button(text="ROI speichern")
        save_roi.bind(on_release=self.save_roi)
        reset_roi = Button(text="ROI zurücksetzen")
        reset_roi.bind(on_release=self.reset_roi)
        snapshot = Button(text="Snapshot aufnehmen")
        snapshot.bind(on_release=self.take_snapshot)
        actions.add_widget(save_roi)
        actions.add_widget(reset_roi)
        actions.add_widget(snapshot)
        root.add_widget(actions)
        self.status = Label(text="Bereit.")
        root.add_widget(self.status)
        self.add_widget(root)

    def _set_status(self, message):
        self.status.text = message

    def _roi_changed(self, roi):
        self.current_roi = dict(roi)

    def _update_roi_display_rect(self, *_):
        self.roi_overlay.set_display_rect(self.camera_widget.get_display_rect())

    def save_roi(self, *_):
        self.settings.set("roi", dict(self.current_roi))
        self.settings.save()
        self.status.text = "ROI gespeichert."

    def reset_roi(self, *_):
        self.current_roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        self.roi_overlay.set_roi(self.current_roi)
        self.status.text = "ROI zurückgesetzt."

    def take_snapshot(self, *_):
        frame = self.camera_widget.get_latest_frame()
        if frame is None:
            self.status.text = "Noch kein Kamerabild verfügbar."
            return
        filename = SNAPSHOT_DIR / f"snapshot_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        if save_snapshot(
            frame, filename, self.camera_widget.rotation, self.current_roi
        ):
            self.status.text = f"Snapshot gespeichert: {filename.name}"
        else:
            self.status.text = "Snapshot konnte nicht gespeichert werden."

    def on_enter(self, *args):
        self.current_roi = dict(self.settings.get("roi", self.current_roi))
        self.roi_overlay.set_roi(self.current_roi)
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
