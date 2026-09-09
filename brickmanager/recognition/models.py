from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """Pixel box with a top-left origin in the API source image."""

    x: float
    y: float
    width: float
    height: float
    image_width: float
    image_height: float
    score: float = 0.0

    def to_image_bounds(self, image_width, image_height):
        scale_x = image_width / self.image_width if self.image_width else 1.0
        scale_y = image_height / self.image_height if self.image_height else 1.0
        left = max(0, min(image_width, round(self.x * scale_x)))
        top = max(0, min(image_height, round(self.y * scale_y)))
        right = max(left, min(image_width, round((self.x + self.width) * scale_x)))
        bottom = max(top, min(image_height, round((self.y + self.height) * scale_y)))
        return left, top, right, bottom


@dataclass(frozen=True)
class BrickRecognition:
    part_id: str | None
    name: str | None
    confidence: float
    bounding_box: BoundingBox | None = None
    color: object | None = None
    category: str | None = None
    image_url: str | None = None


@dataclass(frozen=True)
class RecognitionResult:
    success: bool
    results: list[BrickRecognition]
    error: str | None = None

    @property
    def best_match(self) -> BrickRecognition | None:
        return self.results[0] if self.results else None
