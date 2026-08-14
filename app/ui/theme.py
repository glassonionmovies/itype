"""Colours, fonts and the application stylesheet.

Playful but uncluttered (handoff section 30). The palette is deliberately
low-contrast in the background and high-contrast on the one thing that
matters -- the current letter -- so a child's eye is pulled to the target
without the screen shouting everywhere at once.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase

# -- palette ---------------------------------------------------------------

BACKGROUND = QColor("#151824")
SURFACE = QColor("#1E2233")
SURFACE_LIGHT = QColor("#272C40")
BORDER = QColor("#333950")

TEXT = QColor("#EEF1FA")
TEXT_MUTED = QColor("#8C93AC")
TEXT_FAINT = QColor("#5A6079")

ACCENT = QColor("#4FA8FF")
ACCENT_SOFT = QColor("#2D6699")
SUCCESS = QColor("#4BE08C")
WARNING = QColor("#FFAA3C")
DANGER = QColor("#FF6B6B")
GOLD = QColor("#FFD24A")
PURPLE = QColor("#A78BFA")

#: Character states on the sentence strip.
CHAR_PENDING = TEXT_FAINT
CHAR_CURRENT = QColor("#FFFFFF")
CHAR_CORRECT = SUCCESS

CATEGORY_COLORS = {
    "Animals": QColor("#4BE08C"),
    "Family": QColor("#FFAA3C"),
    "Food": QColor("#FF6B6B"),
    "Activities": QColor("#4FA8FF"),
    "Objects": QColor("#A78BFA"),
    "Funny": QColor("#F472B6"),
    "Nature": QColor("#34D399"),
    "Custom": QColor("#FFD24A"),
}


def category_color(name: str) -> QColor:
    return CATEGORY_COLORS.get(name, ACCENT)


# -- fonts -----------------------------------------------------------------

#: Preferred display faces, in order. A rounded face reads as friendly; we
#: fall back through the usual macOS stack rather than shipping a font.
DISPLAY_FAMILIES = (
    "SF Pro Rounded",
    "Avenir Next",
    "Nunito",
    "Helvetica Neue",
    "Segoe UI",
    "DejaVu Sans",
)

#: The sentence strip needs even advance widths so letters do not shuffle
#: sideways as they change weight.
MONO_FAMILIES = (
    "SF Mono",
    "Menlo",
    "JetBrains Mono",
    "DejaVu Sans Mono",
    "Courier New",
)


def _first_available(families: tuple[str, ...]) -> str:
    installed = set(QFontDatabase.families())
    for family in families:
        if family in installed:
            return family
    return families[-1]


_display_family: str | None = None
_mono_family: str | None = None


def display_font(size: int, weight: QFont.Weight = QFont.Weight.Bold) -> QFont:
    global _display_family
    if _display_family is None:
        _display_family = _first_available(DISPLAY_FAMILIES)
    font = QFont(_display_family, size)
    font.setWeight(weight)
    return font


def mono_font(size: int, weight: QFont.Weight = QFont.Weight.Medium) -> QFont:
    global _mono_family
    if _mono_family is None:
        _mono_family = _first_available(MONO_FAMILIES)
    font = QFont(_mono_family, size)
    font.setWeight(weight)
    return font


# -- stylesheet ------------------------------------------------------------

STYLESHEET = f"""
QWidget {{
    background: {BACKGROUND.name()};
    color: {TEXT.name()};
}}

QLabel {{
    background: transparent;
}}

QPushButton {{
    background: {SURFACE_LIGHT.name()};
    color: {TEXT.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 14px;
    padding: 12px 22px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {BORDER.name()};
    border-color: {ACCENT_SOFT.name()};
}}
QPushButton:pressed {{
    background: {SURFACE.name()};
}}
QPushButton:disabled {{
    color: {TEXT_FAINT.name()};
    background: {SURFACE.name()};
}}

QPushButton#primary {{
    background: {ACCENT.name()};
    color: #0C1220;
    border: none;
    font-size: 17px;
    font-weight: 700;
    padding: 15px 34px;
}}
QPushButton#primary:hover {{
    background: #6FBAFF;
}}
QPushButton#primary:pressed {{
    background: {ACCENT_SOFT.name()};
}}

QPushButton#ghost {{
    background: transparent;
    border: 1px solid {BORDER.name()};
    color: {TEXT_MUTED.name()};
}}
QPushButton#ghost:hover {{
    color: {TEXT.name()};
    border-color: {ACCENT_SOFT.name()};
}}

QFrame#card {{
    background: {SURFACE.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 20px;
}}

QComboBox, QSpinBox, QLineEdit {{
    background: {SURFACE_LIGHT.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 14px;
    min-height: 20px;
}}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
    border-color: {ACCENT.name()};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_LIGHT.name()};
    border: 1px solid {BORDER.name()};
    selection-background-color: {ACCENT_SOFT.name()};
    outline: none;
}}

QCheckBox {{
    font-size: 14px;
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 22px;
    height: 22px;
    border-radius: 7px;
    border: 2px solid {BORDER.name()};
    background: {SURFACE_LIGHT.name()};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT.name()};
    border-color: {ACCENT.name()};
}}

QScrollArea {{
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER.name()};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_FAINT.name()};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QListWidget {{
    background: {SURFACE_LIGHT.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 12px;
    padding: 6px;
    font-size: 14px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background: {ACCENT_SOFT.name()};
    color: {TEXT.name()};
}}

QToolTip {{
    background: {SURFACE_LIGHT.name()};
    color: {TEXT.name()};
    border: 1px solid {BORDER.name()};
    padding: 6px;
    border-radius: 6px;
}}
"""
