from brickmanager.recognition.recognizer import Recognizer

class BrickognizeRecognizer(Recognizer):
    def __init__(self, api_url=None, timeout=30):
        self.api_url = api_url
        self.timeout = timeout
    def recognize(self, image):
        raise NotImplementedError("Brickognize wird in v0.4 implementiert.")
