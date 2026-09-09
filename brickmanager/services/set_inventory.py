import os

import requests


REBRICKABLE_SET_URL = "https://rebrickable.com/api/v3/lego/sets/{set_num}/"
REBRICKABLE_SET_PARTS_URL = "https://rebrickable.com/api/v3/lego/sets/{set_num}/parts/"
DEFAULT_TIMEOUT = 30


class SetInventoryError(RuntimeError):
    pass


class RebrickableSetClient:
    def __init__(self, session=None, timeout=DEFAULT_TIMEOUT):
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_set_with_inventory(self, set_num, api_key=None):
        normalized_set_num = self._normalize_set_num(set_num)
        api_key = api_key or os.getenv("REBRICKABLE_API_KEY")
        if not api_key:
            raise SetInventoryError("REBRICKABLE_API_KEY fehlt.")
        headers = {"Authorization": f"key {api_key}"}
        try:
            set_response = self.session.get(
                REBRICKABLE_SET_URL.format(set_num=normalized_set_num),
                headers=headers,
                timeout=self.timeout,
            )
            set_response.raise_for_status()
            set_data = set_response.json()
            inventory = self._fetch_inventory(normalized_set_num, headers)
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404:
                raise SetInventoryError(
                    "Set wurde in Rebrickable nicht gefunden."
                ) from exc
            if status == 429:
                raise SetInventoryError("Rebrickable Rate Limit erreicht.") from exc
            raise SetInventoryError(f"Rebrickable API-Fehler: {exc}") from exc
        except requests.Timeout as exc:
            raise SetInventoryError(f"Rebrickable Timeout: {exc}") from exc
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            raise SetInventoryError(f"Rebrickable-Fehler: {exc}") from exc

        if not inventory:
            raise SetInventoryError("Das Set enthält kein Inventar.")
        return set_data, inventory

    def _fetch_inventory(self, set_num, headers):
        url = REBRICKABLE_SET_PARTS_URL.format(set_num=set_num)
        inventory = []
        while url:
            response = self.session.get(
                url,
                headers=headers,
                params={"page_size": 1000},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            inventory.extend(payload.get("results", []))
            url = payload.get("next")
        return inventory

    @staticmethod
    def _normalize_set_num(set_num):
        normalized = str(set_num).strip()
        if not normalized:
            raise SetInventoryError("Bitte eine Setnummer eingeben.")
        return normalized if "-" in normalized else f"{normalized}-1"


class SetInventoryService:
    def __init__(self, database, client=None):
        self.database = database
        self.client = client or RebrickableSetClient()

    def add_set(self, set_num, api_key=None):
        normalized_set_num = RebrickableSetClient._normalize_set_num(set_num)
        if self._get_set_row(normalized_set_num) is not None:
            return {"added": False, "reason": "duplicate"}
        set_data, raw_inventory = self.client.fetch_set_with_inventory(
            normalized_set_num, api_key
        )
        return self.store_set(set_data, self._parse_inventory(raw_inventory))

    def store_set(self, set_data, inventory):
        set_num = str(set_data.get("set_num", "")).strip()
        name = str(set_data.get("name", "")).strip()
        if not set_num or not name:
            raise SetInventoryError("Rebrickable lieferte unvollständige Setdaten.")
        if self._get_set_row(set_num) is not None:
            return {"added": False, "reason": "duplicate"}
        items = self._merge_inventory(inventory)
        if not items:
            raise SetInventoryError("Das Set enthält kein gültiges Inventar.")
        database = self.database.connect()
        priority = database.execute(
            "SELECT COALESCE(MAX(priority), -1) + 1 FROM managed_sets"
        ).fetchone()[0]
        with database:
            cursor = database.execute(
                "INSERT INTO managed_sets(set_num, name, set_image_url, priority) VALUES (?, ?, ?, ?)",
                (set_num, name, set_data.get("set_img_url"), priority),
            )
            set_id = cursor.lastrowid
            database.executemany(
                """INSERT INTO managed_set_inventory(
                    set_id, part_num, color_id, color_name, quantity_required,
                    part_image_url, lego_design_id, lego_element_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        set_id,
                        item["part_num"],
                        item["color_id"],
                        item["color_name"],
                        item["quantity"],
                        item.get("part_image"),
                        item.get("lego_design_id"),
                        item.get("lego_element_id"),
                    )
                    for item in items
                ],
            )
        return {"added": True, "set_num": set_num, "set_id": set_id}

    def list_sets(self):
        rows = (
            self.database.connect()
            .execute(
                """SELECT managed_sets.*, COALESCE(SUM(quantity_required), 0) AS quantity_required,
                COALESCE(SUM(quantity_found), 0) AS quantity_found
                FROM managed_sets LEFT JOIN managed_set_inventory
                ON managed_sets.id = managed_set_inventory.set_id
                GROUP BY managed_sets.id ORDER BY priority"""
            )
            .fetchall()
        )
        return [dict(row) for row in rows]

    def get_inventory(self, set_num):
        rows = (
            self.database.connect()
            .execute(
                """SELECT managed_set_inventory.*, MAX(quantity_required - quantity_found, 0)
                AS quantity_remaining FROM managed_set_inventory
                JOIN managed_sets ON managed_sets.id = managed_set_inventory.set_id
                WHERE managed_sets.set_num = ? ORDER BY part_num, color_id""",
                (str(set_num),),
            )
            .fetchall()
        )
        return [dict(row) for row in rows]

    def set_priority_order(self, set_numbers):
        rows = self.list_sets()
        existing = [row["set_num"] for row in rows]
        requested = [str(value) for value in set_numbers]
        if len(requested) != len(existing) or set(requested) != set(existing):
            raise SetInventoryError(
                "Die Prioritätsreihenfolge enthält nicht genau alle Sets."
            )
        database = self.database.connect()
        with database:
            for priority, set_num in enumerate(requested):
                database.execute(
                    "UPDATE managed_sets SET priority = ? WHERE set_num = ?",
                    (priority + len(requested), set_num),
                )
            for priority, set_num in enumerate(requested):
                database.execute(
                    "UPDATE managed_sets SET priority = ? WHERE set_num = ?",
                    (priority, set_num),
                )

    def _get_set_row(self, set_num):
        return (
            self.database.connect()
            .execute("SELECT * FROM managed_sets WHERE set_num = ?", (set_num,))
            .fetchone()
        )

    @staticmethod
    def _parse_inventory(raw_inventory):
        parsed = []
        for item in raw_inventory:
            part = item.get("part") or {}
            color = item.get("color") or {}
            if part.get("part_num") is None or color.get("id") is None:
                continue
            parsed.append(
                {
                    "part_num": str(part["part_num"]),
                    "color_id": int(color["id"]),
                    "color_name": str(color.get("name") or "Unbekannt"),
                    "quantity": int(item.get("quantity") or 0),
                    "part_image": part.get("part_img_url"),
                    "lego_design_id": _lego_design_id(part),
                    "lego_element_id": item.get("element_id"),
                }
            )
        return parsed

    @staticmethod
    def _merge_inventory(inventory):
        merged = {}
        for item in inventory:
            part_num = item.get("part_num")
            color_id = item.get("color_id")
            quantity = int(item.get("quantity", 0))
            if part_num is None or color_id is None or quantity <= 0:
                continue
            key = (str(part_num), int(color_id))
            if key not in merged:
                merged[key] = dict(item)
            else:
                merged[key]["quantity"] += quantity
        return list(merged.values())


class PartAssignmentService:
    def __init__(self, database):
        self.database = database

    def assign_part(
        self, part_num, color_id, confidence=None, delta_e=None, lego_element_id=None
    ):
        database = self.database.connect()
        with database:
            item = database.execute(
                """SELECT managed_set_inventory.id, managed_set_inventory.set_id,
                    managed_sets.set_num, quantity_required, quantity_found
                    FROM managed_set_inventory JOIN managed_sets
                    ON managed_sets.id = managed_set_inventory.set_id
                    WHERE part_num = ? AND color_id = ? AND quantity_found < quantity_required
                    ORDER BY managed_sets.priority LIMIT 1""",
                (str(part_num), int(color_id)),
            ).fetchone()
            if item is None:
                return {"assigned": False, "set_id": None, "reason": "no_demand"}
            database.execute(
                "UPDATE managed_set_inventory SET quantity_found = quantity_found + 1 WHERE id = ?",
                (item["id"],),
            )
            database.execute(
                """INSERT INTO part_assignments(
                    part_num, color_id, set_id, inventory_item_id, confidence, delta_e, lego_element_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(part_num),
                    int(color_id),
                    item["set_id"],
                    item["id"],
                    confidence,
                    delta_e,
                    lego_element_id,
                ),
            )
        found = item["quantity_found"] + 1
        return {
            "assigned": True,
            "set_id": item["set_id"],
            "set_num": item["set_num"],
            "part_num": str(part_num),
            "color_id": int(color_id),
            "quantity_found": found,
            "quantity_required": item["quantity_required"],
            "quantity_remaining": item["quantity_required"] - found,
        }

    def undo_last_assignment(self):
        database = self.database.connect()
        with database:
            assignment = database.execute(
                "SELECT * FROM part_assignments WHERE undone = 0 AND inventory_item_id IS NOT NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if assignment is None:
                return {"undone": False, "reason": "no_assignment"}
            database.execute(
                """UPDATE managed_set_inventory SET quantity_found = MAX(quantity_found - 1, 0)
                    WHERE id = ?""",
                (assignment["inventory_item_id"],),
            )
            database.execute(
                "UPDATE part_assignments SET undone = 1 WHERE id = ?",
                (assignment["id"],),
            )
        return {"undone": True, "set_id": assignment["set_id"]}


def _lego_design_id(part):
    external_ids = part.get("external_ids") or {}
    lego_ids = external_ids.get("LEGO") or external_ids.get("Lego") or []
    return str(lego_ids[0]) if lego_ids else None
