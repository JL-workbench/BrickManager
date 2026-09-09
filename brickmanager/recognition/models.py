from dataclasses import dataclass


@dataclass(frozen=True)
class BrickRecognition:
    part_id: str | None
    name: str | None
    confidence: float
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
