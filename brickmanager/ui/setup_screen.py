import threading

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from brickmanager.vision.camera import OpenCVCamera
from brickmanager.services.lego_color_database import ColorDatabase, ColorDatabaseError
from config import LEGO_COLORS_FILE


class SetupScreen(Screen):
    def __init__(self, settings, camera_factory=None, **kwargs):
        super().__init__(name="setup", **kwargs)
        self.settings = settings
        self.camera_factory = camera_factory or OpenCVCamera
        self.is_searching = False
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(
            Label(text="Setup", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(110))
        grid.add_widget(Label(text="Kamera"))
        current_index = int(settings.get("camera_index", 0))
        self.camera_spinner = Spinner(
            text=f"Kamera {current_index}",
            values=tuple(f"Kamera {i}" for i in range(6)),
        )
        grid.add_widget(self.camera_spinner)
        grid.add_widget(Label(text="Rotation"))
        self.rotation_spinner = Spinner(
            text=f"{settings.get('rotation', 0)}°", values=("0°", "90°", "180°", "270°")
        )
        grid.add_widget(self.rotation_spinner)
        grid.add_widget(Label(text="ROI"))
        grid.add_widget(Label(text="Gesamtes Bild"))
        root.add_widget(grid)
        auto_scan_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.auto_scan_checkbox = CheckBox(
            active=settings.get("auto_scan_enabled", False)
        )
        self.auto_scan_checkbox.bind(active=self._save_auto_scan_enabled)
        auto_scan_row.add_widget(self.auto_scan_checkbox)
        auto_scan_row.add_widget(Label(text="Auto-Scan aktivieren"))
        interval_down = Button(text="−", size_hint_x=None, width=dp(42))
        interval_down.bind(on_release=lambda *_: self._change_auto_scan_interval(-1))
        auto_scan_row.add_widget(interval_down)
        self.auto_scan_interval = Label(
            text=self._format_auto_scan_interval(
                settings.get("auto_scan_interval", 2.0)
            ),
            size_hint_x=None,
            width=dp(62),
        )
        auto_scan_row.add_widget(self.auto_scan_interval)
        interval_up = Button(text="+", size_hint_x=None, width=dp(42))
        interval_up.bind(on_release=lambda *_: self._change_auto_scan_interval(1))
        auto_scan_row.add_widget(interval_up)
        root.add_widget(auto_scan_row)
        filter_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.all_colors_checkbox = CheckBox(
            active=not settings.get("color_filter_enabled", False)
        )
        self.all_colors_checkbox.bind(active=self._set_all_colors)
        filter_row.add_widget(self.all_colors_checkbox)
        filter_row.add_widget(Label(text="Alle Farben"))
        edit_colors = Button(text="Farben bearbeiten", size_hint_x=None, width=dp(150))
        edit_colors.bind(on_release=self.show_color_selection)
        filter_row.add_widget(edit_colors)
        root.add_widget(Label(text="Farbfilter", size_hint_y=None, height=dp(28)))
        root.add_widget(filter_row)
        self.filter_summary = Label(size_hint_y=None, height=dp(28))
        root.add_widget(self.filter_summary)
        sort_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.sort_filtered_checkbox = CheckBox(
            active=settings.get("sort_filtered_parts", False)
        )
        sort_row.add_widget(self.sort_filtered_checkbox)
        sort_row.add_widget(
            Label(text="Teile außerhalb des Filters trotzdem einsortieren")
        )
        root.add_widget(sort_row)
        self._update_filter_summary()
        self.status = Label(text="Kamera wird erst nach Aktivierung geöffnet.")
        root.add_widget(self.status)
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.find_button = Button(text="Kameras suchen")
        self.find_button.bind(on_release=self.find_cameras)
        save = Button(text="Einstellungen speichern")
        save.bind(on_release=self.save_settings)
        buttons.add_widget(self.find_button)
        buttons.add_widget(save)
        root.add_widget(buttons)
        root.add_widget(
            Label(
                text="v0.2: Live-Bild, Kameraauswahl und Rotation werden aktiv geschaltet."
            )
        )
        self.add_widget(root)

    def find_cameras(self, *_):
        if self.is_searching:
            return

        self.is_searching = True
        self.find_button.disabled = True
        self.status.text = "Kameras werden gesucht..."

        thread = threading.Thread(target=self._discover_cameras_async, daemon=True)
        thread.start()

    def _discover_cameras_async(self):
        found = self.camera_factory.enumerate_devices(9)
        Clock.schedule_once(lambda *_: self._apply_camera_results(found), 0)

    def _apply_camera_results(self, found):
        self.is_searching = False
        self.find_button.disabled = False
        self.camera_spinner.values = tuple(f"Kamera {i}" for i in found) or (
            f"Kamera {int(self.settings.get('camera_index', 0))}",
        )
        if found:
            current = self.settings.get("camera_index", 0)
            if current not in found:
                current = found[0]
            self.camera_spinner.text = f"Kamera {current}"
            self.status.text = "Gefundene Kameras: " + ", ".join(f"{i}" for i in found)
        else:
            self.status.text = "Keine Kamera gefunden."

    def save_settings(self, *_):
        try:
            camera_text = self.camera_spinner.text.strip()
            camera_index = int(camera_text.replace("Kamera ", ""))
            rotation = int(self.rotation_spinner.text.replace("°", ""))
            if rotation not in (0, 90, 180, 270):
                raise ValueError
            self.settings.set("camera_index", camera_index)
            self.settings.set("rotation", rotation)
            self.settings.set("auto_scan_enabled", self.auto_scan_checkbox.active)
            self.settings.set(
                "auto_scan_interval",
                self._auto_scan_interval_seconds(),
            )
            self.settings.set(
                "color_filter_enabled", not self.all_colors_checkbox.active
            )
            self.settings.set("sort_filtered_parts", self.sort_filtered_checkbox.active)
            self.settings.save()
            self._update_filter_summary()
            self.status.text = "Einstellungen gespeichert."
        except ValueError:
            self.status.text = "Ungueltige Einstellung."

    def _save_auto_scan_enabled(self, _, enabled):
        self.settings.set("auto_scan_enabled", bool(enabled))
        self.settings.save()

    @staticmethod
    def _format_auto_scan_interval(interval):
        return f"{float(interval):.1f} s"

    def _auto_scan_interval_seconds(self):
        return float(self.auto_scan_interval.text.replace(" s", ""))

    def _change_auto_scan_interval(self, delta):
        interval = max(0.5, self._auto_scan_interval_seconds() + float(delta))
        self.auto_scan_interval.text = self._format_auto_scan_interval(interval)
        self.settings.set("auto_scan_interval", interval)
        self.settings.save()

    def show_color_selection(self, *_):
        try:
            colors = ColorDatabase(LEGO_COLORS_FILE).load()
        except ColorDatabaseError:
            self.status.text = "Lokaler Rebrickable-Farbkatalog nicht verfügbar."
            return
        selected = {
            int(color_id) for color_id in self.settings.get("selected_color_ids", [])
        }
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))
        choices = GridLayout(cols=2, size_hint_y=None, spacing=dp(4))
        choices.bind(minimum_height=choices.setter("height"))
        checkboxes = {}
        for color in sorted(colors, key=lambda item: item.name):
            checkbox = CheckBox(
                active=color.color_id in selected, size_hint_x=None, width=dp(36)
            )
            checkboxes[color.color_id] = checkbox
            choices.add_widget(checkbox)
            choices.add_widget(
                Label(
                    text=f"{color.name} ({color.color_id})",
                    size_hint_y=None,
                    height=dp(32),
                )
            )
        scroll = ScrollView()
        scroll.add_widget(choices)
        content.add_widget(scroll)
        save = Button(text="Farbauswahl übernehmen", size_hint_y=None, height=dp(44))
        content.add_widget(save)
        popup = Popup(title="Farben auswählen", content=content, size_hint=(0.8, 0.8))
        save.bind(on_release=lambda _: self._save_color_selection(popup, checkboxes))
        popup.open()

    def _save_color_selection(self, popup, checkboxes):
        selected = [
            color_id for color_id, checkbox in checkboxes.items() if checkbox.active
        ]
        self.settings.set("selected_color_ids", selected)
        self.all_colors_checkbox.active = not bool(selected)
        self.settings.set("color_filter_enabled", bool(selected))
        self.settings.save()
        self._update_filter_summary()
        popup.dismiss()

    def _set_all_colors(self, _, active):
        if not active:
            return
        self.settings.set("color_filter_enabled", False)
        self.settings.set("selected_color_ids", [])
        self.settings.save()
        self._update_filter_summary()

    def _update_filter_summary(self):
        if self.all_colors_checkbox.active:
            self.filter_summary.text = "Aktiv: Alle Farben"
            return
        selected = self.settings.get("selected_color_ids", [])
        self.filter_summary.text = f"Aktiv: {len(selected)} Farbe(n) ausgewählt"
