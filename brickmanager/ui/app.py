import logging

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager

from settings import Settings
from brickmanager.database.database import Database
from brickmanager.ui.history_screen import HistoryScreen
from brickmanager.ui.menu import NavigationBar
from brickmanager.ui.scan_screen import ScanScreen
from brickmanager.ui.sets_screen import SetsScreen
from brickmanager.ui.setup_screen import SetupScreen
from brickmanager.recognition.brickognize import BrickognizeRecognizer
from brickmanager.vision.camera import OpenCVCamera


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
        self.camera_factory = OpenCVCamera
        self.recognizer = BrickognizeRecognizer()

    def build(self):
        root = RootLayout(orientation="vertical")
        navigation = NavigationBar()
        root.add_widget(navigation)
        manager = ScreenManager(transition=FadeTransition(duration=0.15))
        manager.add_widget(
            SetupScreen(self.settings, camera_factory=self.camera_factory)
        )
        manager.add_widget(SetsScreen(self.database))
        manager.add_widget(
            ScanScreen(
                self.settings,
                camera_factory=self.camera_factory,
                recognizer=self.recognizer,
            )
        )
        manager.add_widget(HistoryScreen(self.database))
        navigation.screen_manager = manager
        root.add_widget(manager)
        self.screen_manager = manager
        return root

    def on_stop(self):
        if getattr(self, "screen_manager", None) is not None:
            for screen in self.screen_manager.screens:
                if hasattr(screen, "stop_camera"):
                    screen.stop_camera()
        self.settings.save()
        self.database.close()
