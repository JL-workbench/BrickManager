import pytest

from brickmanager.vision.camera import OpenCVCamera


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.release_count = 0

    def isOpened(self):
        return self.opened

    def read(self):
        return True, "frame"

    def release(self):
        self.release_count += 1
        self.opened = False


class FakeVideoCaptureFactory:
    def __init__(self, available_indexes):
        self.available_indexes = set(available_indexes)
        self.calls = []

    def __call__(self, index, backend=None):
        self.calls.append((index, backend))
        capture = FakeCapture(opened=index in self.available_indexes)
        return capture


def test_open_and_close_camera(monkeypatch):
    fake_factory = FakeVideoCaptureFactory({2})
    monkeypatch.setattr("brickmanager.vision.camera.cv2.VideoCapture", fake_factory)

    camera = OpenCVCamera(2)
    assert camera.open() is True
    assert camera.read() == (True, "frame")
    camera.close()
    assert camera.capture is None


def test_camera_open_failure_releases_capture(monkeypatch):
    fake_factory = FakeVideoCaptureFactory(set())
    monkeypatch.setattr("brickmanager.vision.camera.cv2.VideoCapture", fake_factory)

    camera = OpenCVCamera(4)
    assert camera.open() is False
    assert camera.capture is None


def test_enumerate_devices_lists_available_indexes(monkeypatch):
    fake_factory = FakeVideoCaptureFactory({0, 2})
    monkeypatch.setattr("brickmanager.vision.camera.cv2.VideoCapture", fake_factory)

    assert OpenCVCamera.enumerate_devices(4) == [0, 2]
