"""User settings, persisted as JSON.

Defaults are deliberately gentle (handoff section 31): every sensory setting
starts at its calm end, and nothing strobes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields

from .game.difficulty import Difficulty
from .paths import settings_path

log = logging.getLogger(__name__)


@dataclass
class Settings:
    """Everything a parent can change."""

    # -- feedback ----------------------------------------------------------
    voice_cues: bool = True
    keyboard_lighting: bool = True
    wrong_sound: bool = True
    correct_sound: bool = True
    celebrations: bool = True
    attention_cues: bool = True

    # -- timing ------------------------------------------------------------
    attention_delay: float = 5.0
    """Seconds of stillness before the first reminder. 0 disables."""

    # -- difficulty --------------------------------------------------------
    difficulty: str = Difficulty.GUIDED.value
    require_shift: bool = False
    """When on, capitals must be typed with Shift. Off for beginners."""

    # -- sensory -----------------------------------------------------------
    animation: str = "gentle"  # none | gentle | fun
    sound_level: str = "gentle"  # off | gentle | fun
    visual_intensity: str = "medium"  # low | medium | high
    word_highlight_style: str = "none"  # none | dock | separate
    highlight_font_size: int = 54
    baseline_font_size: int = 34
    keyboard_highlight: str = "pulse"  # off | static | pulse | blink
    voice_rate: int = 170
    voice_name: str = ""
    """Empty means the system default voice."""

    # -- hardware ----------------------------------------------------------
    lighting_backend: str = "auto"
    show_onscreen_keyboard: bool = True
    lighting_target_color: str = "#4285F4"
    lighting_bg_color: str = "#000000"

    # -- content -----------------------------------------------------------
    category: str = ""
    """Empty means all categories."""

    level: int = 0
    """0 means any level."""
    
    all_caps: bool = False

    custom_only: bool = False

    def as_difficulty(self) -> Difficulty:
        try:
            return Difficulty(self.difficulty)
        except ValueError:
            return Difficulty.GUIDED

    @property
    def sounds_enabled(self) -> bool:
        return self.sound_level != "off"

    @property
    def animations_enabled(self) -> bool:
        return self.animation != "none"

    def lighting_color_rgb(self) -> tuple[int, int, int]:
        h = self.lighting_target_color.lstrip('#')
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except (ValueError, IndexError):
            return (66, 133, 244) # fallback #4285F4

    def lighting_bg_rgb(self) -> tuple[int, int, int]:
        h = self.lighting_bg_color.lstrip('#')
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except (ValueError, IndexError):
            return (0, 0, 0) # fallback #000000

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Build from a dict, ignoring unknown or malformed keys.

        Tolerating junk matters because this file is user-editable and a
        typo should not stop the app from starting.
        """
        known = {f.name: f.type for f in fields(cls)}
        clean = {}
        for key, value in (data or {}).items():
            if key not in known:
                continue
            clean[key] = value
        try:
            return cls(**clean)
        except TypeError as exc:
            log.warning("ignoring bad settings (%s), using defaults", exc)
            return cls()

    # -- persistence -------------------------------------------------------

    def save(self, path=None) -> None:
        target = path or settings_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            # Write via a temp file so a crash mid-write cannot corrupt it.
            temp = target.with_suffix(".tmp")
            temp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
            temp.replace(target)
        except OSError as exc:
            log.warning("could not save settings: %s", exc)

    @classmethod
    def load(cls, path=None) -> "Settings":
        source = path or settings_path()
        try:
            if not source.exists():
                return cls()
            return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("could not read settings (%s), using defaults", exc)
            return cls()
