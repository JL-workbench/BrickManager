from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

class HistoryScreen(Screen):
    def __init__(self, database, **kwargs):
        super().__init__(name="history", **kwargs)
        count = database.scalar("SELECT COUNT(*) FROM history")
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(Label(text="History", font_size=dp(26), size_hint_y=None, height=dp(45)))
        root.add_widget(Label(text=f"Erkennungen werden ab v0.8 gespeichert.\nAktuelle Eintraege: {count}"))
        self.add_widget(root)
