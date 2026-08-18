"""The main window: owns the views and the navigation between them."""

from __future__ import annotations

import logging
import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from ..audio.feedback import FeedbackBundle, SessionFeedback
from ..config import Settings
from ..data import sentences as sentence_data
from ..data.database import Database
from ..keyboard.manager import LightingManager
from . import theme
from .game_view import GameView
from .home_view import HomeView
from .freetype_view import FreeTypeView
from .results_view import ResultsView
from .settings_view import SettingsView

log = logging.getLogger(__name__)

HOME, GAME, RESULTS, SETTINGS, FREE_TYPE = range(5)


class MainWindow(QMainWindow):
    """Hosts the four screens and keeps shared services alive."""

    def __init__(
        self,
        settings: Settings,
        database: Database,
        lighting: LightingManager,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.database = database
        self.lighting = lighting
        self.feedback_bundle = FeedbackBundle(settings)
        self.session_feedback = SessionFeedback(self.feedback_bundle)

        self.setWindowTitle("Typing Adventure")
        self.resize(1120, 760)
        self.setMinimumSize(880, 620)

        self._current_sentence = ""
        self._free_play = False

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_view = HomeView(settings, database)
        self.game_view = GameView(
            settings, lighting=lighting, feedback=self._game_feedback()
        )
        self.results_view = ResultsView(settings)
        self.settings_view = SettingsView(settings, database, lighting)
        self.free_type_view = FreeTypeView(voice=self.feedback_bundle.voice)

        for view in (
            self.home_view,
            self.game_view,
            self.results_view,
            self.settings_view,
            self.free_type_view,
        ):
            self.stack.addWidget(view)

        self._connect()
        self._apply_settings()
        self.stack.setCurrentIndex(HOME)

    def _game_feedback(self):
        """Adapter the game view hands to the session.

        Exposes ``play(name)`` for the session and ``voice`` plus
        ``play_complete`` for the view itself.
        """
        bundle = self.feedback_bundle
        feedback = self.session_feedback

        class _Adapter:
            voice = bundle.voice

            @staticmethod
            def play(name: str) -> None:
                feedback.play(name)

            @staticmethod
            def play_complete(perfect: bool = False) -> None:
                bundle.play_complete(perfect)

        return _Adapter()

    # -- wiring ------------------------------------------------------------

    def _connect(self) -> None:
        self.home_view.play_requested.connect(self._start_sentence)
        self.home_view.settings_requested.connect(self._open_settings)
        self.home_view.free_play_requested.connect(self._start_free_play)
        self.home_view.free_type_requested.connect(self._start_free_type)

        self.game_view.finished.connect(self._on_finished)
        self.game_view.quit_requested.connect(self._go_home)

        self.results_view.next_requested.connect(self._next_sentence)
        self.results_view.repeat_requested.connect(self._repeat_sentence)
        self.results_view.home_requested.connect(self._go_home)

        self.settings_view.closed.connect(self._go_home)
        self.settings_view.settings_changed.connect(self._apply_settings)

        self.free_type_view.quit_requested.connect(self._go_home)

    def _apply_settings(self) -> None:
        """Push settings changes into the live services."""
        self.feedback_bundle.apply(self.settings)
        # The adapter captured the old voice object; rebuild it.
        self.game_view.feedback = self._game_feedback()
        self.game_view.settings = self.settings
        self.free_type_view.update_voice(self.feedback_bundle.voice)

        self.lighting.set_mode(self.settings.keyboard_highlight)
        if not self.settings.keyboard_lighting:
            self.lighting.blackout()

    # -- navigation --------------------------------------------------------

    def _start_sentence(self, text: str) -> None:
        self._current_sentence = text
        self.stack.setCurrentIndex(GAME)
        self.game_view.start(text)

    def _start_free_play(self) -> None:
        """A single fun word, with an emoji reward (handoff section 27)."""
        word, _icon = random.choice(sentence_data.FREE_PLAY_WORDS)
        self._free_play = True
        self._start_sentence(word)

    def _start_free_type(self) -> None:
        self.free_type_view.update_voice(self.feedback_bundle.voice)
        self.free_type_view.start()
        self.stack.setCurrentIndex(FREE_TYPE)

    def _next_sentence(self) -> None:
        if self._free_play:
            self._start_free_play()
            return
        self._start_sentence(self.home_view.next_sentence())

    def _repeat_sentence(self) -> None:
        self._start_sentence(self._current_sentence)

    def _on_finished(self, result) -> None:
        try:
            self.database.record_session(result)
        except Exception as exc:  # persistence must never lose the celebration
            log.warning("could not save session: %s", exc)
        self.lighting.blackout()
        self.results_view.show_result(result)
        self.stack.setCurrentIndex(RESULTS)
        self.home_view.refresh()

    def _open_settings(self) -> None:
        self.settings_view.reload()
        self.stack.setCurrentIndex(SETTINGS)

    def _go_home(self) -> None:
        self._free_play = False
        self.game_view.stop()
        self.free_type_view.stop()
        self.lighting.blackout()
        self.home_view.refresh()
        self.stack.setCurrentIndex(HOME)

    # -- shutdown ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        """Hand the keyboard back before the window disappears."""
        try:
            self.game_view.stop()
            self.free_type_view.stop()
            self.feedback_bundle.shutdown()
            self.lighting.shutdown()
            self.database.close()
        except Exception as exc:
            log.warning("shutdown problem: %s", exc)
        super().closeEvent(event)


def apply_theme(app) -> None:
    """Apply the application-wide palette and stylesheet."""
    app.setStyleSheet(theme.STYLESHEET)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
