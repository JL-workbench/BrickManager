import logging
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from settings import Settings
from brickmanager.database.database import Database
from brickmanager.ui.menu import NavigationBar
from brickmanager.ui.setup_screen import SetupScreen
from brickmanager.ui.scan_screen import ScanScreen
from brickmanager.ui.sets_screen import SetsScreen
from brickmanager.ui.history_screen import HistoryScreen

class RootLayout(BoxLayout):
    pass

class BrickManagerApp(App):
    title = "BrickManager"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("BrickManager")
        self.settings = Settings()
        self.database = Database()
        self.database.initialize()

    def build(self):
        root = RootLayout(orientation="vertical")
        navigation = NavigationBar()
        root.add_widget(navigation)
        manager = ScreenManager(transition=FadeTransition(duration=0.15))
        manager.add_widget(SetupScreen(self.settings))
        manager.add_widget(SetsScreen(self.database))
        manager.add_widget(ScanScreen(self.settings))
        manager.add_widget(HistoryScreen(self.database))
        navigation.screen_manager = manager
        root.add_widget(manager)
        self.screen_manager = manager
        return root

    def on_stop(self):
        self.settings.save()
        self.database.close()
