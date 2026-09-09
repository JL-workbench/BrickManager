import threading
from datetime import datetime, timezone
from pathlib import Path

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from brickmanager.recognition.brickognize import BrickognizeRecognizer
from brickmanager.recognition.models import RecognitionResult
from brickmanager.ui.camera_widget import CameraWidget
from brickmanager.ui.roi_overlay import RoiOverlay
from brickmanager.vision.image_processing import save_snapshot
from brickmanager.vision.image_processing import prepare_snapshot_frame
from brickmanager.vision.color_detection import create_background_reference
from brickmanager.vision.recognition_processing import enrich_recognition
from config import SNAPSHOT_DIR


class ScanScreen(Screen):
    def __init__(self, settings, camera_factory=None, recognizer=None, **kwargs):
        super().__init__(name="scan", **kwargs)
        self.settings = settings
        self.recognizer = recognizer or BrickognizeRecognizer()
        self.selected_image_path = None
        self.recognition_running = False
        self.background_reference = None
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
        controls = BoxLayout(
            orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(162)
        )
        left_controls = BoxLayout(orientation="vertical", size_hint_x=0.5)
        roi_actions = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(104), spacing=dp(6)
        )
        save_roi = Button(text="ROI speichern", size_hint_y=None, height=dp(49))
        save_roi.bind(on_release=self.save_roi)
        reset_roi = Button(text="ROI zurücksetzen", size_hint_y=None, height=dp(49))
        reset_roi.bind(on_release=self.reset_roi)
        roi_actions.add_widget(save_roi)
        roi_actions.add_widget(reset_roi)
        left_controls.add_widget(roi_actions)
        controls.add_widget(left_controls)

        right_controls = BoxLayout(orientation="vertical", size_hint_x=0.5)
        recognition_actions = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(162), spacing=dp(6)
        )
        snapshot = Button(text="Snapshot", size_hint_y=None, height=dp(50))
        snapshot.bind(on_release=self.take_snapshot)
        snapshot_and_recognize = Button(
            text="Snapshot und erkennen", size_hint_y=None, height=dp(50)
        )
        snapshot_and_recognize.bind(on_release=self.snapshot_and_recognize)
        choose_image = Button(
            text="Bild auswählen und erkennen", size_hint_y=None, height=dp(50)
        )
        choose_image.bind(on_release=self.choose_image)
        recognition_actions.add_widget(snapshot)
        recognition_actions.add_widget(snapshot_and_recognize)
        recognition_actions.add_widget(choose_image)
        right_controls.add_widget(recognition_actions)
        controls.add_widget(right_controls)
        root.add_widget(controls)

        image_row = BoxLayout(orientation="horizontal", spacing=dp(8))
        live_preview = FloatLayout(size_hint_x=0.5)
        live_preview.add_widget(self.camera_widget)
        live_preview.add_widget(self.roi_overlay)
        image_row.add_widget(live_preview)

        self.selected_image_preview = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint_x=0.5,
        )
        image_row.add_widget(self.selected_image_preview)
        root.add_widget(image_row)

        image_info = BoxLayout(
            orientation="horizontal", spacing=dp(8), size_hint_y=None
        )
        image_info.add_widget(Widget(size_hint_x=0.5))
        self.image_label = Label(
            text="Kein Bild ausgewählt.",
            size_hint_y=None,
            height=dp(44),
            size_hint_x=0.5,
            halign="left",
            valign="middle",
        )
        self.image_label.bind(size=self._update_image_label_text_size)
        image_info.add_widget(self.image_label)
        root.add_widget(image_info)
        self.camera_widget.bind(
            pos=self._update_roi_display_rect,
            size=self._update_roi_display_rect,
            texture_size=self._update_roi_display_rect,
        )
        self.status = Label(text="Bereit.")
        root.add_widget(self.status)
        self.add_widget(root)

    def _set_status(self, message):
        self.status.text = message

    def _update_image_label_text_size(self, *_):
        self.image_label.text_size = self.image_label.size

    def _roi_changed(self, roi):
        self.current_roi = dict(roi)

    def _update_roi_display_rect(self, *_):
        self.roi_overlay.set_display_rect(self.camera_widget.get_display_rect())

    def save_roi(self, *_):
        self.settings.set("roi", dict(self.current_roi))
        self.settings.save()
        frame = self.camera_widget.get_latest_frame()
        if frame is None:
            self.background_reference = None
            self.status.text = "ROI gespeichert, Referenzbild nicht verfügbar."
            return
        self.status.text = "ROI ausgewählt. Referenzbild wird aufgenommen..."
        reference_frame = prepare_snapshot_frame(
            frame, self.camera_widget.rotation, self.current_roi
        )
        self.background_reference = create_background_reference(reference_frame)
        if self.background_reference is None:
            self.status.text = "Referenzbild konnte nicht aufgenommen werden."
            return
        self.status.text = "Referenzbild aufgenommen. LEGO-Teil analysierbar."

    def reset_roi(self, *_):
        self.current_roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        self.roi_overlay.set_roi(self.current_roi)
        self.status.text = "ROI zurückgesetzt."

    def take_snapshot(self, *_):
        frame = self.camera_widget.get_latest_frame()
        if frame is None:
            self.status.text = "Noch kein Kamerabild verfügbar."
            return None
        filename = (
            SNAPSHOT_DIR / f"snapshot_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.jpg"
        )
        if save_snapshot(
            frame, filename, self.camera_widget.rotation, self.current_roi
        ):
            self._set_selected_image(filename)
            self.image_label.text = (
                f"Bild: {filename.name}\nSnapshot gespeichert: {filename.name}"
            )
            self.status.text = "Snapshot bereit."
            return filename
        else:
            self.status.text = "Snapshot konnte nicht gespeichert werden."
            return None

    def snapshot_and_recognize(self, *_):
        image_path = self.take_snapshot()
        if image_path is not None:
            self._start_recognition(image_path)

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
            image_path = Path(selection[0])
            self._set_selected_image(image_path)
            popup.dismiss()
            self._start_recognition(image_path)

    def _set_selected_image(self, image_path):
        self.selected_image_path = Path(image_path)
        self.selected_image_preview.source = str(self.selected_image_path)
        self.selected_image_preview.reload()
        self.image_label.text = f"Bild: {self.selected_image_path.name}"

    def _start_recognition(self, image_path):
        if self.recognition_running:
            return

        self.recognition_running = True
        self.status.text = "Brickognize-Erkennung läuft..."
        thread = threading.Thread(
            target=self._recognize_in_background,
            args=(Path(image_path),),
            daemon=True,
        )
        thread.start()

    def recognize_image(self, *_):
        if self.selected_image_path is None:
            self.status.text = "Bitte zuerst ein Bild auswählen."
            return
        self._start_recognition(self.selected_image_path)

    def _recognize_in_background(self, image_path):
        result = self.recognizer.identify_part(image_path)
        result, debug_path = enrich_recognition(
            image_path, result, reference=self.background_reference
        )
        Clock.schedule_once(lambda *_: self._display_recognition(result, debug_path), 0)

    def _display_recognition(self, result: RecognitionResult, debug_path=None):
        self.recognition_running = False
        if not result.success:
            self.status.text = f"Brickognize API-Fehler: {result.error}"
            return
        if not result.best_match:
            self.status.text = "Kein LEGO-Teil erkannt."
            return

        best = result.best_match
        if debug_path is not None:
            self.selected_image_preview.source = str(debug_path)
            self.selected_image_preview.reload()
        lines = [
            f"Part: {best.part_id or '-'}",
            f"Name: {best.name or '-'}",
            f"Confidence: {best.confidence:.2%}",
        ]
        if best.bounding_box is not None:
            box = best.bounding_box
            lines.append(
                f"Bounding Box: x={box.x:.0f}, y={box.y:.0f}, "
                f"width={box.width:.0f}, height={box.height:.0f}"
            )
        else:
            lines.append("Bounding Box: nicht verfügbar")
        if best.color is not None:
            lines.append(f"Farbe: RGB {best.color.rgb}, {best.color.hex}")
        if result.color_error is not None:
            lines.append(f"Farbanalyse: {result.color_error}")
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
