"""The home screen: pick a category and start typing."""

from __future__ import annotations

import random

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap, QColor
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


def _build_icon(emoji: str, base_color: QColor) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw faded background circle
    bg_color = QColor(base_color)
    bg_color.setAlphaF(0.2)
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, 64, 64)
    
    # Draw emoji centered
    painter.setPen(theme.TEXT)
    painter.setFont(theme.display_font(32))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)

class CategoryButton(QPushButton):
    """A large, colourful category tile."""

    def __init__(self, category: str, parent: QWidget | None = None) -> None:
        emoji = sentence_data.CATEGORY_ICONS.get(category, "🐶")
        super().__init__(f"  {category}", parent)
        self.category = category
        self.setCheckable(True)
        self.setMinimumHeight(84)
        self.setFont(theme.display_font(18, QFont.Weight.Medium))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        color = theme.category_color(category)
        
        self.setIcon(_build_icon(emoji, color))
        self.setIconSize(QPixmap(48, 48).size())
        
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.SURFACE.name()};
                border: 1px solid {theme.BORDER.name()};
                border-radius: 12px;
                text-align: left;
                padding-left: 16px;
                color: {theme.TEXT.name()};
            }}
            QPushButton:hover {{ border-color: {theme.TEXT_FAINT.name()}; }}
            QPushButton:checked {{
                background: {theme.BLUE.lighter(170).name()};
                border: 2px solid {theme.BLUE.name()};
            }}
            """
        )


class HomeView(QWidget):
    """Category picker and entry point to the other screens."""

    play_requested = Signal(str)
    settings_requested = Signal()
    free_play_requested = Signal()
    free_type_requested = Signal()

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

        title_html = (
            f"<span style='color:{theme.BLUE.name()}'>Typing </span>"
            f"<span style='color:{theme.RED.name()}'>A</span>"
            f"<span style='color:{theme.BLUE.name()}'>d</span>"
            f"<span style='color:{theme.YELLOW.name()}'>v</span>"
            f"<span style='color:{theme.BLUE.name()}'>e</span>"
            f"<span style='color:{theme.GREEN.name()}'>n</span>"
            f"<span style='color:{theme.BLUE.name()}'>t</span>"
            f"<span style='color:{theme.GREEN.name()}'>u</span>"
            f"<span style='color:{theme.RED.name()}'>r</span>"
            f"<span style='color:{theme.YELLOW.name()}'>e</span>"
        )
        title = QLabel(title_html)
        title.setFont(theme.display_font(48, QFont.Weight.Black))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("Find the letter. Press the key. You've got this.")
        subtitle.setFont(theme.display_font(18, QFont.Weight.Medium))
        subtitle.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        root.addSpacing(6)

        # -- Free Type hero button (top option) ----------------------------
        free_type_btn = QPushButton("\u270f\ufe0f   Free Type  \u2014  Write your own sentence")
        free_type_btn.setObjectName("primary")
        free_type_btn.setMinimumHeight(64)
        free_type_btn.setFont(theme.display_font(20, QFont.Weight.DemiBold))
        free_type_btn.clicked.connect(self.free_type_requested.emit)
        root.addWidget(free_type_btn)

        root.addSpacing(4)

        # Progress summary.
        self.progress_card = Card()
        progress_layout = QHBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(24, 16, 24, 16)
        self._stat_labels: dict[str, QLabel] = {}
        for key, caption, color in (
            ("sentences", "SENTENCES", theme.BLUE),
            ("stars", "STARS", theme.YELLOW),
            ("accuracy", "ACCURACY", theme.GREEN),
            ("perfect", "PERFECT", theme.RED),
        ):
            block = QVBoxLayout()
            value = QLabel("—")
            value.setFont(theme.display_font(34, QFont.Weight.Black))
            value.setStyleSheet(f"color: {color.name()};")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            caption_label = QLabel(caption)
            caption_label.setFont(theme.display_font(13, QFont.Weight.Bold))
            caption_label.setStyleSheet(f"color: {color.name()}; letter-spacing: 1px;")
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
                button = CategoryButton("Surprise me!")
                # Override icon for surprise me
                button.setIcon(_build_icon("🎲", theme.BLUE))
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

        # Custom Sentences category: use only user-added sentences
        if self.settings.category == sentence_data.CUSTOM or self.settings.custom_only:
            pool = self.database.custom_sentences()
            if not pool:
                pool = ["Add sentences in Grown-ups settings."]

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
