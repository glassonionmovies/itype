"""Custom widgets: the sentence strip, the on-screen keyboard, and rewards.

The two that carry the game are :class:`SentenceStrip` and
:class:`OnScreenKeyboard`. Between them they have to make the target
unmistakable using more than colour alone -- weight, scale, an underline and a
glow all move together (handoff section 12).
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from ..game.sentence import CharState
from ..keyboard import keymap
from . import theme


class Card(QFrame):
    """A rounded panel used to group content."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class SentenceStrip(QWidget):
    """Renders the sentence with per-character state.

    Characters are laid out on a fixed grid derived from the widest glyph, so
    the text never reflows as letters change weight -- a moving target is
    exactly what a child learning key locations does not need.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._characters: list[str] = []
        self._states: list[CharState] = []
        self._pulse = 0.0
        self._shake = 0.0
        self._font_size = 34
        self._animate = True
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(33)

    # -- state -------------------------------------------------------------

    def set_sentence(self, characters: list[str]) -> None:
        self._characters = list(characters)
        self._states = [CharState.PENDING] * len(characters)
        if self._states:
            self._states[0] = CharState.CURRENT
        self._relayout()
        self.update()

    def set_states(self, states: list[CharState]) -> None:
        self._states = list(states)
        self.update()

    def set_animate(self, enabled: bool) -> None:
        self._animate = enabled
        if not enabled:
            self._pulse = 0.0

    def nudge(self) -> None:
        """Small wobble on the current letter after a wrong key.

        Deliberately gentle: it draws the eye without reading as a buzzer.
        """
        if self._animate:
            self._shake = 1.0

    def _advance(self) -> None:
        if self._animate:
            self._pulse = (self._pulse + 0.033) % 1000.0
        if self._shake > 0:
            self._shake = max(0.0, self._shake - 0.08)
        if self._animate or self._shake > 0:
            self.update()

    # -- layout ------------------------------------------------------------

    def _relayout(self) -> None:
        """Shrink the type size until the sentence fits the available width."""
        if not self._characters:
            return
        available = max(200, self.width() - 60)
        size = 44
        while size > 16:
            metrics = QFontMetrics(theme.mono_font(size, QFont.Weight.DemiBold))
            cell = metrics.horizontalAdvance("W") + 4
            if cell * len(self._characters) <= available:
                break
            size -= 2
        self._font_size = size

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._relayout()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self._characters:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        base_font = theme.mono_font(self._font_size, QFont.Weight.DemiBold)
        metrics = QFontMetrics(base_font)
        cell = metrics.horizontalAdvance("W") + 4
        total = cell * len(self._characters)
        start_x = (self.width() - total) / 2
        baseline = self.height() / 2 + metrics.capHeight() / 2

        wave = (math.sin(self._pulse * 2 * math.pi * 0.8) + 1) / 2

        for index, char in enumerate(self._characters):
            state = (
                self._states[index]
                if index < len(self._states)
                else CharState.PENDING
            )
            x = start_x + index * cell
            self._draw_char(painter, char, state, x, baseline, cell, metrics, wave)
        painter.end()

    def _draw_char(
        self,
        painter: QPainter,
        char: str,
        state: CharState,
        x: float,
        baseline: float,
        cell: float,
        metrics: QFontMetrics,
        wave: float,
    ) -> None:
        if state is CharState.CURRENT:
            self._draw_current(painter, char, x, baseline, cell, metrics, wave)
            return

        font = theme.mono_font(self._font_size, QFont.Weight.DemiBold)
        if state is CharState.CORRECT:
            color = QColor(theme.CHAR_CORRECT)
            color.setAlpha(215)
        else:
            color = QColor(theme.CHAR_PENDING)
        painter.setFont(font)
        painter.setPen(QPen(color))
        advance = metrics.horizontalAdvance(char)
        painter.drawText(QPointF(x + (cell - advance) / 2, baseline), char)

    def _draw_current(
        self,
        painter: QPainter,
        char: str,
        x: float,
        baseline: float,
        cell: float,
        metrics: QFontMetrics,
        wave: float,
    ) -> None:
        """Draw the target: bigger, brighter, glowing, and underlined.

        Four redundant cues on purpose, so the target is still obvious to a
        child who cannot distinguish the colours.
        """
        offset = 0.0
        if self._shake > 0:
            offset = math.sin(self._shake * math.pi * 6) * 5 * self._shake

        scale = 1.16 + (0.05 * wave if self._animate else 0.0)
        size = int(self._font_size * scale)
        font = theme.mono_font(size, QFont.Weight.Black)
        big_metrics = QFontMetrics(font)
        advance = big_metrics.horizontalAdvance(char if char != " " else "_")
        center_x = x + cell / 2 + offset

        # Glow behind the letter.
        glow_radius = cell * 0.95
        gradient = QLinearGradient(
            center_x, baseline - glow_radius, center_x, baseline + glow_radius * 0.4
        )
        top = QColor(theme.ACCENT)
        top.setAlpha(int(70 + 50 * wave))
        bottom = QColor(theme.ACCENT)
        bottom.setAlpha(0)
        gradient.setColorAt(0.0, bottom)
        gradient.setColorAt(0.5, top)
        gradient.setColorAt(1.0, bottom)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(
            QRectF(
                center_x - glow_radius * 0.7,
                baseline - glow_radius,
                glow_radius * 1.4,
                glow_radius * 1.35,
            )
        )

        # A space has no glyph, so show a visible key-shaped placeholder.
        if char == " ":
            width = cell * 1.5
            rect = QRectF(center_x - width / 2, baseline - 14, width, 14)
            painter.setBrush(QBrush(QColor(theme.ACCENT)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 5, 5)
        else:
            painter.setFont(font)
            painter.setPen(QPen(QColor(theme.CHAR_CURRENT)))
            painter.drawText(
                QPointF(center_x - advance / 2, baseline + big_metrics.descent() * 0.1),
                char,
            )

        # Underline anchors the eye to the position in the sentence.
        underline = QColor(theme.ACCENT)
        underline.setAlpha(240)
        pen = QPen(underline, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        y = baseline + metrics.descent() + 10
        painter.drawLine(
            QPointF(center_x - cell * 0.36, y), QPointF(center_x + cell * 0.36, y)
        )


# -- on-screen keyboard ----------------------------------------------------

#: A 60% ANSI layout, matching the PRO X 60's key set. Each entry is
#: (label, canonical key name or None, width in units).
KEYBOARD_ROWS: list[list[tuple[str, str | None, float]]] = [
    [
        ("~", "TILDE", 1.0), ("1", "ONE", 1.0), ("2", "TWO", 1.0), ("3", "THREE", 1.0),
        ("4", "FOUR", 1.0), ("5", "FIVE", 1.0), ("6", "SIX", 1.0), ("7", "SEVEN", 1.0),
        ("8", "EIGHT", 1.0), ("9", "NINE", 1.0), ("0", "ZERO", 1.0),
        ("-", "MINUS", 1.0), ("=", "EQUALS", 1.0), ("⌫", "BACKSPACE", 2.0),
    ],
    [
        ("⇥", "TAB", 1.5), ("Q", "Q", 1.0), ("W", "W", 1.0), ("E", "E", 1.0),
        ("R", "R", 1.0), ("T", "T", 1.0), ("Y", "Y", 1.0), ("U", "U", 1.0),
        ("I", "I", 1.0), ("O", "O", 1.0), ("P", "P", 1.0),
        ("[", "OPEN_BRACKET", 1.0), ("]", "CLOSE_BRACKET", 1.0), ("\\", "BACKSLASH", 1.5),
    ],
    [
        ("⇪", None, 1.75), ("A", "A", 1.0), ("S", "S", 1.0), ("D", "D", 1.0),
        ("F", "F", 1.0), ("G", "G", 1.0), ("H", "H", 1.0), ("J", "J", 1.0),
        ("K", "K", 1.0), ("L", "L", 1.0), (";", "SEMICOLON", 1.0),
        ("'", "APOSTROPHE", 1.0), ("⏎", "ENTER", 2.25),
    ],
    [
        ("⇧", "LEFT_SHIFT", 2.25), ("Z", "Z", 1.0), ("X", "X", 1.0), ("C", "C", 1.0),
        ("V", "V", 1.0), ("B", "B", 1.0), ("N", "N", 1.0), ("M", "M", 1.0),
        (",", "COMMA", 1.0), (".", "PERIOD", 1.0), ("/", "FORWARD_SLASH", 1.0),
        ("⇧", "RIGHT_SHIFT", 2.75),
    ],
    [
        ("ctrl", None, 1.25), ("opt", None, 1.25), ("cmd", None, 1.25),
        ("", "SPACE", 6.25),
        ("cmd", None, 1.25), ("fn", None, 1.25), ("ctrl", None, 2.5),
    ],
]


class OnScreenKeyboard(QWidget):
    """A 60% keyboard map that highlights the target key.

    This is what keeps the hand-eye coordination goal intact when the physical
    RGB is unavailable (handoff section 37): the child still gets a spatial
    "the key is *there*" cue, just on screen instead of under their fingers.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._target: str | None = None
        self._recent_wrong: str | None = None
        self._pulse = 0.0
        self._animate = True
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    #: Layout units across the widest row, used to keep keys square.
    _UNITS_WIDE = max(sum(width for _, _, width in row) for row in KEYBOARD_ROWS)
    _MAX_KEY = 62.0

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Keep the keyboard's aspect ratio so keys stay square.

        Without this the widget keeps its minimum height and the keys shrink
        to a fraction of the available width, which wastes the panel and makes
        the target harder to find -- the opposite of the point.
        """
        super().resizeEvent(event)
        rows = len(KEYBOARD_ROWS)
        margin, gap = 10.0, 3.0
        unit = (self.width() - 2 * margin - gap * 14) / self._UNITS_WIDE
        unit = max(18.0, min(self._MAX_KEY, unit))
        self.setFixedHeight(int(rows * unit + (rows - 1) * gap + 2 * margin))

    def set_target(self, key: str | None) -> None:
        if key != self._target:
            self._target = key
            self.update()

    def flash_wrong(self, key: str | None) -> None:
        self._recent_wrong = key
        self.update()
        QTimer.singleShot(450, self._clear_wrong)

    def _clear_wrong(self) -> None:
        self._recent_wrong = None
        self.update()

    def set_animate(self, enabled: bool) -> None:
        self._animate = enabled

    def _tick(self) -> None:
        if self._animate and self._target:
            self._pulse += 0.04
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rows = len(KEYBOARD_ROWS)
        margin = 10.0
        gap = 3.0
        # Mirrors resizeEvent exactly; the row gap count is rows - 1, not rows.
        unit = (self.width() - 2 * margin - gap * 14) / self._UNITS_WIDE
        unit = max(18.0, min(self._MAX_KEY, unit))
        key_height = min(unit, (self.height() - 2 * margin - gap * (rows - 1)) / rows)

        total_height = rows * key_height + (rows - 1) * gap
        y = (self.height() - total_height) / 2

        wave = (math.sin(self._pulse * 2 * math.pi * 0.5) + 1) / 2

        for row in KEYBOARD_ROWS:
            row_width = sum(w for _, _, w in row) * unit + gap * (len(row) - 1)
            x = (self.width() - row_width) / 2
            for label, key, width in row:
                w = width * unit
                self._draw_key(
                    painter, QRectF(x, y, w, key_height), label, key, wave
                )
                x += w + gap
            y += key_height + gap
        painter.end()

    def _draw_key(
        self,
        painter: QPainter,
        rect: QRectF,
        label: str,
        key: str | None,
        wave: float,
    ) -> None:
        is_target = key is not None and key == self._target
        is_wrong = key is not None and key == self._recent_wrong

        if is_target:
            glow = QColor(theme.ACCENT)
            glow.setAlpha(int(60 + 60 * wave))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 10, 10)

            fill = QColor(theme.ACCENT)
            border = QColor("#FFFFFF")
            text_color = QColor("#0C1220")
        elif is_wrong:
            fill = QColor(theme.WARNING)
            fill.setAlpha(150)
            border = QColor(theme.WARNING)
            text_color = QColor("#1A1400")
        else:
            fill = QColor(theme.SURFACE_LIGHT)
            border = QColor(theme.BORDER)
            text_color = QColor(theme.TEXT_FAINT)

        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, 2 if is_target else 1))
        painter.drawPath(path)

        if label:
            size = max(8, int(rect.height() * (0.42 if len(label) <= 2 else 0.3)))
            font = theme.display_font(
                size, QFont.Weight.Black if is_target else QFont.Weight.DemiBold
            )
            painter.setFont(font)
            painter.setPen(QPen(text_color))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)


# -- rewards ---------------------------------------------------------------


class StarRating(QWidget):
    """Five stars that fill in one at a time."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stars = 0
        self._revealed = 0
        self.setMinimumHeight(64)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reveal_next)

    def set_stars(self, stars: int, animate: bool = True) -> None:
        self._stars = max(0, min(5, stars))
        if animate:
            self._revealed = 0
            self._timer.start(220)
        else:
            self._revealed = self._stars
        self.update()

    def _reveal_next(self) -> None:
        if self._revealed >= self._stars:
            self._timer.stop()
            return
        self._revealed += 1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = min(self.height(), self.width() / 6)
        spacing = size * 1.2
        start = (self.width() - spacing * 5) / 2 + spacing / 2
        for i in range(5):
            filled = i < self._revealed
            self._draw_star(
                painter, QPointF(start + i * spacing, self.height() / 2), size * 0.45, filled
            )
        painter.end()

    @staticmethod
    def _draw_star(painter: QPainter, center: QPointF, radius: float, filled: bool) -> None:
        path = QPainterPath()
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            r = radius if i % 2 == 0 else radius * 0.45
            point = QPointF(
                center.x() + math.cos(angle) * r, center.y() + math.sin(angle) * r
            )
            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        if filled:
            painter.setBrush(QBrush(QColor(theme.GOLD)))
            painter.setPen(QPen(QColor("#B88900"), 1.5))
        else:
            painter.setBrush(QBrush(QColor(theme.SURFACE_LIGHT)))
            painter.setPen(QPen(QColor(theme.BORDER), 1.5))
        painter.drawPath(path)


