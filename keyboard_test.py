#!/usr/bin/env python3
"""Logitech PRO X 60 hardware test utility.

Run this the moment the keyboard arrives. It answers, in order, the questions
that decide whether per-key lighting is usable:

1. Does macOS see the keyboard at all, and on which interfaces?
2. Can we open the vendor (HID++) interface without root?
3. Does the device answer HID++ and report feature 0x8081?
4. Does a single key actually light up?
5. Does M -> O -> N -> K -> E -> Y run cleanly in sequence?

Usage::

    python3 keyboard_test.py            # interactive menu
    python3 keyboard_test.py --scan     # enumerate and exit
    python3 keyboard_test.py --monkey   # run the MONKEY test and exit
    python3 keyboard_test.py --calibrate

The calibration mode matters. Solaar's per-key zone table is overridable per
device, so the zone-ID encoding is not guaranteed to be identical on the
PRO X 60. Calibration walks the IDs one at a time and lets you record which
one lights which physical key, turning a guess into a measurement.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from app.keyboard import hid as hid_scan  # noqa: E402
from app.keyboard.base import DIM_COLOR, TARGET_COLOR  # noqa: E402
from app.keyboard.hidpp import (  # noqa: E402
    ZONE_SCHEMES,
    HidppKeyboardLighting,
)
from app.keyboard.manager import detect  # noqa: E402

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[36m"
RESET = "\033[0m"


def colour(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{RESET}"


def header(title: str) -> None:
    line = "=" * 60
    print(f"\n{colour(line, BLUE)}")
    print(colour(f" {title}", BOLD))
    print(colour(line, BLUE))


def ok(message: str) -> None:
    print(f"  {colour('[OK]', GREEN)}   {message}")


def warn(message: str) -> None:
    print(f"  {colour('[WARN]', YELLOW)} {message}")


def fail(message: str) -> None:
    print(f"  {colour('[FAIL]', RED)} {message}")


def info(message: str) -> None:
    print(f"  {colour('[..]', DIM)}   {message}")


# -- step 1: environment ---------------------------------------------------


def show_environment() -> None:
    header("Environment")
    print(f"  Platform     : {platform.system()} {platform.release()}")
    print(f"  Architecture : {platform.machine()}")
    print(f"  Python       : {platform.python_version()}")

    if platform.system() != "Darwin":
        warn("Not running on macOS. Results here will not reflect the target Mac.")

    try:
        import hid  # noqa: F401

        ok("hidapi is installed")
    except ImportError:
        fail("hidapi is NOT installed. Run: pip install hidapi")

    if platform.system() == "Darwin":
        try:
            running = subprocess.run(
                ["pgrep", "-x", "lghub"], capture_output=True, timeout=4
            )
            if running.returncode == 0:
                warn(
                    "Logitech G HUB is running. It may own the lighting. "
                    "Quit it for the cleanest test."
                )
            else:
                ok("Logitech G HUB does not appear to be running")
        except (OSError, subprocess.SubprocessError):
            pass


# -- step 2: enumeration ---------------------------------------------------


def show_devices(verbose: bool = True) -> hid_scan.HidScan:
    header("HID enumeration")
    scan = hid_scan.scan(hid_scan.LOGITECH_VENDOR_ID)

    if not scan.available:
        fail(scan.error)
        return scan

    if not scan.interfaces:
        fail("No Logitech devices found.")
        info("Check: is the keyboard plugged in by USB, or the receiver seated?")
        return scan

    ok(f"Found {len(scan.interfaces)} Logitech HID interface(s)")
    for interface in scan.interfaces:
        marker = colour(" <-- HID++ vendor interface", GREEN) if interface.likely_hidpp else ""
        print(f"    • {interface.describe()}{marker}")

    if verbose:
        for interface in scan.hidpp_capable:
            print()
            print(colour("  Vendor interface detail:", BOLD))
            for key, value in interface.as_report().items():
                print(f"    {key:<16}: {value}")
            opened, reason = hid_scan.probe_open(interface)
            (ok if opened else fail)(f"open: {reason}")

    if not scan.hidpp_capable:
        fail("No vendor (0xFF00) interface found -- per-key lighting needs it.")
        info("Try the other transport: USB cable vs LIGHTSPEED receiver.")
    return scan


# -- step 3: lighting ------------------------------------------------------


def connect_backend(scheme: str = "hid-3") -> HidppKeyboardLighting | None:
    header("Connecting to per-key lighting")
    backend = HidppKeyboardLighting(zone_scheme=scheme)
    if backend.connect():
        ok(f"Connected: {backend.describe()}")
        device = backend.device
        if device:
            for key, value in device.extra.items():
                print(f"    {key:<14}: {value}")
        return backend
    fail(backend.last_error)
    return None


def test_all_off(backend) -> None:
    info("All keys -> dim")
    backend.set_all(DIM_COLOR)
    backend.flush()


def test_light(backend, letter: str, seconds: float = 1.2) -> None:
    info(f"Lighting {letter}")
    backend.focus_key(letter, TARGET_COLOR)
    time.sleep(seconds)


def test_sequence(backend, word: str = "MONKEY", delay: float = 0.7) -> None:
    header(f"Sequence test: {word}")
    for letter in word:
        key = letter.upper()
        if letter == " ":
            info("space -- nothing to light")
            backend.set_all(DIM_COLOR)
            backend.flush()
        else:
            info(f"{key} bright, everything else dim")
            backend.focus_key(key, TARGET_COLOR)
        time.sleep(delay)
    backend.set_all(DIM_COLOR)
    backend.flush()
    ok("Sequence finished")


def test_endurance(backend, count: int = 25, delay: float = 0.12) -> None:
    """Handoff test 7: many changes without losing synchronisation."""
    header(f"Endurance: {count} rapid changes")
    letters = "MONKEYISJUMPING"
    start = time.monotonic()
    for i in range(count):
        backend.focus_key(letters[i % len(letters)], TARGET_COLOR)
        time.sleep(delay)
    elapsed = time.monotonic() - start
    backend.set_all(DIM_COLOR)
    backend.flush()
    ok(f"{count} updates in {elapsed:.1f}s ({count / elapsed:.1f}/s)")
    print("  Did every change appear, in order, with no stuck keys? (y/n)")


def calibrate(backend, start: int = 1, end: int = 60) -> None:
    """Walk raw zone IDs so the real mapping can be recorded.

    The zone-ID encoding is the one part of this protocol that is genuinely
    device-specific, so it is worth measuring rather than assuming.
    """
    header("Zone calibration")
    print(
        "  Each step lights ONE zone ID. Write down which physical key\n"
        "  lights up for each number. Press Enter to step, 'q' to stop.\n"
    )
    mapping: dict[int, str] = {}
    for zone in range(start, end + 1):
        backend.paint_zone(zone, TARGET_COLOR)
        answer = input(f"  zone {zone:>3} -> which key lit up? (Enter to skip, q) ")
        if answer.strip().lower() == "q":
            break
        if answer.strip():
            mapping[zone] = answer.strip().upper()

    backend.set_all(DIM_COLOR)
    backend.flush()

    if mapping:
        header("Recorded mapping")
        for zone, key in sorted(mapping.items()):
            print(f"    {zone:>3} : {key}")
        print(
            "\n  Compare against the built-in scheme with:\n"
            "    python3 -c \"from app.keyboard.hidpp import zone_id_hid_minus_3 as z;"
            " print({k: z(k) for k in 'MONKEY'})\""
        )


# -- interactive menu ------------------------------------------------------

MENU = """
================================
 Logitech PRO X 60 Test
