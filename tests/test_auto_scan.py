import numpy as np

from brickmanager.vision.auto_scan import AutoScanController, AutoScanState


def test_empty_roi_and_noise_do_not_trigger():
    reference = np.zeros((20, 20, 3), dtype=np.uint8)
    noise = reference.copy()
    noise[0, 0] = 10
    controller = AutoScanController(threshold=20, min_changed_ratio=0.1)

    assert controller.process_frame(reference, reference) is False
    assert controller.process_frame(reference, noise) is False


def test_stable_part_triggers_once_then_requires_removal():
    reference = np.zeros((20, 20, 3), dtype=np.uint8)
    part = reference.copy()
    part[3:17, 3:17] = 180
    controller = AutoScanController(
        threshold=20, min_changed_ratio=0.1, stable_checks=2
    )

    assert controller.process_frame(reference, part) is False
    assert controller.process_frame(reference, part) is True
    assert controller.state == AutoScanState.SCANNING
    assert controller.process_frame(reference, part) is False
    controller.scan_completed()
    assert controller.state == AutoScanState.WAITING_FOR_REMOVAL
    assert controller.process_frame(reference, part) is False
    assert controller.process_frame(reference, reference) is False
    assert controller.process_frame(reference, part) is False
    assert controller.process_frame(reference, part) is True


def test_moving_part_waits_for_a_stable_roi_before_triggering():
    reference = np.zeros((20, 20, 3), dtype=np.uint8)
    moving_part = reference.copy()
    moving_part[2:12, 2:12] = 180
    stable_part = reference.copy()
    stable_part[8:18, 8:18] = 180
    controller = AutoScanController(
        threshold=20, min_changed_ratio=0.1, stable_checks=2
    )

    assert controller.process_frame(reference, moving_part) is False
    assert controller.process_frame(reference, stable_part) is False
    assert controller.process_frame(reference, stable_part) is False
    assert controller.process_frame(reference, stable_part) is True
    assert controller.state == AutoScanState.SCANNING


def test_scan_running_or_scanning_state_never_triggers_a_second_scan():
    reference = np.zeros((20, 20, 3), dtype=np.uint8)
    part = reference.copy()
    part[3:17, 3:17] = 180
    controller = AutoScanController(
        threshold=20, min_changed_ratio=0.1, stable_checks=1
    )

    assert controller.process_frame(reference, part, scan_running=True) is False
    assert controller.process_frame(reference, part) is True
    assert controller.process_frame(reference, part) is False


def test_default_controller_detects_a_small_stable_part():
    reference = np.zeros((20, 20, 3), dtype=np.uint8)
    part = reference.copy()
    part[7:10, 7:10] = 180  # 2.25% of the ROI
    controller = AutoScanController()

    assert controller.process_frame(reference, part) is True
