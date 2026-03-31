"""Animation controller for buddy sprites."""

from __future__ import annotations


class AnimationController:
    """Manages frame cycling for sprite animations."""

    def __init__(self, frame_count: int):
        self.frame_count = frame_count
        self.current_frame = 0

    def tick(self) -> int:
        """Advance to next frame. Returns new frame index."""
        self.current_frame = (self.current_frame + 1) % self.frame_count
        return self.current_frame

    def reset(self):
        self.current_frame = 0
