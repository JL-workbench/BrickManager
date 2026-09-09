from dataclasses import dataclass
from typing import Optional

@dataclass
class Brick:
    id: Optional[int] = None
    manufacturer: str = "LEGO"
    shape_id: Optional[str] = None
    color_id: Optional[int] = None
    part_number: Optional[str] = None

@dataclass
class BrickSet:
    id: Optional[int] = None
    manufacturer: str = "LEGO"
    set_number: str = ""
    name: str = ""
    quantity: int = 1
    complete: bool = False

@dataclass
class RecognitionResult:
    shape_id: Optional[str] = None
    score: float = 0.0
    bbox: Optional[tuple] = None
    rotation: int = 0
    rgb: Optional[tuple] = None
    manufacturer: str = "LEGO"
    brick_id: Optional[int] = None
    assigned_set: Optional[int] = None
    inventory_changed: bool = False
