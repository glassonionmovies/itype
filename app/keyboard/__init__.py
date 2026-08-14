"""Vendor-independent keyboard lighting.

Import from here rather than reaching into a specific backend, so swapping
hardware never touches game code.
"""

from .base import (
    CORRECT_COLOR,
    DIM_COLOR,
    MISTAKE_COLOR,
    RGB,
    TARGET_COLOR,
    DeviceInfo,
    KeyboardLighting,
)
from .manager import BACKEND_ORDER, LightingManager, detect
from .noop import NoOpKeyboardLighting

__all__ = [
    "BACKEND_ORDER",
    "CORRECT_COLOR",
    "DIM_COLOR",
    "DeviceInfo",
    "KeyboardLighting",
    "LightingManager",
    "MISTAKE_COLOR",
    "NoOpKeyboardLighting",
    "RGB",
    "TARGET_COLOR",
    "detect",
]
