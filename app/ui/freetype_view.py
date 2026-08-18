"""Free Type view.

The child types whatever they want. The app coaches letter-by-letter
while a word is being formed, confirms each word on Space, and reads
the whole sentence on a period.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..audio.voice import NullVoice
from ..game.freetype_engine import FreeEvent, FreeTypeEngine
from ..game.phonetics import phonetic_for
from . import theme

log = logging.getLogger(__name__)

_TICK_MS = 500            # attention timer resolution
_IDLE_TICKS = 4           # ticks before first spell (2 s)
_MAX_SPELL_REPEATS = 5    # stop after this many spelling rounds


class FreeTypeView(QWidget):
    """Creative free-typing mode screen."""

    quit_requested = Signal()

    def __init__(self, voice=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.voice = voice or NullVoice()
        self.engine = FreeTypeEngine()
        self._idle_ticks: int = 0
        self._spell_repeats: int = 0
        self._build()

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 32, 48, 32)
        root.setSpacing(0)

        header = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.setObjectName("ghost")
        back.setFixedHeight(40)
        back.clicked.connect(self.quit_requested.emit)
        header.addWidget(back)
        header.addStretch(1)

        mode_lbl = QLabel("\u270f\ufe0f  Free Type")
        mode_lbl.setFont(theme.display_font(17, QFont.Weight.DemiBold))
        mode_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        header.addWidget(mode_lbl)
        root.addLayout(header)

        root.addStretch(1)

        self.text_label = QLabel("Start typing\u2026")
        self.text_label.setFont(theme.display_font(54, QFont.Weight.Bold))
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        root.addWidget(self.text_label)

        root.addSpacing(18)

        self.hint_label = QLabel(
            "Press Space to confirm a word \u00b7 Press . to finish your sentence"
        )
        self.hint_label.setFont(theme.display_font(14, QFont.Weight.Normal))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet(f"color: {theme.TEXT_FAINT.name()};")
        root.addWidget(self.hint_label)

        root.addStretch(2)

    def start(self) -> None:
        self.engine.reset()
        self._idle_ticks = 0
        self._spell_repeats = 0
        self._refresh_display()
        self._reset_hint()
        self._timer.start()
        self.setFocus()

    def stop(self) -> None:
        self._timer.stop()

    def update_voice(self, voice) -> None:
        self.voice = voice

    def _refresh_display(self) -> None:
        confirmed = self.engine.confirmed_words
        partial = self.engine.current_word

        if not confirmed and not partial:
            self.text_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
            self.text_label.setText("Start typing\u2026")
            return

        parts = []
        for w in confirmed:
            parts.append(
                f"<span style='color:{theme.TEXT.name()};'>{w}</span>"
            )
        if partial:
            parts.append(
                f"<span style='color:{theme.BLUE.name()};font-style:italic;'>{partial}</span>"
            )
        self.text_label.setStyleSheet("")
        self.text_label.setText(" ".join(parts))

    def _flash_rejected(self) -> None:
        partial = self.engine.current_word
        confirmed = self.engine.confirmed_words
        parts = []
        for w in confirmed:
            parts.append(f"<span style='color:{theme.TEXT.name()};'>{w}</span>")
        if partial:
            parts.append(
                f"<span style='color:{theme.RED.name()};font-weight:bold;'>{partial}</span>"
            )
        self.text_label.setStyleSheet("")
        self.text_label.setText(" ".join(parts))
        QTimer.singleShot(900, self._refresh_display)

    def _set_hint(self, text: str, *, temporary: bool = False) -> None:
        self.hint_label.setText(text)
        if temporary:
            QTimer.singleShot(2500, self._reset_hint)

    def _reset_hint(self) -> None:
        self.hint_label.setText(
            "Press Space to confirm a word \u00b7 Press . to finish your sentence"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Escape:
            self.quit_requested.emit()
            return

        if key == Qt.Key.Key_Backspace:
            char = "\x08"
        elif text:
            char = text
        else:
            super().keyPressEvent(event)
            return

        result = self.engine.press(char)
        self._idle_ticks = 0
        self._spell_repeats = 0

        if result.event == FreeEvent.LETTER:
            self._refresh_display()
            self._reset_hint()

        elif result.event == FreeEvent.BACKSPACE:
            self._refresh_display()

        elif result.event == FreeEvent.WORD_CONFIRMED:
            self._refresh_display()
            self._reset_hint()
            word = result.confirmed_words[-1] if result.confirmed_words else ""
            if word:
                self.voice.say(word, priority=True)

        elif result.event == FreeEvent.WORD_REJECTED:
            self._flash_rejected()
            self._set_hint(
                "\u26a0\ufe0f  Not an English word \u2014 keep typing or press Backspace",
                temporary=True,
            )
            self.voice.say("Not a word yet. Keep typing.", priority=True)

        elif result.event == FreeEvent.SENTENCE_DONE:
            sentence = result.sentence
            self._set_hint("\u2728 Great sentence! Listen carefully\u2026")
            self.voice.say(sentence, priority=True)
            QTimer.singleShot(5000, lambda: self.voice.say(sentence))
            QTimer.singleShot(8500, self._after_sentence)

    def _after_sentence(self) -> None:
        self._refresh_display()
        self._reset_hint()

    def _on_tick(self) -> None:
        partial = self.engine.current_word
        if not partial:
            self._idle_ticks = 0
            self._spell_repeats = 0
            return

        self._idle_ticks += 1

        next_fire = (self._spell_repeats + 1) * _IDLE_TICKS
        if self._idle_ticks < next_fire:
            return
        if self._spell_repeats >= _MAX_SPELL_REPEATS:
            return

        self._spell_repeats += 1

        spelled = " ".join(partial.upper())
        phonetic = phonetic_for(partial)

        if phonetic and phonetic.lower() != partial.lower():
            self.voice.say(f"{spelled} \u2014 {phonetic}", priority=True)
        else:
            self.voice.say(spelled, priority=True)
