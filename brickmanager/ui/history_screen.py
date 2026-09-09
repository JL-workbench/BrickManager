from datetime import datetime

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen


class HistoryScreen(Screen):
    def __init__(self, assignment_service, **kwargs):
        super().__init__(name="history", **kwargs)
        self.assignment_service = assignment_service
        self.root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        self.add_widget(self.root)
        self.refresh()

    def on_enter(self, *args):
        self.refresh()
        return super().on_enter(*args)

    def refresh(self, *_):
        self.root.clear_widgets()
        self.root.add_widget(
            Label(text="History", font_size=dp(26), size_hint_y=None, height=dp(45))
        )
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        content.bind(minimum_height=content.setter("height"))
        entries = self.assignment_service.list_history()
        if not entries:
            content.add_widget(
                Label(
                    text="Noch keine gefundenen Teile.", size_hint_y=None, height=dp(44)
                )
            )
        for entry in entries:
            content.add_widget(self._build_history_row(entry))
        scroll = ScrollView()
        scroll.add_widget(content)
        self.root.add_widget(scroll)

    def _build_history_row(self, entry):
        row = BoxLayout(size_hint_y=None, height=dp(82), spacing=dp(8))
        if entry["image_path"]:
            row.add_widget(
                Image(source=entry["image_path"], size_hint_x=None, width=dp(70))
            )
        details = (
            f"{entry['part_num']} - {entry['color_name'] or 'Unbekannt'} (Color-ID: {entry['color_id']})\n"
            f"Gefunden: {self._format_timestamp(entry['timestamp'])}\n"
            f"Einsortiert: {entry['assigned_set_num'] or 'Kein Bedarf'}"
        )
        row.add_widget(Label(text=details, halign="left", valign="middle"))
        button = Button(text="Neu zuordnen", size_hint_x=None, width=dp(125))
        button.bind(on_release=lambda _, scan=entry: self.show_reassignment(scan))
        row.add_widget(button)
        return row

    def show_reassignment(self, entry):
        targets = self.assignment_service.get_reassignment_targets(entry["scan_id"])
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        content.add_widget(
            Label(
                text=f"{entry['part_num']} - {entry['color_name'] or 'Unbekannt'}\nIn folgenden Sets benötigt:",
                size_hint_y=None,
                height=dp(52),
            )
        )
        popup = Popup(title="Teil neu zuordnen", content=content, size_hint=(0.85, 0.8))
        if not targets:
            content.add_widget(Label(text="Kein passendes Set vorhanden."))
        for target in targets:
            status = "Aktuell" if target["is_current"] else ""
            if target["quantity_found"] >= target["quantity_required"]:
                status = f"{status} Vollständig".strip()
            button = Button(
                text=f"{target['set_num']} {target['name']}\n{target['quantity_found']} / {target['quantity_required']} {status}".strip(),
                size_hint_y=None,
                height=dp(62),
            )
            button.bind(
                on_release=lambda _, set_id=target["set_id"]: (
                    self._reassign_and_refresh(popup, entry["scan_id"], set_id)
                )
            )
            content.add_widget(button)
        cancel = Button(text="Abbrechen", size_hint_y=None, height=dp(44))
        cancel.bind(on_release=popup.dismiss)
        content.add_widget(cancel)
        popup.open()

    def _reassign_and_refresh(self, popup, scan_id, target_set_id):
        self.assignment_service.reassign_part(scan_id, target_set_id)
        popup.dismiss()
        self.refresh()

    @staticmethod
    def _format_timestamp(timestamp):
        try:
            return datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            return timestamp or "-"
