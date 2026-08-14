"""The celebration screen shown after a completed sentence.

Every completion gets a celebration, including one with mistakes in it
(handoff section 21). Accuracy and independence lead; speed is a footnote.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Settings
from ..game.scoring import SessionResult
from ..keyboard import keymap
from . import theme
from .widgets import AccuracyBar, Card, Confetti, StarRating


class ResultsView(QWidget):
    """Shows how the sentence went."""

    next_requested = Signal()
    repeat_requested = Signal()
    home_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._result: SessionResult | None = None
        self._build()

        self.confetti = Confetti(self)
        self.confetti.hide()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 32, 48, 32)
        root.setSpacing(12)

        root.addStretch(1)

        self.headline = QLabel("GREAT JOB!")
        self.headline.setFont(theme.display_font(46, QFont.Weight.Black))
        self.headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.headline)

        self.sentence_label = QLabel("")
        self.sentence_label.setFont(theme.mono_font(17, QFont.Weight.Medium))
        self.sentence_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        self.sentence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence_label.setWordWrap(True)
        root.addWidget(self.sentence_label)

        self.stars = StarRating()
        root.addWidget(self.stars)

        root.addSpacing(8)

        # Stats card.
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 22, 28, 22)
        card_layout.setSpacing(14)

        accuracy_row = QHBoxLayout()
        accuracy_caption = QLabel("Accuracy")
        accuracy_caption.setFont(theme.display_font(14, QFont.Weight.DemiBold))
        accuracy_row.addWidget(accuracy_caption)
        accuracy_row.addStretch(1)
        self.accuracy_value = QLabel("100%")
        self.accuracy_value.setFont(theme.display_font(14, QFont.Weight.Black))
        accuracy_row.addWidget(self.accuracy_value)
        card_layout.addLayout(accuracy_row)

        self.accuracy_bar = AccuracyBar()
        card_layout.addWidget(self.accuracy_bar)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(28)
        self._details: dict[str, QLabel] = {}
        for key, caption in (
            ("mistakes", "Oops"),
            ("time", "Time"),
            ("independence", "By myself"),
            ("wpm", "Words / min"),
        ):
            block = QVBoxLayout()
            value = QLabel("—")
            value.setFont(theme.display_font(20, QFont.Weight.Black))
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label = QLabel(caption)
            label.setFont(theme.display_font(11, QFont.Weight.Normal))
            label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block.addWidget(value)
            block.addWidget(label)
            detail_row.addLayout(block, 1)
            self._details[key] = value
        card_layout.addLayout(detail_row)

        root.addWidget(card)

        self.tip_label = QLabel("")
        self.tip_label.setFont(theme.display_font(13, QFont.Weight.Normal))
        self.tip_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.tip_label)

        root.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.home_button = QPushButton("🏠  Home")
        self.home_button.setObjectName("ghost")
        self.home_button.clicked.connect(self.home_requested.emit)
        actions.addWidget(self.home_button)

        self.repeat_button = QPushButton("↻  Again")
        self.repeat_button.clicked.connect(self.repeat_requested.emit)
        actions.addWidget(self.repeat_button)

        actions.addStretch(1)

        self.next_button = QPushButton("Next Sentence  →")
        self.next_button.setObjectName("primary")
        self.next_button.clicked.connect(self.next_requested.emit)
        self.next_button.setDefault(True)
        actions.addWidget(self.next_button)
        root.addLayout(actions)

    # -- display -----------------------------------------------------------

    def show_result(self, result: SessionResult) -> None:
        self._result = result
        animate = self.settings.animations_enabled

        self.headline.setText(result.headline)
        color = theme.SUCCESS if result.perfect else theme.ACCENT
        self.headline.setStyleSheet(f"color: {color.name()};")

        self.sentence_label.setText(result.sentence)
        self.stars.set_stars(result.stars, animate)
        self.accuracy_bar.set_value(result.accuracy, animate)
        self.accuracy_value.setText(f"{result.accuracy_percent}%")

        self._details["mistakes"].setText(str(result.mistakes))
        self._details["time"].setText(f"{result.elapsed_seconds:.0f}s")
        self._details["independence"].setText(
            "⭐" * result.assistance.independence_stars
        )
        self._details["wpm"].setText(f"{result.wpm:.0f}")

        self.tip_label.setText(self._tip_for(result))

        if animate and self.settings.celebrations:
            self.confetti.setGeometry(self.rect())
            self.confetti.burst(120 if result.perfect else 70)

        self.next_button.setFocus()

    def _tip_for(self, result: SessionResult) -> str:
        """One short, encouraging line. Never scolding."""
        if result.perfect:
            return "Not a single mistake. That was perfect typing!"
        if result.trouble_keys:
            names = [keymap.display_name(key) for key in result.trouble_keys[:2]]
            joined = " and ".join(name.upper() for name in names)
            return f"Keep an eye out for {joined} next time — you'll get it."
        if result.accuracy >= 0.9:
            return "So close to perfect. Great focus!"
        return "You finished the whole sentence. That's what counts."

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self.confetti.setGeometry(self.rect())

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.confetti.stop()
        super().hideEvent(event)
