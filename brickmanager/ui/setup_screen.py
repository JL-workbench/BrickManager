import cv2
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner

class SetupScreen(Screen):
    def __init__(self, settings, **kwargs):
        super().__init__(name="setup", **kwargs)
        self.settings = settings
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(Label(text="Setup", font_size=dp(26), size_hint_y=None, height=dp(45)))
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(110))
        grid.add_widget(Label(text="Kamera"))
        self.camera_spinner = Spinner(text=f"Kamera {settings.get('camera_index',0)}",
                                      values=tuple(f"Kamera {i}" for i in range(6)))
        grid.add_widget(self.camera_spinner)
        grid.add_widget(Label(text="Rotation"))
        self.rotation_spinner = Spinner(text=f"{settings.get('rotation',0)}°",
                                        values=("0°","90°","180°","270°"))
        grid.add_widget(self.rotation_spinner)
        grid.add_widget(Label(text="ROI"))
        grid.add_widget(Label(text="Gesamtes Bild"))
        root.add_widget(grid)
        self.status = Label(text="Kamera wird erst ab v0.2 geoeffnet.")
        root.add_widget(self.status)
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        find = Button(text="Kameras suchen")
        find.bind(on_release=self.find_cameras)
        save = Button(text="Einstellungen speichern")
        save.bind(on_release=self.save_settings)
        buttons.add_widget(find); buttons.add_widget(save)
        root.add_widget(buttons)
        root.add_widget(Label(text="v0.1: GUI-Stabilitaet zuerst, Kamera-Streaming folgt in v0.2."))
        self.add_widget(root)

    def find_cameras(self, *_):
        found = []
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                found.append(i)
                cap.release()
        self.camera_spinner.values = tuple(f"Kamera {i}" for i in found)
        self.status.text = ("Gefundene Kameras: " + ", ".join(map(str, found))) if found else "Keine Kamera gefunden."

    def save_settings(self, *_):
        try:
            self.settings.set("camera_index", int(self.camera_spinner.text.replace("Kamera ","")))
            self.settings.set("rotation", int(self.rotation_spinner.text.replace("°","")))
            self.settings.save()
            self.status.text = "Einstellungen gespeichert."
        except ValueError:
            self.status.text = "Ungueltige Einstellung."
