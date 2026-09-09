import threading

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from brickmanager.services.set_inventory import SetInventoryError


class SetsScreen(Screen):
    def __init__(self, inventory_service, assignment_service, **kwargs):
        super().__init__(name="sets", **kwargs)
        self.inventory_service = inventory_service
        self.assignment_service = assignment_service
        self.root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        self.root.add_widget(
            Label(text="Sets", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        self.add_widget(self.root)
        self.show_set_list()

    def on_enter(self, *args):
        self.show_set_list()
        return super().on_enter(*args)

    def show_set_list(self, *_):
        self.root.clear_widgets()
        self.root.add_widget(
            Label(text="Sets", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        add_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.set_number = TextInput(hint_text="Setnummer, z. B. 10303", multiline=False)
        add_button = Button(text="Set hinzufügen", size_hint_x=None, width=dp(150))
        add_button.bind(on_release=self.add_set)
        add_row.add_widget(self.set_number)
        add_row.add_widget(add_button)
        self.root.add_widget(add_row)
        undo_button = Button(
            text="Letzte Zuordnung rückgängig", size_hint_y=None, height=dp(42)
        )
        undo_button.bind(on_release=self.undo_last_assignment)
        self.root.add_widget(undo_button)
        self.status = Label(text="", size_hint_y=None, height=dp(32))
        self.root.add_widget(self.status)
        self._add_scroll_content(self._build_set_list())

    def add_set(self, *_):
        set_num = self.set_number.text.strip()
        try:
            normalized_set_num = self.inventory_service.client._normalize_set_num(
                set_num
            )
        except SetInventoryError as exc:
            self.status.text = str(exc)
            return
        if any(
            item["set_num"] == normalized_set_num
            for item in self.inventory_service.list_sets()
        ):
            self.status.text = "Set bereits vorhanden"
            return
        self.status.text = "Set und Inventar werden geladen..."
        threading.Thread(
            target=self._load_set_in_background,
            args=(normalized_set_num,),
            daemon=True,
        ).start()

    def _load_set_in_background(self, set_num):
        try:
            set_data, raw_inventory = (
                self.inventory_service.client.fetch_set_with_inventory(set_num)
            )
            inventory = self.inventory_service._parse_inventory(raw_inventory)
            Clock.schedule_once(
                lambda *_: self._store_loaded_set(set_data, inventory), 0
            )
        except SetInventoryError as exc:
            error_message = str(exc)
            Clock.schedule_once(
                lambda _, message=error_message: self._set_status(message), 0
            )

    def _store_loaded_set(self, set_data, inventory):
        try:
            result = self.inventory_service.store_set(set_data, inventory)
        except SetInventoryError as exc:
            self.status.text = str(exc)
            return
        if not result["added"]:
            self.status.text = "Set bereits vorhanden"
            return
        self.status.text = f"Set {result['set_num']} hinzugefügt."
        self.show_set_list()
        self.status.text = f"Set {result['set_num']} hinzugefügt."

    def _build_set_list(self):
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        content.bind(minimum_height=content.setter("height"))
        sets = self.inventory_service.list_sets()
        if not sets:
            content.add_widget(
                Label(
                    text="Noch keine Sets hinzugefügt.", size_hint_y=None, height=dp(44)
                )
            )
            return content
        for index, item in enumerate(sets):
            required = item["quantity_required"]
            found = item["quantity_found"]
            row = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(6))
            if item["set_image_url"]:
                row.add_widget(
                    AsyncImage(
                        source=item["set_image_url"], size_hint_x=None, width=dp(70)
                    )
                )
            else:
                row.add_widget(Label(text="Kein Bild", size_hint_x=None, width=dp(70)))
            details = Button(
                text=f"{index + 1}. {item['set_num']}  {item['name']}\n{found} / {required} Teile gefunden",
                halign="left",
                valign="middle",
            )
            details.bind(
                on_release=lambda _, number=item["set_num"]: self.show_details(number)
            )
            up = Button(text="↑", size_hint_x=None, width=dp(42), disabled=index == 0)
            down = Button(
                text="↓",
                size_hint_x=None,
                width=dp(42),
                disabled=index == len(sets) - 1,
            )
            up.bind(on_release=lambda _, position=index: self.move_set(position, -1))
            down.bind(on_release=lambda _, position=index: self.move_set(position, 1))
            row.add_widget(details)
            row.add_widget(up)
            row.add_widget(down)
            content.add_widget(row)
        return content

    def move_set(self, index, change):
        sets = self.inventory_service.list_sets()
        target = index + change
        if target < 0 or target >= len(sets):
            return
        ordered = [item["set_num"] for item in sets]
        ordered[index], ordered[target] = ordered[target], ordered[index]
        self.inventory_service.set_priority_order(ordered)
        self.show_set_list()

    def show_details(self, set_num):
        set_data = next(
            (
                item
                for item in self.inventory_service.list_sets()
                if item["set_num"] == set_num
            ),
            None,
        )
        if set_data is None:
            return
        self.root.clear_widgets()
        back = Button(text="Zurück zu Sets", size_hint_y=None, height=dp(42))
        back.bind(on_release=self.show_set_list)
        self.root.add_widget(back)
        self.root.add_widget(
            Label(
                text=f"{set_data['set_num']} {set_data['name']}\n"
                f"Gefunden: {set_data['quantity_found']} / {set_data['quantity_required']} Teile",
                size_hint_y=None,
                height=dp(65),
            )
        )
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        content.bind(minimum_height=content.setter("height"))
        for item in self.inventory_service.get_inventory(set_num):
            row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(8))
            if item["part_image_url"]:
                row.add_widget(
                    AsyncImage(
                        source=item["part_image_url"], size_hint_x=None, width=dp(70)
                    )
                )
            else:
                row.add_widget(Label(text="Kein Bild", size_hint_x=None, width=dp(70)))
            remaining = item["quantity_remaining"]
            label = (
                f"Part {item['part_num']} - {item['color_name']}\n"
                f"Benötigt: {item['quantity_required']}    Gefunden: {item['quantity_found']}"
            )
            row.add_widget(
                Label(text=label + ("  ✓" if remaining == 0 else ""), halign="left")
            )
            content.add_widget(row)
        self._add_scroll_content(content)

    def undo_last_assignment(self, *_):
        result = self.assignment_service.undo_last_assignment()
        self.status.text = (
            "Letzte Zuordnung rückgängig gemacht."
            if result["undone"]
            else "Keine Zuordnung zum Rückgängigmachen vorhanden."
        )
        self.show_set_list()
        self.status.text = (
            "Letzte Zuordnung rückgängig gemacht."
            if result["undone"]
            else "Keine Zuordnung zum Rückgängigmachen vorhanden."
        )

    def _add_scroll_content(self, content):
        scroll = ScrollView()
        scroll.add_widget(content)
        self.root.add_widget(scroll)

    def _set_status(self, message):
        self.status.text = message
