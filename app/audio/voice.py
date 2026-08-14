"""Verbal coaching through the operating system's local speech engine.

macOS ``say`` is used directly. No cloud speech, no API key, no network
(handoff sections 19 and 29).

Speech runs on a worker thread. The important behaviour is that a *priority*
line cancels whatever is currently being spoken: when a child presses a wrong
key, "Oops, we're looking for O" has to interrupt the tail of the previous
cue, not queue up behind it.
"""

from __future__ import annotations

import logging
import queue
import shutil
import subprocess
import sys
import threading

log = logging.getLogger(__name__)


def _detect_engine() -> tuple[str, list[str]] | None:
    """Find a local text-to-speech command.

    Returns the executable and the argument prefix, or ``None`` when the
    machine has no local voice, in which case coaching silently degrades to
    on-screen text.
    """
    if sys.platform == "darwin" and shutil.which("say"):
        return "say", []
    for command in ("espeak-ng", "espeak"):
        if shutil.which(command):
            return command, []
    if shutil.which("spd-say"):
        return "spd-say", ["-e"]
    return None


class VoiceCoach:
    """Speaks short coaching lines, newest-first when it matters."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        rate: int = 170,
        voice: str = "",
    ) -> None:
        self.enabled = enabled
        self.rate = rate
        self.voice = voice
        self._engine = _detect_engine()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stopped = threading.Event()
        if self.available:
            self._start()

    @property
    def available(self) -> bool:
        return self._engine is not None

    @property
    def engine_name(self) -> str:
        return self._engine[0] if self._engine else "none"

    def _start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="voice-coach", daemon=True
        )
        self._thread.start()

    # -- public API --------------------------------------------------------

    def say(self, text: str, *, priority: bool = False) -> None:
        """Speak *text*.

        ``priority`` cancels current speech and clears anything queued, which
        is what makes corrections feel responsive rather than laggy.
        """
        if not (self.enabled and self.available and text):
            return
        if priority:
            self.stop_current()
            self._drain()
        self._queue.put(text)

    def stop_current(self) -> None:
        """Kill in-flight speech without shutting the coach down."""
        with self._process_lock:
            process = self._process
            self._process = None
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def shutdown(self) -> None:
        self._stopped.set()
        self.stop_current()
        self._drain()
        self._queue.put(None)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

    # -- worker ------------------------------------------------------------

    def _drain(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _command(self, text: str) -> list[str]:
        assert self._engine is not None
        name, prefix = self._engine
        if name == "say":
            command = ["say", "-r", str(int(self.rate))]
            if self.voice:
                command += ["-v", self.voice]
            return command + [text]
        if name.startswith("espeak"):
            # espeak's rate is words-per-minute like `say`, close enough.
            return [name, "-s", str(int(self.rate)), text]
        return [name, *prefix, text]

    def _run(self) -> None:
        while not self._stopped.is_set():
            text = self._queue.get()
            if text is None:
                return
            try:
                process = subprocess.Popen(
                    self._command(text),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, ValueError) as exc:
                log.info("speech failed: %s", exc)
                continue
            with self._process_lock:
                self._process = process
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
            finally:
                with self._process_lock:
                    if self._process is process:
                        self._process = None


def list_voices() -> list[str]:
    """Available macOS voice names, for the settings screen."""
    if sys.platform != "darwin" or not shutil.which("say"):
        return []
    try:
        output = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    voices = []
    for line in output.splitlines():
        # Format: "Samantha           en_US    # Hello, my name is Samantha."
        parts = line.split()
        if len(parts) >= 2 and "_" in parts[1]:
            voices.append(parts[0])
    return voices


class NullVoice:
    """Stand-in used when speech is switched off, and in tests."""

    available = False
    engine_name = "none"

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def say(self, text: str, *, priority: bool = False) -> None:
        self.spoken.append(text)

    def stop_current(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
