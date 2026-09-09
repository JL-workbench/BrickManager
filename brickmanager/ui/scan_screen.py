from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

class ScanScreen(Screen):
    def __init__(self, settings, **kwargs):
        super().__init__(name="scan", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(Label(text="Scan", font_size=dp(26), size_hint_y=None, height=dp(45)))
        root.add_widget(Label(text="Kameraansicht folgt in v0.2.\nFotoaufnahme in v0.3, Erkennung danach."))
        button = Button(text="Test-Snapshot", size_hint_y=None, height=dp(50))
        button.bind(on_release=lambda *_: setattr(self.status, "text", "Snapshot ist fuer v0.3 vorgesehen."))
        root.add_widget(button)
        self.status = Label(text="Bereit.")
        root.add_widget(self.status)
        self.add_widget(root)
