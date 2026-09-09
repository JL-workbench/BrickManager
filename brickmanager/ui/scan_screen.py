from datetime import datetime
from pathlib import Path
import threading

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from brickmanager.ui.camera_widget import CameraWidget
from brickmanager.ui.roi_overlay import RoiOverlay
from brickmanager.recognition.brickognize import BrickognizeRecognizer
from brickmanager.recognition.models import RecognitionResult
from brickmanager.vision.image_processing import save_snapshot
from config import SNAPSHOT_DIR


class ScanScreen(Screen):
    def __init__(self, settings, camera_factory=None, recognizer=None, **kwargs):
        super().__init__(name="scan", **kwargs)
        self.settings = settings
        self.recognizer = recognizer or BrickognizeRecognizer()
        self.selected_image_path = None
        self.recognition_running = False
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
        recognition_actions = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        choose_image = Button(text="Bild auswählen")
        choose_image.bind(on_release=self.choose_image)
        recognize = Button(text="Brick erkennen")
        recognize.bind(on_release=self.recognize_image)
        recognition_actions.add_widget(choose_image)
        recognition_actions.add_widget(recognize)
        root.add_widget(recognition_actions)
        self.image_label = Label(
            text="Kein Bild ausgewählt.", size_hint_y=None, height=dp(28)
        )
        root.add_widget(self.image_label)
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
            self.selected_image_path = filename
            self.image_label.text = f"Bild: {filename.name}"
            self.status.text = f"Snapshot gespeichert: {filename.name}"
        else:
            self.status.text = "Snapshot konnte nicht gespeichert werden."

    def choose_image(self, *_):
        chooser = FileChooserListView(
            path=str(Path.cwd()),
            filters=["*.jpg", "*.jpeg", "*.png", "*.bmp"],
            multiselect=False,
        )
        popup = Popup(title="Bild auswählen", content=chooser, size_hint=(0.9, 0.9))
        chooser.bind(
            on_submit=lambda _, selection, __: self._select_image(popup, selection)
        )
        popup.open()

    def _select_image(self, popup, selection):
        if selection:
            self.selected_image_path = Path(selection[0])
            self.image_label.text = f"Bild: {self.selected_image_path.name}"
            self.status.text = "Bild ausgewählt."
            popup.dismiss()

    def recognize_image(self, *_):
        if self.recognition_running:
            return
        if self.selected_image_path is None:
            self.status.text = "Bitte zuerst ein Bild auswählen."
            return

        self.recognition_running = True
        self.status.text = "Brickognize-Erkennung läuft..."
        thread = threading.Thread(target=self._recognize_in_background, daemon=True)
        thread.start()

    def _recognize_in_background(self):
        result = self.recognizer.identify_part(self.selected_image_path)
        Clock.schedule_once(lambda *_: self._display_recognition(result), 0)

    def _display_recognition(self, result: RecognitionResult):
        self.recognition_running = False
        if not result.success:
            self.status.text = f"Brickognize API-Fehler: {result.error}"
            return
        if not result.best_match:
            self.status.text = "Kein LEGO-Teil erkannt."
            return

        best = result.best_match
        lines = [
            f"Part: {best.part_id or '-'}",
            f"Name: {best.name or '-'}",
            f"Confidence: {best.confidence:.2%}",
        ]
        if len(result.results) > 1:
            lines.append(
                "Weitere Treffer: "
                + ", ".join(
                    f"{item.part_id or '-'} ({item.confidence:.2%})"
                    for item in result.results[1:]
                )
            )
        self.status.text = "\n".join(lines)

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
