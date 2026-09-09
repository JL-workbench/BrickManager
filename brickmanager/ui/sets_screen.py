from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

class SetsScreen(Screen):
    def __init__(self, database, **kwargs):
        super().__init__(name="sets", **kwargs)
        self.database = database
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(Label(text="Sets", font_size=dp(26), size_hint_y=None, height=dp(45)))
        root.add_widget(Label(text="Spaeter: Sets, benoetigte Bricks, Fehlmengen und Vollstaendigkeit."))
        button = Button(text="Datenbank pruefen", size_hint_y=None, height=dp(50))
        button.bind(on_release=self.check)
        root.add_widget(button)
        self.status = Label(text="Datenbank initialisiert.")
        root.add_widget(self.status)
        self.add_widget(root)

    def check(self, *_):
        count = self.database.scalar("SELECT COUNT(*) FROM manufacturers")
        self.status.text = f"Datenbank OK - {count} Hersteller vorhanden."
