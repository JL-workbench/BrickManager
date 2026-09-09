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
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from brickmanager.recognition.brickognize import BrickognizeRecognizer
from brickmanager.recognition.models import RecognitionResult
from brickmanager.ui.camera_widget import CameraWidget
from brickmanager.ui.roi_overlay import RoiOverlay
from brickmanager.vision.image_processing import save_snapshot
from brickmanager.vision.image_processing import prepare_snapshot_frame
from brickmanager.vision.color_detection import (
    create_background_reference,
    load_background_reference,
    save_background_reference,
)
from brickmanager.vision.recognition_processing import enrich_recognition
from brickmanager.vision.auto_scan import AutoScanController, AutoScanState
from brickmanager.services.color_filter import color_is_visible, sort_filtered_parts
from config import BACKGROUND_REFERENCE_FILE, SNAPSHOT_DIR


class ScanScreen(Screen):
    def __init__(
        self,
        settings,
        camera_factory=None,
        recognizer=None,
        assignment_service=None,
        **kwargs,
    ):
        super().__init__(name="scan", **kwargs)
        self.settings = settings
        self.recognizer = recognizer or BrickognizeRecognizer()
        self.assignment_service = assignment_service
        self.selected_image_path = None
        self.recognition_running = False
        self.background_reference = None
        self.auto_scan_controller = AutoScanController()
        self._auto_scan_event = None
        self._auto_scan_progress_event = None
        self._auto_scan_elapsed = 0.0
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
        self.auto_scan_progress = ProgressBar(
            max=1.0, value=0, size_hint_y=None, height=dp(16)
        )
        self.auto_scan_progress.opacity = 0
        root.add_widget(self.auto_scan_progress)
        self.auto_scan_progress_label = Label(
            text="", size_hint_y=None, height=dp(22)
        )
        root.add_widget(self.auto_scan_progress_label)
        self.auto_scan_status = Label(text="", size_hint_y=None, height=dp(24))
        root.add_widget(self.auto_scan_status)
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
        if not save_background_reference(self.background_reference, BACKGROUND_REFERENCE_FILE):
            self.status.text = "Referenzbild konnte nicht gespeichert werden."
            return
        self.status.text = "Referenzbild aufgenommen. LEGO-Teil analysierbar."
        self._start_auto_scan()

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

    def _start_auto_scan(self):
        self._stop_auto_scan()
        if not self.settings.get("auto_scan_enabled", False):
            return
        if self.background_reference is None or self.camera_widget.camera is None:
            if self.background_reference is None:
                self.auto_scan_status.text = (
                    "Auto-Scan wartet: Leeren ROI anzeigen und 'ROI speichern' drücken."
                )
            else:
                self.auto_scan_status.text = "Auto-Scan wartet auf die Kamera."
            return
        interval = float(self.settings.get("auto_scan_interval", 2.0))
        self.auto_scan_controller.reset()
        self._auto_scan_elapsed = 0.0
        self.auto_scan_progress.max = interval
        self.auto_scan_progress.value = 0
        self.auto_scan_progress.opacity = 1
        self.auto_scan_progress_label.text = (
            f"Nächste Prüfung: 0.0 / {interval:.1f} s"
        )
        self.auto_scan_status.text = "Auto-Scan aktiv: Warte auf Bauteil ..."
        self._auto_scan_event = Clock.schedule_interval(self._check_auto_scan, interval)
        self._auto_scan_progress_event = Clock.schedule_interval(
            self._update_auto_scan_progress, 0.05
        )

    def _stop_auto_scan(self):
        for event_name in ("_auto_scan_event", "_auto_scan_progress_event"):
            event = getattr(self, event_name, None)
            if event is not None:
                event.cancel()
                setattr(self, event_name, None)
        self.auto_scan_progress.opacity = 0
        self.auto_scan_progress_label.text = ""
        self.auto_scan_status.text = ""

    def _update_auto_scan_progress(self, delta):
        interval = float(self.settings.get("auto_scan_interval", 2.0))
        if self.recognition_running:
            return
        self._auto_scan_elapsed = min(interval, self._auto_scan_elapsed + delta)
        self.auto_scan_progress.value = self._auto_scan_elapsed
        self.auto_scan_progress_label.text = (
            f"Nächste Prüfung: {self._auto_scan_elapsed:.1f} / {interval:.1f} s"
        )

    def _check_auto_scan(self, _):
        self._auto_scan_elapsed = 0.0
        if self.recognition_running or self.background_reference is None:
            return
        frame = self.camera_widget.get_latest_frame()
        if frame is None:
            return
        current_roi = prepare_snapshot_frame(
            frame, self.camera_widget.rotation, self.current_roi
        )
        if self.auto_scan_controller.process_frame(
            self.background_reference.image, current_roi, self.recognition_running
        ):
            self.auto_scan_status.text = "Bauteil erkannt. Scan wird durchgeführt ..."
            filename = (
                SNAPSHOT_DIR / f"auto_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.jpg"
            )
            if save_snapshot(
                frame, filename, self.camera_widget.rotation, self.current_roi
            ):
                self._set_selected_image(filename)
                self._start_recognition(filename)
            else:
                self.auto_scan_controller.scan_failed()
                self.auto_scan_status.text = (
                    "Auto-Scan: Snapshot fehlgeschlagen. Warte auf Entfernung ..."
                )
        elif self.auto_scan_controller.state == AutoScanState.SCANNING:
            self.auto_scan_status.text = "Bauteil erkannt. Scan wird durchgefuehrt ..."
        elif self.auto_scan_controller.state == AutoScanState.WAITING_FOR_REMOVAL:
            self.auto_scan_status.text = (
                "Bauteil liegt noch im ROI. Warte auf Entfernung ..."
            )
        else:
            ratio = self.auto_scan_controller.last_changed_ratio * 100
            minimum = self.auto_scan_controller.min_changed_ratio * 100
            motion = self.auto_scan_controller.last_motion_ratio * 100
            maximum_motion = self.auto_scan_controller.max_motion_ratio * 100
            if ratio >= minimum and motion > maximum_motion:
                self.auto_scan_status.text = (
                    "Bauteilbewegung erkannt. Warte auf stabiles Bild ... "
                    f"Bewegung: {motion:.1f}%"
                )
            else:
                self.auto_scan_status.text = (
                    "Auto-Scan aktiv: Warte auf Bauteil ... "
                    f"ROI-Änderung: {ratio:.1f}% (Auslösung ab {minimum:.1f}%)"
                )

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
        self.auto_scan_controller.scan_completed()
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
        if best.lego_color is not None:
            lego_color = best.lego_color
            lines.append(f"LEGO-Farbe: {lego_color.name} (ID: {lego_color.color_id})")
            element_id = getattr(lego_color, "element_id", None)
            element_ids = getattr(lego_color, "element_ids", ())
            all_element_ids = list(
                dict.fromkeys(filter(None, (element_id, *element_ids)))
            )
            lines.append(f"LEGO Element-ID: {', '.join(all_element_ids) or '?'}")
            if self.assignment_service is not None and best.part_id:
                try:
                    is_visible = color_is_visible(self.settings, lego_color.color_id)
                    assignment = self.assignment_service.assign_part(
                        best.part_id,
                        lego_color.color_id,
                        confidence=best.confidence,
                        delta_e=lego_color.delta_e,
                        lego_element_id=element_id,
                        color_name=lego_color.name,
                        image_path=self.selected_image_path,
                        allow_assignment=is_visible
                        or sort_filtered_parts(self.settings),
                    )
                    if not is_visible:
                        lines.append("Farbe nicht im Filter")
                        self._show_filtered_color_notice(lego_color.name)
                    if assignment["assigned"]:
                        lines.append(
                            f"Zuordnung: {best.part_id} - {lego_color.name} -> Set {assignment['set_num']}"
                        )
                    else:
                        lines.append("Zuordnung: Kein Bedarf in den aktiven Sets")
                except (OSError, RuntimeError, TypeError, ValueError):
                    lines.append("Zuordnung: nicht verfügbar")
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
        if self.settings.get("auto_scan_enabled", False):
            self.auto_scan_status.text = "Scan abgeschlossen. Warte auf Entfernung ..."

    def _show_filtered_color_notice(self, color_name):
        message = (
            f"Das erkannte Bauteil hat die Farbe: {color_name}\n"
            "Diese Farbe ist aktuell nicht ausgewählt."
        )
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        content.add_widget(Label(text=message))
        dismiss = Button(text="OK", size_hint_y=None, height=dp(42))
        content.add_widget(dismiss)
        popup = Popup(
            title="Farbe nicht im Filter",
            content=content,
            size_hint=(0.75, None),
            height=dp(180),
        )
        dismiss.bind(on_release=popup.dismiss)
        popup.open()

    def on_enter(self, *args):
        self.current_roi = dict(self.settings.get("roi", self.current_roi))
        self.roi_overlay.set_roi(self.current_roi)
        self.camera_widget.start(
            self.settings.get("camera_index", 0),
            self.settings.get("rotation", 0),
        )
        self.background_reference = load_background_reference(BACKGROUND_REFERENCE_FILE)
        self._start_auto_scan()
        return super().on_enter(*args)

    def on_leave(self, *args):
        self._stop_auto_scan()
        self.stop_camera()
        return super().on_leave(*args)

    def stop_camera(self):
        self._stop_auto_scan()
        self.camera_widget.stop()
