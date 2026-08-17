"""Application entry point.

Start with ``python -m app.main`` during development, or launch the packaged
``Typing Adventure.app`` on macOS.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys

from app import APP_NAME, __version__
from app.config import Settings
from app.data.database import Database
from app.keyboard.manager import LightingManager
from app.paths import log_path


def configure_logging(verbose: bool = False) -> None:
    """Log to a file always, and to the console when asked.

    A packaged .app has nowhere to print, so the file is the only record when
    something goes wrong on a user's machine.
    """
    handlers: list[logging.Handler] = []
    try:
        handlers.append(logging.FileHandler(log_path(), encoding="utf-8"))
    except OSError:
        pass
    if verbose or not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="typing-adventure",
        description=f"{APP_NAME} - a keyboard learning game for kids.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument(
        "--no-lighting",
        action="store_true",
        help="skip hardware detection and use screen highlighting only",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="force a lighting backend (hidpp, openrgb, logitech-sdk, off)",
    )
    parser.add_argument(
        "--sentence", default=None, help="start immediately on this sentence"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    log = logging.getLogger("app")
    log.info("%s %s starting", APP_NAME, __version__)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is not installed.\n"
            "Install it with:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    from app.ui.main_window import MainWindow, apply_theme

    settings = Settings.load()
    database = Database()

    lighting = LightingManager()
    backend = args.backend or settings.lighting_backend
    if args.no_lighting or not settings.keyboard_lighting:
        backend = "off"
    lighting.start(backend)
    lighting.set_color(settings.lighting_color_rgb())
    lighting.blackout()
    for note in lighting.notes:
        log.info("lighting: %s", note)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Typing Adventure")
    apply_theme(app)

    window = MainWindow(settings, database, lighting)
    window.show()

    # Ctrl-C in a terminal should still restore the keyboard.
    def _interrupt(_signum, _frame):
        window.close()
        app.quit()

    signal.signal(signal.SIGINT, _interrupt)

    if args.sentence:
        window._start_sentence(args.sentence)

    try:
        return app.exec()
    finally:
        lighting.shutdown()
        database.close()
        log.info("%s exiting", APP_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
