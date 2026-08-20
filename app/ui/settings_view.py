"""Parent settings (handoff section 26).

Groups every switch a grown-up might want, plus custom sentences and a live
hardware panel that explains -- in words, not a status code -- what the
keyboard lighting is doing and why.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..audio.voice import list_voices
from ..config import Settings
from ..data.database import Database
from ..game.difficulty import Difficulty, profile_for
from . import theme
from .widgets import Card


def _section(title: str) -> QLabel:
    label = QLabel(title)
    label.setFont(theme.display_font(16, QFont.Weight.Black))
    label.setStyleSheet(f"color: {theme.ACCENT.name()}; margin-top: 8px;")
    return label


def _row(caption: str, widget: QWidget, hint: str = "") -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 4, 0, 4)

    text = QVBoxLayout()
    label = QLabel(caption)
    label.setFont(theme.display_font(14, QFont.Weight.DemiBold))
    text.addWidget(label)
    if hint:
        hint_label = QLabel(hint)
        hint_label.setFont(theme.display_font(11, QFont.Weight.Normal))
        hint_label.setStyleSheet(f"color: {theme.TEXT_MUTED.name()};")
        hint_label.setWordWrap(True)
        text.addWidget(hint_label)
    layout.addLayout(text, 1)
    layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
    return container


class SettingsView(QWidget):
    """Everything a parent can change, on one scrolling page."""

    closed = Signal()
    settings_changed = Signal()

    def __init__(
        self,
        settings: Settings,
        database: Database,
        lighting=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.database = database
        self.lighting = lighting
        self._loading = False
        self._build()
        self.reload()

    # -- construction ------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.setContentsMargins(32, 20, 32, 8)
        back = QPushButton("← Done")
        back.setObjectName("ghost")
        back.clicked.connect(self._on_done)
        header.addWidget(back)
        title = QLabel("Grown-up Settings")
        title.setFont(theme.display_font(22, QFont.Weight.Black))
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 8, 32, 32)
        layout.setSpacing(10)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # -- difficulty ----------------------------------------------------
        layout.addWidget(_section("How much help?"))
        self.difficulty_box = QComboBox()
        for level in Difficulty:
            self.difficulty_box.addItem(f"{level.label} — {level.blurb}", level.value)
        self.difficulty_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Difficulty", self.difficulty_box))

        self.shift_check = QCheckBox()
        self.shift_check.stateChanged.connect(self._on_change)
        layout.addWidget(
            _row(
                "Capitals need Shift",
                self.shift_check,
                "Off by default. Beginners find the letter key first; "
                "the Shift lesson comes later.",
            )
        )

        # -- feedback ------------------------------------------------------
        layout.addWidget(_section("Sound and voice"))

        self.all_caps_check = QCheckBox()
        self.all_caps_check.stateChanged.connect(self._on_change)
        layout.addWidget(_row("EVERYTHING CAPS", self.all_caps_check, "All sentences will be shown in UPPERCASE."))

        self.voice_check = QCheckBox()
        self.voice_check.stateChanged.connect(self._on_change)
        layout.addWidget(_row("Voice coaching", self.voice_check))

        self.voice_box = QComboBox()
        self.voice_box.addItem("System default", "")
        for name in list_voices():
            self.voice_box.addItem(name, name)
        self.voice_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Voice", self.voice_box))

        self.sound_box = QComboBox()
        for value, label in (("off", "Off"), ("gentle", "Gentle"), ("fun", "Fun")):
            self.sound_box.addItem(label, value)
        self.sound_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Sound effects", self.sound_box))

        self.correct_check = QCheckBox()
        self.correct_check.stateChanged.connect(self._on_change)
        layout.addWidget(_row("Sound on correct key", self.correct_check))

        self.wrong_check = QCheckBox()
        self.wrong_check.stateChanged.connect(self._on_change)
        layout.addWidget(
            _row("Sound on wrong key", self.wrong_check, "Always gentle, never harsh.")
        )

        self.celebration_check = QCheckBox()
        self.celebration_check.stateChanged.connect(self._on_change)
        layout.addWidget(_row("Celebrations", self.celebration_check))

        # -- attention -----------------------------------------------------
        layout.addWidget(_section("Focus reminders"))
        self.attention_box = QComboBox()
        for value, label in (
            (0.0, "Off"),
            (5.0, "After 5 seconds"),
            (8.0, "After 8 seconds"),
            (10.0, "After 10 seconds"),
        ):
            self.attention_box.addItem(label, value)
        self.attention_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(
            _row(
                "Remind if nothing happens",
                self.attention_box,
                "A quiet nudge, spaced out so it never nags.",
            )
        )

        # -- sensory -------------------------------------------------------
        layout.addWidget(_section("Look and feel"))
        self.animation_box = QComboBox()
        for value, label in (("none", "None"), ("gentle", "Gentle"), ("fun", "Fun")):
            self.animation_box.addItem(label, value)
        self.animation_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Animation", self.animation_box))

        self.onscreen_check = QCheckBox()
        self.onscreen_check.stateChanged.connect(self._on_change)
        layout.addWidget(
            _row(
                "Show the on-screen keyboard",
                self.onscreen_check,
                "Shows where the key lives, even without keyboard lighting.",
            )
        )

        self.highlight_style_box = QComboBox()
        for value, label in (("none", "None"), ("dock", "Dock Style"), ("separate", "Separate")):
            self.highlight_style_box.addItem(label, value)
        self.highlight_style_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Word highlight style", self.highlight_style_box))

        self.highlight_size_spin = QSpinBox()
        self.highlight_size_spin.setRange(16, 90)
        self.highlight_size_spin.valueChanged.connect(self._on_change)
        layout.addWidget(_row("Highlight font size", self.highlight_size_spin))

        self.baseline_size_spin = QSpinBox()
        self.baseline_size_spin.setRange(16, 90)
        self.baseline_size_spin.valueChanged.connect(self._on_change)
        layout.addWidget(_row("Baseline font size", self.baseline_size_spin))

        self.overflow_box = QComboBox()
        for value, label in (("wrap", "Word Wrap"), ("scroll", "Scroll")):
            self.overflow_box.addItem(label, value)
        self.overflow_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Sentence overflow", self.overflow_box))

        # -- hardware ------------------------------------------------------
        layout.addWidget(_section("Keyboard lighting"))
        self.lighting_check = QCheckBox()
        self.lighting_check.stateChanged.connect(self._on_change)
        layout.addWidget(_row("Light up the physical key", self.lighting_check))

        self.highlight_box = QComboBox()
        for value, label in (
            ("pulse", "Pulse (recommended)"),
            ("static", "Static"),
            ("blink", "Blink"),
            ("off", "Off"),
        ):
            self.highlight_box.addItem(label, value)
        self.highlight_box.currentIndexChanged.connect(self._on_change)
        layout.addWidget(_row("Highlight style", self.highlight_box))

        self.color_button = QPushButton()
        self.color_button.setFixedSize(36, 36)
        self.color_button.clicked.connect(self._pick_color)
        layout.addWidget(_row("Highlight color", self.color_button, "The color used for the target key."))

        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(36, 36)
        self.bg_color_button.clicked.connect(self._pick_bg_color)
        layout.addWidget(_row("Background color", self.bg_color_button, "The color used for all other keys. Black means off."))

        self.hardware_card = Card()
        hardware_layout = QVBoxLayout(self.hardware_card)
        hardware_layout.setContentsMargins(18, 14, 18, 14)
        self.hardware_label = QLabel("Checking…")
        self.hardware_label.setFont(theme.display_font(12, QFont.Weight.Normal))
        self.hardware_label.setWordWrap(True)
        self.hardware_label.setTextFormat(Qt.TextFormat.RichText)
        hardware_layout.addWidget(self.hardware_label)
        rescan = QPushButton("Check again")
        rescan.setObjectName("ghost")
        rescan.clicked.connect(self._rescan)
        hardware_layout.addWidget(rescan, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.hardware_card)

        # -- custom sentences ----------------------------------------------
        layout.addWidget(_section("Your own sentences"))
        entry_row = QHBoxLayout()
        self.sentence_input = QLineEdit()
        self.sentence_input.setPlaceholderText("Dad is making pancakes.")
        self.sentence_input.returnPressed.connect(self._add_sentence)
        entry_row.addWidget(self.sentence_input, 1)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_sentence)
        entry_row.addWidget(add_button)
        layout.addLayout(entry_row)

        self.sentence_list = QListWidget()
        self.sentence_list.setMaximumHeight(150)
        layout.addWidget(self.sentence_list)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        remove_button = QPushButton("Remove selected")
        remove_button.setObjectName("ghost")
        remove_button.clicked.connect(self._remove_sentence)
        remove_row.addWidget(remove_button)
        layout.addLayout(remove_row)

        self.custom_only_check = QCheckBox()
        self.custom_only_check.stateChanged.connect(self._on_change)
        layout.addWidget(
            _row("Use only my sentences", self.custom_only_check)
        )

        layout.addStretch(1)

    # -- data ---------------------------------------------------------------

    def reload(self) -> None:
        """Populate every control from the current settings."""
        self._loading = True
        settings = self.settings

        self._select(self.difficulty_box, settings.difficulty)
        self.shift_check.setChecked(settings.require_shift)
        self.all_caps_check.setChecked(settings.all_caps)
        self.voice_check.setChecked(settings.voice_cues)
        self._select(self.voice_box, settings.voice_name)
        self._select(self.sound_box, settings.sound_level)
        self.correct_check.setChecked(settings.correct_sound)
        self.wrong_check.setChecked(settings.wrong_sound)
        self.celebration_check.setChecked(settings.celebrations)
        self._select(
            self.attention_box,
            settings.attention_delay if settings.attention_cues else 0.0,
        )
        self._select(self.animation_box, settings.animation)
        self.onscreen_check.setChecked(settings.show_onscreen_keyboard)
        self._select(self.highlight_style_box, settings.word_highlight_style)
        self.highlight_size_spin.setValue(settings.highlight_font_size)
        self.baseline_size_spin.setValue(settings.baseline_font_size)
        self._select(self.overflow_box, settings.sentence_overflow)
        
        self.lighting_check.setChecked(settings.keyboard_lighting)
        self._select(self.highlight_box, settings.keyboard_highlight)
        
        # Style color button
        bg = settings.lighting_target_color
        self.color_button.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; border: 1px solid {theme.BORDER.name()}; border-radius: 18px; }}"
        )
        
        bg_color = settings.lighting_bg_color
        self.bg_color_button.setStyleSheet(
            f"QPushButton {{ background-color: {bg_color}; border: 1px solid {theme.BORDER.name()}; border-radius: 18px; }}"
        )
        
        self.custom_only_check.setChecked(settings.custom_only)

        self.sentence_list.clear()
        self.sentence_list.addItems(self.database.custom_sentences())

        self._refresh_hardware()
        self._loading = False

    @staticmethod
    def _select(box: QComboBox, value) -> None:
        index = box.findData(value)
        box.setCurrentIndex(index if index >= 0 else 0)

    def _on_change(self) -> None:
        if self._loading:
            return
        settings = self.settings
        settings.difficulty = self.difficulty_box.currentData()
        settings.require_shift = self.shift_check.isChecked()
        settings.all_caps = self.all_caps_check.isChecked()
        settings.voice_cues = self.voice_check.isChecked()
        settings.voice_name = self.voice_box.currentData() or ""
        settings.sound_level = self.sound_box.currentData()
        settings.correct_sound = self.correct_check.isChecked()
        settings.wrong_sound = self.wrong_check.isChecked()
        settings.celebrations = self.celebration_check.isChecked()

        delay = self.attention_box.currentData()
        settings.attention_cues = bool(delay)
        settings.attention_delay = float(delay or 5.0)

        settings.animation = self.animation_box.currentData()
        settings.show_onscreen_keyboard = self.onscreen_check.isChecked()
        settings.word_highlight_style = self.highlight_style_box.currentData()
        settings.highlight_font_size = self.highlight_size_spin.value()
        settings.baseline_font_size = self.baseline_size_spin.value()
        settings.sentence_overflow = self.overflow_box.currentData()
        
        settings.keyboard_lighting = self.lighting_check.isChecked()
        settings.keyboard_highlight = self.highlight_box.currentData()
        settings.custom_only = self.custom_only_check.isChecked()

        settings.save()
        self.settings_changed.emit()

    def _pick_color(self) -> None:
        initial = QColor(self.settings.lighting_target_color)
        color = QColorDialog.getColor(initial, self, "Pick Highlight Color")
        if color.isValid():
            self.settings.lighting_target_color = color.name()
            self.settings.save()
            self.settings_changed.emit()
            self.reload()
            if self.lighting:
                self.lighting.set_color(self.settings.lighting_color_rgb())

    def _pick_bg_color(self) -> None:
        initial = QColor(self.settings.lighting_bg_color)
        color = QColorDialog.getColor(initial, self, "Pick Background Color")
        if color.isValid():
            self.settings.lighting_bg_color = color.name()
            self.settings.save()
            self.settings_changed.emit()
            self.reload()
            if self.lighting:
                self.lighting.set_background_color(self.settings.lighting_bg_rgb())
                self.lighting.blackout()

    # -- hardware panel ----------------------------------------------------

    def _refresh_hardware(self) -> None:
        """Explain the lighting situation in plain language."""
        if self.lighting is None:
            self.hardware_label.setText("Keyboard lighting is not set up.")
            return

        available = self.lighting.available()
        if available:
            head = (
                f"<b style='color:{theme.SUCCESS.name()}'>Connected.</b> "
                f"{self.lighting.describe()}"
            )
        else:
            head = (
                f"<b style='color:{theme.WARNING.name()}'>No lighting hardware.</b> "
                "The game uses the on-screen keyboard instead — everything else "
                "works exactly the same."
            )

        notes = "<br>".join(f"• {note}" for note in self.lighting.notes)
        extra = (
            "<br><br><span style='color:#8C93AC'>Tried:</span><br>" + notes
            if notes
            else ""
        )
        gh = (
            "<br><br><span style='color:#8C93AC'>If you use Logitech G HUB, "
            "closing it while playing gives Type Scholar full control of "
            "the lights.</span>"
        )
        self.hardware_label.setText(head + extra + gh)

    def _rescan(self) -> None:
        if self.lighting is None:
            return
        self.lighting.shutdown()
        self.lighting.start(self.settings.lighting_backend)
        self._refresh_hardware()

    # -- custom sentences --------------------------------------------------

    def _add_sentence(self) -> None:
        text = self.sentence_input.text().strip()
        if not text:
            return
        if self.database.add_sentence(text):
            self.sentence_list.insertItem(0, text)
        self.sentence_input.clear()

    def _remove_sentence(self) -> None:
        item = self.sentence_list.currentItem()
        if item is None:
            return
        self.database.delete_sentence(item.text())
        self.sentence_list.takeItem(self.sentence_list.row(item))

    def _on_done(self) -> None:
        self.settings.save()
        self.closed.emit()

    def current_profile(self):
        return profile_for(self.settings.as_difficulty())
