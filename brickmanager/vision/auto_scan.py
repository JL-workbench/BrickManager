from enum import Enum

import numpy as np

from brickmanager.vision.color_detection import difference_mask


class AutoScanState(str, Enum):
    WAITING_FOR_PART = "waiting_for_part"
    WAITING_FOR_REMOVAL = "waiting_for_removal"
    SCANNING = "scanning"


class AutoScanController:
    def __init__(
        self,
        threshold=20,
        min_changed_ratio=0.02,
        max_motion_ratio=0.08,
        stable_checks=1,
    ):
        self.threshold = threshold
        self.min_changed_ratio = min_changed_ratio
        self.max_motion_ratio = max_motion_ratio
        self.stable_checks = stable_checks
        self.state = AutoScanState.WAITING_FOR_PART
        self._present_checks = 0
        self._previous_roi = None
        self.last_changed_ratio = 0.0
        self.last_motion_ratio = 0.0

    def reset(self):
        self.state = AutoScanState.WAITING_FOR_PART
        self._present_checks = 0
        self._previous_roi = None
        self.last_changed_ratio = 0.0
        self.last_motion_ratio = 0.0

    def scan_completed(self):
        """Keep the detected part locked until the ROI is empty again."""
        if self.state == AutoScanState.SCANNING:
            self.state = AutoScanState.WAITING_FOR_REMOVAL

    def scan_failed(self):
        """A failed snapshot must not cause repeated scans of the same part."""
        self.scan_completed()

    def process_frame(self, reference, current, scan_running=False):
        if reference is None or current is None or scan_running:
            return False
        if self.state == AutoScanState.SCANNING:
            return False
        _, mask = difference_mask(reference, current, self.threshold)
        if mask is None:
            return False
        changed_ratio = float(np.count_nonzero(mask)) / mask.size
        self.last_changed_ratio = changed_ratio
        part_present = changed_ratio >= self.min_changed_ratio
        if self.state == AutoScanState.WAITING_FOR_REMOVAL:
            if not part_present:
                self.reset()
            return False
        if not part_present:
            self._present_checks = 0
            self._previous_roi = current.copy()
            return False
        motion_ratio = 0.0
        if self._previous_roi is not None:
            _, motion_mask = difference_mask(
                self._previous_roi, current, self.threshold
            )
            motion_ratio = float(np.count_nonzero(motion_mask)) / motion_mask.size
        self.last_motion_ratio = motion_ratio
        self._previous_roi = current.copy()
        if motion_ratio > self.max_motion_ratio:
            self._present_checks = 0
            return False
        self._present_checks += 1
        if self._present_checks < self.stable_checks:
            return False
        self.state = AutoScanState.SCANNING
        self._present_checks = 0
        return True
