import threading

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner

from brickmanager.vision.camera import OpenCVCamera


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
            self.settings.save()
            self.status.text = "Einstellungen gespeichert."
        except ValueError:
            self.status.text = "Ungueltige Einstellung."