================================

  Device detected: {detected}
  Backend        : {backend}

  [1] Environment + enumerate devices
  [2] All keys off
  [3] Light M
  [4] Light O
  [5] Light N
  [6] Test MONKEY
  [7] Test "MONKEY IS JUMPING."
  [8] Endurance test (25 changes)
  [9] Calibrate zone IDs
  [s] Switch zone scheme (current: {scheme})
  [r] Reconnect
  [0] Restore keyboard
  [q] Quit
"""


def interactive() -> int:
    show_environment()
    show_devices()

    scheme = "hid-3"
    backend = connect_backend(scheme)

    try:
        while True:
            detected = (
                colour("YES", GREEN) if backend and backend.connected else colour("NO", RED)
            )
            name = backend.describe() if backend else "none (screen-only fallback)"
            print(MENU.format(detected=detected, backend=name, scheme=scheme))

            choice = input("  > ").strip().lower()

            if choice == "q":
                break
            if choice == "1":
                show_environment()
                show_devices()
                continue
            if choice == "r":
                if backend:
                    backend.restore()
                backend = connect_backend(scheme)
                continue
            if choice == "s":
                options = list(ZONE_SCHEMES)
                scheme = options[(options.index(scheme) + 1) % len(options)]
                print(f"  Zone scheme is now: {scheme}")
                if backend:
                    backend.set_zone_scheme(scheme)
                continue

            if backend is None or not backend.connected:
                fail("Not connected. Use [r] to retry, or [1] to inspect devices.")
                continue

            if choice == "2":
                test_all_off(backend)
            elif choice == "3":
                test_light(backend, "M")
            elif choice == "4":
                test_light(backend, "O")
            elif choice == "5":
                test_light(backend, "N")
            elif choice == "6":
                test_sequence(backend, "MONKEY")
            elif choice == "7":
                test_sentence(backend, "MONKEY IS JUMPING.")
            elif choice == "8":
                test_endurance(backend)
            elif choice == "9":
                calibrate(backend)
            elif choice == "0":
                backend.restore()
                ok("Keyboard restored")
            else:
                print("  Unknown option.")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        if backend:
            backend.restore()
            ok("Keyboard restored on exit")
    return 0


def test_sentence(backend, text: str, delay: float = 0.5) -> None:
    """Walk a full sentence, including spaces and punctuation."""
    from app.keyboard import keymap

    header(f"Sentence test: {text}")
    for char in text:
        key = keymap.key_name_for_char(char)
        if key is None:
            info(f"{char!r}: no physical key, skipping")
            continue
        if key == "SPACE":
            info("space -> spacebar")
        else:
            info(f"{char!r} -> {key}")
        backend.focus_key(key, TARGET_COLOR)
        time.sleep(delay)
    backend.set_all(DIM_COLOR)
    backend.flush()
    ok("Sentence finished")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scan", action="store_true", help="enumerate and exit")
    parser.add_argument("--monkey", action="store_true", help="run MONKEY and exit")
    parser.add_argument("--sentence", metavar="TEXT", help="walk a sentence and exit")
    parser.add_argument("--calibrate", action="store_true", help="zone calibration")
    parser.add_argument(
        "--scheme", default="hid-3", choices=list(ZONE_SCHEMES), help="zone encoding"
    )
    parser.add_argument(
        "--auto", action="store_true", help="probe every backend the game would try"
    )
    args = parser.parse_args(argv)

    if args.auto:
        show_environment()
        header("Backend auto-detection (same order the game uses)")
        backend, notes = detect("auto")
        for note in notes:
            print(f"  • {note}")
        (ok if backend.available() else warn)(backend.describe())
        backend.restore()
        return 0

    if args.scan:
        show_environment()
        scan = show_devices()
        return 0 if scan.hidpp_capable else 1

    if args.monkey or args.sentence or args.calibrate:
        show_environment()
        show_devices(verbose=False)
        backend = connect_backend(args.scheme)
        if backend is None:
            fail("Cannot run: no per-key lighting available.")
            return 1
        try:
            if args.calibrate:
                calibrate(backend)
            elif args.sentence:
                test_sentence(backend, args.sentence)
            else:
                test_sequence(backend, "MONKEY")
        finally:
            backend.restore()
            ok("Keyboard restored")
        return 0

    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
