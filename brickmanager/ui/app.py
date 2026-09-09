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
from brickmanager.services.set_inventory import (
    PartAssignmentService,
    RebrickableSetClient,
    SetInventoryService,
)
from brickmanager.services.rebrickable_cache_service import RebrickableCacheService
from config import REBRICKABLE_CACHE_FILE
from brickmanager.vision.camera import get_camera_factory


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
        self.camera_factory = get_camera_factory()
        self.recognizer = BrickognizeRecognizer()
        self.rebrickable_cache_service = RebrickableCacheService(REBRICKABLE_CACHE_FILE)
        self.set_inventory_service = SetInventoryService(
            self.database,
            client=RebrickableSetClient(cache_service=self.rebrickable_cache_service),
        )
        self.part_assignment_service = PartAssignmentService(self.database)

    def build(self):
        root = RootLayout(orientation="vertical")
        navigation = NavigationBar()
        root.add_widget(navigation)
        manager = ScreenManager(transition=FadeTransition(duration=0.15))
        manager.add_widget(
            SetupScreen(self.settings, camera_factory=self.camera_factory)
        )
        manager.add_widget(
            SetsScreen(
                self.set_inventory_service, self.part_assignment_service, self.settings
            )
        )
        manager.add_widget(
            ScanScreen(
                self.settings,
                camera_factory=self.camera_factory,
                recognizer=self.recognizer,
                assignment_service=self.part_assignment_service,
            )
        )
        manager.add_widget(HistoryScreen(self.part_assignment_service, self.settings))
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
        self.rebrickable_cache_service.close()
        self.database.close()
