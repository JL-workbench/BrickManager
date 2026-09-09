import json
import logging
import sqlite3
import threading
import time
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class RebrickableCacheService:
    _state_lock = threading.Lock()
    _request_states = {}

    def __init__(self, path, min_request_interval=1.0, clock=None, sleep=None):
        self.path = Path(path)
        self.min_request_interval = min_request_interval
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._state_lock:
            self._request_states.setdefault(
                str(self.path.resolve()), [threading.Lock(), None]
            )
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """CREATE TABLE IF NOT EXISTS rebrickable_cache_meta (
                key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rebrickable_colors (
                color_id INTEGER PRIMARY KEY, name TEXT NOT NULL, rgb TEXT NOT NULL,
                is_trans INTEGER NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS rebrickable_part_colors (
                part_num TEXT NOT NULL, color_id INTEGER NOT NULL, name TEXT NOT NULL,
                rgb TEXT NOT NULL, is_trans INTEGER NOT NULL, element_ids TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(part_num, color_id));
            CREATE TABLE IF NOT EXISTS rebrickable_sets_cache (
                set_num TEXT PRIMARY KEY, set_data TEXT NOT NULL, inventory_data TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);"""
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO rebrickable_cache_meta(key, value) VALUES ('schema_version', '1')"
        )
        self.connection.commit()

    def get_colors(self, color_ids=None):
        query = "SELECT color_id, name, rgb, is_trans FROM rebrickable_colors"
        parameters = ()
        if color_ids:
            ids = [int(color_id) for color_id in color_ids]
            query += f" WHERE color_id IN ({','.join('?' for _ in ids)})"
            parameters = tuple(ids)
        rows = self.connection.execute(query, parameters).fetchall()
        return [self._color_from_row(row) for row in rows]

    def get_color(self, color_id):
        colors = self.get_colors([color_id])
        return colors[0] if colors else None

    def save_colors(self, colors):
        values = [
            (
                int(color["color_id"]),
                str(color["name"]),
                str(color["rgb"]),
                int(bool(color.get("is_trans"))),
            )
            for color in colors
        ]
        with self.connection:
            self.connection.executemany(
                """INSERT INTO rebrickable_colors(color_id, name, rgb, is_trans)
                VALUES (?, ?, ?, ?) ON CONFLICT(color_id) DO UPDATE SET
                name=excluded.name, rgb=excluded.rgb, is_trans=excluded.is_trans,
                updated_at=CURRENT_TIMESTAMP""",
                values,
            )

    def get_part_colors(self, part_num):
        rows = self.connection.execute(
            """SELECT color_id, name, rgb, is_trans, element_ids
            FROM rebrickable_part_colors WHERE part_num = ? ORDER BY color_id""",
            (str(part_num),),
        ).fetchall()
        if rows:
            LOGGER.debug("[RebrickableCache] Part %s colors: CACHE HIT", part_num)
        return [
            {
                **self._color_from_row(row),
                "element_ids": json.loads(row["element_ids"]),
                "element_id": (json.loads(row["element_ids"]) or [None])[0],
            }
            for row in rows
        ]

    def save_part_colors(self, part_num, colors):
        with self.connection:
            self.connection.execute(
                "DELETE FROM rebrickable_part_colors WHERE part_num = ?",
                (str(part_num),),
            )
            self.connection.executemany(
                """INSERT INTO rebrickable_part_colors(
                    part_num, color_id, name, rgb, is_trans, element_ids
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (
                        str(part_num),
                        int(color["color_id"]),
                        str(color["name"]),
                        str(color["rgb"]),
                        int(bool(color.get("is_trans"))),
                        json.dumps(list(color.get("element_ids") or [])),
                    )
                    for color in colors
                ],
            )
        LOGGER.debug("[RebrickableCache] Saved part %s colors to cache", part_num)

    def get_element_id(self, part_num, color_id):
        colors = self.get_part_colors(part_num)
        for color in colors:
            if color["color_id"] == int(color_id):
                return color["element_id"]
        return None

    def get_set(self, set_num):
        row = self.connection.execute(
            "SELECT set_data, inventory_data FROM rebrickable_sets_cache WHERE set_num = ?",
            (str(set_num),),
        ).fetchone()
        if row is None:
            return None
        LOGGER.debug("[RebrickableCache] Set %s: CACHE HIT", set_num)
        return json.loads(row["set_data"]), json.loads(row["inventory_data"])

    def save_set(self, set_num, set_data, inventory):
        with self.connection:
            self.connection.execute(
                """INSERT INTO rebrickable_sets_cache(set_num, set_data, inventory_data)
                VALUES (?, ?, ?) ON CONFLICT(set_num) DO UPDATE SET
                set_data=excluded.set_data, inventory_data=excluded.inventory_data,
                updated_at=CURRENT_TIMESTAMP""",
                (str(set_num), json.dumps(set_data), json.dumps(inventory)),
            )

    def clear(self):
        with self.connection:
            self.connection.execute("DELETE FROM rebrickable_colors")
            self.connection.execute("DELETE FROM rebrickable_part_colors")
            self.connection.execute("DELETE FROM rebrickable_sets_cache")

    def wait_for_request_slot(self):
        request_lock, last_request = self._request_states[str(self.path.resolve())]
        with request_lock:
            now = self.clock()
            if last_request is not None:
                wait_time = self.min_request_interval - (now - last_request)
                if wait_time > 0:
                    self.sleep(wait_time)
            self._request_states[str(self.path.resolve())][1] = self.clock()

    def request(self, session, url, *, max_retries=1, **kwargs):
        for attempt in range(max_retries + 1):
            self.wait_for_request_slot()
            response = session.get(url, **kwargs)
            if getattr(response, "status_code", None) != 429 or attempt == max_retries:
                return response
            LOGGER.warning("[RebrickableCache] Rate limit reached; retrying once")
        return response

    def close(self):
        self.connection.close()

    @staticmethod
    def _color_from_row(row):
        return {
            "color_id": int(row["color_id"]),
            "name": str(row["name"]),
            "rgb": str(row["rgb"]),
            "is_trans": bool(row["is_trans"]),
        }