class AccuracyBar(QWidget):
    """A chunky progress bar that animates up to its value."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._shown = 0.0
        self.setFixedHeight(26)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def set_value(self, value: float, animate: bool = True) -> None:
        self._value = max(0.0, min(1.0, value))
        if animate:
            self._shown = 0.0
            self._timer.start(16)
        else:
            self._shown = self._value
        self.update()

    def _step(self) -> None:
        self._shown += max(0.006, (self._value - self._shown) * 0.12)
        if self._shown >= self._value:
            self._shown = self._value
            self._timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        radius = self.height() / 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(theme.SURFACE_LIGHT)))
        painter.drawRoundedRect(rect, radius, radius)

        if self._shown > 0:
            width = max(self.height(), rect.width() * self._shown)
            fill = QRectF(0, 0, width, self.height())
            gradient = QLinearGradient(0, 0, width, 0)
            if self._value >= 0.95:
                gradient.setColorAt(0.0, QColor(theme.SUCCESS))
                gradient.setColorAt(1.0, QColor("#8CF0B4"))
            elif self._value >= 0.75:
                gradient.setColorAt(0.0, QColor(theme.ACCENT))
                gradient.setColorAt(1.0, QColor("#8CCBFF"))
            else:
                gradient.setColorAt(0.0, QColor(theme.WARNING))
                gradient.setColorAt(1.0, QColor("#FFD08C"))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill, radius, radius)
        painter.end()


class Confetti(QWidget):
    """A brief burst of falling shapes for a completed sentence.

    Transparent to mouse events so it can sit over the results screen. Stops
    itself after a few seconds; it is a reward, not a permanent decoration.
    """

    finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pieces: list[dict] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def burst(self, count: int = 90) -> None:
        colors = [
            theme.ACCENT, theme.SUCCESS, theme.GOLD,
            theme.PURPLE, theme.WARNING, QColor("#F472B6"),
        ]
        self._pieces = [
            {
                "x": random.uniform(0, max(1, self.width())),
                "y": random.uniform(-self.height() * 0.4, 0),
                "vx": random.uniform(-1.4, 1.4),
                "vy": random.uniform(1.8, 4.6),
                "size": random.uniform(5, 11),
                "spin": random.uniform(-9, 9),
                "angle": random.uniform(0, 360),
                "color": QColor(random.choice(colors)),
            }
            for _ in range(count)
        ]
        self._timer.start(16)
        self.show()
        self.raise_()

    def stop(self) -> None:
        self._timer.stop()
        self._pieces = []
        self.hide()

    def _step(self) -> None:
        height = self.height()
        alive = []
        for piece in self._pieces:
            piece["x"] += piece["vx"]
            piece["y"] += piece["vy"]
            piece["vy"] += 0.05
            piece["angle"] += piece["spin"]
            if piece["y"] < height + 20:
                alive.append(piece)
        self._pieces = alive
        if not self._pieces:
            self._timer.stop()
            self.hide()
            self.finished.emit()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self._pieces:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for piece in self._pieces:
            painter.save()
            painter.translate(piece["x"], piece["y"])
            painter.rotate(piece["angle"])
            painter.setBrush(QBrush(piece["color"]))
            size = piece["size"]
            painter.drawRoundedRect(QRectF(-size / 2, -size / 4, size, size / 2), 2, 2)
            painter.restore()
        painter.end()


class KeyHint(QWidget):
    """A single large key cap showing the character to press.

    Used in Guided mode where the target letter gets its own oversized
    presentation next to the sentence.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._char = ""
        self._pulse = 0.0
        self._animate = True
        self.setFixedSize(120, 120)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_char(self, char: str | None) -> None:
        self._char = char or ""
        self.update()

    def set_animate(self, enabled: bool) -> None:
        self._animate = enabled

    def _tick(self) -> None:
        if self._animate and self._char:
            self._pulse += 0.04
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self._char:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        wave = (math.sin(self._pulse * 2 * math.pi * 0.6) + 1) / 2
        inset = 8 - 3 * wave
        rect = QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset)

        glow = QColor(theme.ACCENT)
        glow.setAlpha(int(40 + 45 * wave))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawRoundedRect(rect.adjusted(-6, -6, 6, 6), 22, 22)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor("#6FBAFF"))
        gradient.setColorAt(1.0, QColor(theme.ACCENT))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawRoundedRect(rect, 18, 18)

        label = "space" if self._char == " " else self._char
        size = 46 if len(label) == 1 else 20
        painter.setFont(theme.display_font(size, QFont.Weight.Black))
        painter.setPen(QPen(QColor("#0C1220")))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()


def key_label_for(char: str | None) -> str:
    """Friendly label for the key a character lives on."""
    if not char:
        return ""
    if char == " ":
        return "space"
    return keymap.spoken_name_for_char(char)
