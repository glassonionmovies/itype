"""The home screen: pick a category and start typing."""

from __future__ import annotations

import random

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Settings
from ..data import sentences as sentence_data
from ..data.database import Database
from . import theme
from .widgets import Card


class CategoryButton(QPushButton):
    """A large, colourful category tile."""

    def __init__(self, category: str, parent: QWidget | None = None) -> None:
        icon = sentence_data.CATEGORY_ICONS.get(category, "✏️")
        super().__init__(f"{icon}\n{category}", parent)
        self.category = category
        self.setCheckable(True)
        self.setMinimumHeight(96)
        self.setFont(theme.display_font(14, QFont.Weight.DemiBold))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        color = theme.category_color(category)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.SURFACE_LIGHT.name()};
                border: 2px solid {theme.BORDER.name()};
                border-radius: 18px;
                font-size: 15px;
                padding: 10px;
            }}
            QPushButton:hover {{ border-color: {color.name()}; }}
            QPushButton:checked {{
                background: {color.darker(240).name()};
                border-color: {color.name()};
                color: {color.lighter(140).name()};
            }}
            """
        )


class HomeView(QWidget):
    """Category picker and entry point to the other screens."""

    play_requested = Signal(str)
    settings_requested = Signal()
    free_play_requested = Signal()

    def __init__(
        self,
        settings: Settings,
        database: Database,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.database = database
        self._buttons: list[CategoryButton] = []
        self._last_sentence: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 36)
        root.setSpacing(18)

        title = QLabel("🐵  Typing Adventure")
        title.setFont(theme.display_font(40, QFont.Weight.Black))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("Find the letter. Press the key. You've got this.")
        subtitle.setFont(theme.display_font(16, QFont.Weight.Normal))
        subtitle.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        root.addSpacing(6)

        # Progress summary.
        self.progress_card = Card()
        progress_layout = QHBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(24, 16, 24, 16)
        self._stat_labels: dict[str, QLabel] = {}
        for key, caption in (
            ("sentences", "Sentences"),
            ("stars", "Stars"),
            ("accuracy", "Accuracy"),
            ("perfect", "Perfect"),
        ):
            block = QVBoxLayout()
            value = QLabel("—")
            value.setFont(theme.display_font(26, QFont.Weight.Black))
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption_label = QLabel(caption)
            caption_label.setFont(theme.display_font(11, QFont.Weight.Normal))
            caption_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
            caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block.addWidget(value)
            block.addWidget(caption_label)
            progress_layout.addLayout(block, 1)
            self._stat_labels[key] = value
        root.addWidget(self.progress_card)

        root.addSpacing(4)

        pick_label = QLabel("Pick something to type about")
        pick_label.setFont(theme.display_font(15, QFont.Weight.DemiBold))
        pick_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        root.addWidget(pick_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        categories = ["Surprise me!", *sentence_data.CATEGORIES]
        for index, category in enumerate(categories):
            if category == "Surprise me!":
                button = CategoryButton("Funny")
                button.setText("🎲\nSurprise me!")
                button.category = ""
            else:
                button = CategoryButton(category)
            button.clicked.connect(
                lambda _checked, b=button: self._select(b)
            )
            grid.addWidget(button, index // 4, index % 4)
            self._buttons.append(button)
        root.addLayout(grid)

        root.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.settings_button = QPushButton("⚙  Grown-ups")
        self.settings_button.setObjectName("ghost")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        actions.addWidget(self.settings_button)

        self.free_play_button = QPushButton("🎈  Free Play")
        self.free_play_button.clicked.connect(self.free_play_requested.emit)
        actions.addWidget(self.free_play_button)

        actions.addStretch(1)

        self.play_button = QPushButton("Start Typing  →")
        self.play_button.setObjectName("primary")
        self.play_button.clicked.connect(self._start)
        self.play_button.setDefault(True)
        actions.addWidget(self.play_button)

        root.addLayout(actions)

    # -- behaviour ---------------------------------------------------------

    def _select(self, chosen: CategoryButton) -> None:
        for button in self._buttons:
            button.setChecked(button is chosen)
        self.settings.category = chosen.category
        self.settings.save()

    def _start(self) -> None:
        self.play_requested.emit(self.next_sentence())

    def next_sentence(self) -> str:
        """Choose the next sentence, honouring category and level settings."""
        pool: list[str] = []
        if self.settings.custom_only:
            pool = self.database.custom_sentences()
        if not pool:
            custom = self.database.custom_sentences()
            entry = sentence_data.random_entry(
                category=self.settings.category or None,
                level=self.settings.level or None,
                exclude=self._last_sentence,
            )
            pool = [entry.text]
            # Give parent-written sentences a healthy share of the rotation.
            if custom and not self.settings.category and random.random() < 0.3:
                pool = [random.choice(custom)]

        choice = random.choice(pool) if pool else "Monkey is jumping."
        self._last_sentence = choice
        return choice

    def refresh(self) -> None:
        """Re-read progress numbers and restore the selected category."""
        summary = self.database.summary()
        self._stat_labels["sentences"].setText(str(summary.total_sessions))
        self._stat_labels["stars"].setText(str(summary.total_stars))
        accuracy = (
            f"{round(summary.average_accuracy * 100)}%"
            if summary.total_sessions
            else "—"
        )
        self._stat_labels["accuracy"].setText(accuracy)
        self._stat_labels["perfect"].setText(str(summary.perfect_sentences))

        for button in self._buttons:
            button.setChecked(button.category == self.settings.category)
