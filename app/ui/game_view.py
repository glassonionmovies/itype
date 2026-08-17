"""The play screen.

Owns keyboard focus and turns key events into engine calls. Everything else
-- lighting, voice, sounds -- is sequenced by
:class:`~app.game.session.GameSession`; this view just renders the outcome
(handoff section 15: the window owns focus, no global input monitoring).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Settings
from ..game.difficulty import profile_for
from ..game.scoring import SessionResult
from ..game.sentence import CharState
from ..game.session import AttentionSettings, GameSession
from ..keyboard import keymap
from . import theme
from .widgets import Card, KeyHint, OnScreenKeyboard, SentenceStrip


class GameView(QWidget):
    """Plays one sentence."""

    finished = Signal(SessionResult)
    quit_requested = Signal()

    def __init__(
        self,
        settings: Settings,
        lighting=None,
        feedback=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.lighting = lighting
        self.feedback = feedback
        self.session: GameSession | None = None

        self._build()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._attention_timer = QTimer(self)
        self._attention_timer.timeout.connect(self._check_attention)
        self._attention_timer.setInterval(500)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._countdown_step = 0

    # -- construction ------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 20, 32, 24)
        root.setSpacing(14)

        # Top bar: back button, category, live stats.
        top = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("ghost")
        self.back_button.clicked.connect(self._on_back)
        self.back_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top.addWidget(self.back_button)
        top.addStretch(1)

        self.stats_label = QLabel("")
        self.stats_label.setFont(theme.display_font(14, QFont.Weight.DemiBold))
        self.stats_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        top.addWidget(self.stats_label)
        root.addLayout(top)

        root.addStretch(1)

        # The sentence itself.
        self.strip = SentenceStrip()
        root.addWidget(self.strip)

        # Coaching line plus the oversized target key.
        middle = QHBoxLayout()
        middle.setSpacing(24)
        middle.addStretch(1)

        self.hint = KeyHint()
        middle.addWidget(self.hint, 0, Qt.AlignmentFlag.AlignVCenter)

        self.coach_label = QLabel("")
        self.coach_label.setFont(theme.display_font(26, QFont.Weight.Bold))
        self.coach_label.setMinimumWidth(320)
        self.coach_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        middle.addWidget(self.coach_label, 0, Qt.AlignmentFlag.AlignVCenter)
        middle.addStretch(1)
        root.addLayout(middle)

        root.addStretch(1)

        # The on-screen keyboard map.
        self.keyboard_card = Card()
        card_layout = QVBoxLayout(self.keyboard_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        self.keyboard = OnScreenKeyboard()
        card_layout.addWidget(self.keyboard)
        root.addWidget(self.keyboard_card)

        self.lighting_note = QLabel("")
        self.lighting_note.setFont(theme.display_font(11, QFont.Weight.Normal))
        self.lighting_note.setStyleSheet(f"color: {theme.TEXT_FAINT.name()};")
        self.lighting_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lighting_note)

    # -- lifecycle ---------------------------------------------------------

    def start(self, text: str) -> None:
        """Begin a new sentence."""
        profile = profile_for(self.settings.as_difficulty())

        attention = AttentionSettings(
            enabled=self.settings.attention_cues and self.settings.attention_delay > 0,
            first_delay=self.settings.attention_delay or 5.0,
            second_delay=(self.settings.attention_delay or 5.0) + 4.0,
        )

        self.session = GameSession(
            text,
            difficulty=self.settings.as_difficulty(),
            lighting=self.lighting if self.settings.keyboard_lighting else None,
            voice=self.feedback.voice if self.feedback else None,
            sounds=self.feedback,
            attention=attention,
            require_shift=self.settings.require_shift,
        )

        characters = [c.display for c in self.session.engine.sentence.characters]
        self.strip.set_sentence(characters)
        self.strip.set_animate(self.settings.animations_enabled)
        self.keyboard.set_animate(self.settings.animations_enabled)
        self.hint.set_animate(self.settings.animations_enabled)

        # Hide UI elements during countdown
        self.strip.setVisible(False)
        self.keyboard_card.setVisible(False)
        self.hint.setVisible(False)

        if self.lighting:
            self.lighting.blackout()

        self._update_lighting_note()
        self.setFocus()
        
        self.coach_label.setText("Ready...")
        if self.feedback and self.feedback.voice:
            self.feedback.voice.say("Ready", priority=True)
            
        self._countdown_step = 0
        self._countdown_timer.start(1000)
        self.setFocus()

    def stop(self) -> None:
        self._attention_timer.stop()
        self._countdown_timer.stop()
        if self.session:
            self.session.end()

    def _on_back(self) -> None:
        self.stop()
        self.quit_requested.emit()

    def _on_countdown_tick(self) -> None:
        self._countdown_step += 1
        if self._countdown_step == 1:
            self.coach_label.setText("Set...")
            if self.feedback and self.feedback.voice:
                self.feedback.voice.say("Set", priority=True)
        elif self._countdown_step == 2:
            self.coach_label.setText("Go!")
            if self.feedback and self.feedback.voice:
                self.feedback.voice.say("Go", priority=True)
        else:
            self._countdown_timer.stop()
            self.coach_label.setText("")
            
            profile = profile_for(self.settings.as_difficulty())
            self.strip.setVisible(True)
            show_keyboard = profile.show_onscreen_keyboard and self.settings.show_onscreen_keyboard
            self.keyboard_card.setVisible(show_keyboard)
            self.hint.setVisible(profile.show_target_letter)
            
            if self.session:
                self.session.begin()
            self._refresh()
            self._attention_timer.start()

    def _update_lighting_note(self) -> None:
        """Tell the parent, quietly, what the keyboard is doing.

        Handoff section 37 asks for an explicit message when RGB is
        unavailable rather than silent degradation.
        """
        if not self.settings.keyboard_lighting:
            self.lighting_note.setText("Keyboard lighting is turned off in settings.")
            return
        if self.lighting and self.lighting.available():
            self.lighting_note.setText(f"Keyboard: {self.lighting.describe()}")
        else:
            self.lighting_note.setText(
                "Keyboard lighting unavailable — using the screen keyboard instead."
            )

    # -- input -------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() == Qt.Key.Key_Escape:
            self._on_back()
            return
        if self.session is None or not self.session.started or self.session.engine.finished:
            super().keyPressEvent(event)
            return

        text = event.text()
        if event.key() == Qt.Key.Key_Space:
            text = " "
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            text = "\n"

        # Modifiers and navigation keys arrive with empty text; ignore them so
        # holding Shift is never scored as a mistake.
        if not text:
            super().keyPressEvent(event)
            return

        result = self.session.press(text)
        if result.ignored:
            return

        if not result.accepted:
            self.strip.nudge()
            pressed_key = keymap.key_name_for_char(result.typed_char)
            self.keyboard.flash_wrong(pressed_key)

        self._refresh()

        if result.finished:
            self._complete()

    def _refresh(self) -> None:
        if self.session is None:
            return
        engine = self.session.engine
        states = [engine.state_of(i) for i in range(len(engine.sentence))]
        self.strip.set_states(states)

        expected = engine.expected_char
        self.keyboard.set_target(engine.expected_key)
        self.hint.set_char(engine.expected_display)

        if expected:
            spoken = keymap.spoken_name_for_char(expected)
            self.coach_label.setText(f"Find {spoken}")
            self.coach_label.setStyleSheet(f"color: {theme.TEXT.name()};")
        else:
            self.coach_label.setText("You did it!")
            self.coach_label.setStyleSheet(f"color: {theme.SUCCESS.name()};")

        stars = "⭐" * min(5, engine.correct // 5)
        self.stats_label.setText(
            f"{engine.correct}/{len(engine.sentence)}   "
            f"Oops: {engine.mistakes}   {stars}"
        )

    def _check_attention(self) -> None:
        if self.session is None:
            return
        message = self.session.tick()
        if message:
            self.coach_label.setText(message)
            self.coach_label.setStyleSheet(f"color: {theme.WARNING.name()};")
            self.strip.nudge()

    def _complete(self) -> None:
        self._attention_timer.stop()
        if self.session is None:
            return
        result = self.session.result()
        if self.feedback:
            self.feedback.play_complete(result.perfect)
        # Small pause so the last keystroke's feedback lands before the
        # screen changes underneath the child.
        QTimer.singleShot(650, lambda: self.finished.emit(result))

    # -- state -------------------------------------------------------------

    def current_states(self) -> list[CharState]:
        if self.session is None:
            return []
        engine = self.session.engine
        return [engine.state_of(i) for i in range(len(engine.sentence))]
