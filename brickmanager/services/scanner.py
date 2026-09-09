class ScannerService:
    def __init__(self, recognizer=None, inventory_service=None):
        self.recognizer = recognizer
        self.inventory_service = inventory_service

    def process_image(self, image):
        if self.recognizer is None:
            raise RuntimeError("Kein Recognizer konfiguriert.")
        return self.recognizer.recognize(image)
