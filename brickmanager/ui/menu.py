from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

class NavigationBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(54), spacing=dp(5), padding=dp(5), **kwargs)
        self.screen_manager = None
        self.add_widget(Label(text="BrickManager", size_hint_x=1.3))
        for caption, name in (("Setup","setup"),("Sets","sets"),("Scan","scan"),("History","history")):
            button = Button(text=caption)
            button.bind(on_release=lambda _, n=name: self.go_to(n))
            self.add_widget(button)

    def go_to(self, name):
        if self.screen_manager:
            self.screen_manager.current = name
