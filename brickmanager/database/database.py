import sqlite3
from config import DATABASE_FILE

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS manufacturers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS brick_colors (
 id INTEGER PRIMARY KEY AUTOINCREMENT, manufacturer_id INTEGER, name TEXT NOT NULL,
 r INTEGER NOT NULL, g INTEGER NOT NULL, b INTEGER NOT NULL,
 FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id));
CREATE TABLE IF NOT EXISTS brick_shapes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, manufacturer_id INTEGER, shape_id TEXT NOT NULL, name TEXT,
 FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id), UNIQUE(manufacturer_id,shape_id));
CREATE TABLE IF NOT EXISTS bricks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, manufacturer_id INTEGER, shape_id INTEGER, color_id INTEGER,
 part_number TEXT, FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id),
 FOREIGN KEY(shape_id) REFERENCES brick_shapes(id), FOREIGN KEY(color_id) REFERENCES brick_colors(id));
CREATE TABLE IF NOT EXISTS sets (
 id INTEGER PRIMARY KEY AUTOINCREMENT, manufacturer_id INTEGER, set_number TEXT NOT NULL, name TEXT,
 quantity INTEGER NOT NULL DEFAULT 1, complete INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id));
CREATE TABLE IF NOT EXISTS set_parts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, set_id INTEGER NOT NULL, brick_id INTEGER NOT NULL,
 required_quantity INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(set_id) REFERENCES sets(id) ON DELETE CASCADE,
 FOREIGN KEY(brick_id) REFERENCES bricks(id));
CREATE TABLE IF NOT EXISTS inventory (
 id INTEGER PRIMARY KEY AUTOINCREMENT, brick_id INTEGER NOT NULL,
 quantity_owned INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(brick_id) REFERENCES bricks(id));
CREATE TABLE IF NOT EXISTS history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 image_path TEXT, manufacturer_id INTEGER, shape_id TEXT, color_r INTEGER, color_g INTEGER, color_b INTEGER,
 score REAL, bbox_x INTEGER, bbox_y INTEGER, bbox_w INTEGER, bbox_h INTEGER, brick_id INTEGER,
 assigned_set_id INTEGER, accepted INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id),
 FOREIGN KEY(brick_id) REFERENCES bricks(id), FOREIGN KEY(assigned_set_id) REFERENCES sets(id));
CREATE TABLE IF NOT EXISTS managed_sets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 set_num TEXT NOT NULL UNIQUE,
 name TEXT NOT NULL,
 set_image_url TEXT,
 priority INTEGER NOT NULL UNIQUE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS managed_set_inventory (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 set_id INTEGER NOT NULL,
 part_num TEXT NOT NULL,
 color_id INTEGER NOT NULL,
 color_name TEXT NOT NULL,
 quantity_required INTEGER NOT NULL CHECK(quantity_required >= 0),
 quantity_found INTEGER NOT NULL DEFAULT 0 CHECK(quantity_found >= 0),
 part_image_url TEXT,
 lego_design_id TEXT,
 lego_element_id TEXT,
 UNIQUE(set_id, part_num, color_id),
 FOREIGN KEY(set_id) REFERENCES managed_sets(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS part_assignments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 part_num TEXT NOT NULL,
 color_id INTEGER NOT NULL,
 set_id INTEGER,
 inventory_item_id INTEGER,
 confidence REAL,
 delta_e REAL,
 lego_element_id TEXT,
 undone INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(set_id) REFERENCES managed_sets(id),
 FOREIGN KEY(inventory_item_id) REFERENCES managed_set_inventory(id));
"""


class Database:
    def __init__(self, path=DATABASE_FILE):
        self.path = path
        self.connection = None

    def connect(self):
        if self.connection is None:
            self.connection = sqlite3.connect(self.path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys=ON")
        return self.connection

    def initialize(self):
        db = self.connect()
        db.executescript(SCHEMA)
        db.execute("INSERT OR IGNORE INTO manufacturers(name) VALUES (?)", ("LEGO",))
        db.commit()

    def scalar(self, query, parameters=()):
        row = self.connect().execute(query, parameters).fetchone()
        return row[0] if row else None

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
