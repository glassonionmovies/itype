# 🐵 Type Scholar

A typing and hand-eye coordination game for a child learning the keyboard.

The screen shows a sentence. One letter is the target. The physical key lights
up on the keyboard. The child finds it, presses it, and the light moves to the
next letter.

```
Monkey is jumping.
^
"Find M."          M = bright, every other key dim
```

Press `M` → the light moves to `O`. Press the wrong key → **nothing is lost**,
the target stays put and gets a little more prominent. Mistakes are
information, not failure.

This is not a typing-speed test. It is built for key-location recognition,
attention, accuracy and gradually growing independence. Speed comes last.

---

## Quick start (macOS)

```bash
git clone <this repo> && cd itype
./install_mac.sh
```

That sets up a virtualenv, installs dependencies, runs the tests, builds
`Type Scholar.app` and installs it. Other modes:

```bash
./install_mac.sh --run             # run from source, skip the build
./install_mac.sh --test-keyboard   # go straight to the hardware test
```

**Plug the PRO X 60 in by USB and run the hardware test first.** It tells you
whether per-key lighting works before you sit down with your child:

```bash
python3 keyboard_test.py
```

### Linux / Windows

The game itself is cross-platform; only the packaging and the voice are
macOS-specific.

```bash
pip install -r requirements.txt
python -m app.main
```

---

## The keyboard

Target hardware is the **Logitech PRO X 60 LIGHTSPEED**. Getting per-key RGB
out of it from a third-party macOS app is the highest-risk part of this
project, so it was researched before any UI was written.

**Short version:** the viable route is Logitech's own **HID++ 2.0 protocol,
feature `0x8081` (per-key lighting v2)**, over the keyboard's vendor HID
collection. It needs no root and no kernel extension on macOS, and works over
USB and LIGHTSPEED.

The Logitech LED SDK is Windows-only. OpenRGB does not list this keyboard.
Both are implemented as fallbacks anyway.

Full write-up, protocol details and sources:
**[`docs/hardware-research.md`](docs/hardware-research.md)**

### Backends

Probed in order, first one that answers wins:

| Backend | What it needs | Outlook |
|---|---|---|
| `hidpp` | `hidapi`, keyboard on USB or LIGHTSPEED | **Primary route** |
| `logitech-sdk` | A macOS LED SDK dylib | None ships today |
| `openrgb` | OpenRGB running, SDK server on | PRO X 60 unsupported |
| `noop` | Nothing | Always works |

```bash
python3 keyboard_test.py --auto      # see which one wins on your machine
python -m app.main --backend hidpp   # force one
python -m app.main --no-lighting     # screen only
```

### If lighting does not work

**The game works anyway.** It says so plainly, and the on-screen 60% keyboard
takes over the hand-eye job — the child still learns *where* the key is, just
from the screen rather than from under their fingers. Nothing about the game
is blocked on RGB.

### Hardware test utility

```bash
python3 keyboard_test.py             # interactive menu
python3 keyboard_test.py --scan      # enumerate: VID, PID, usage page, transport
python3 keyboard_test.py --monkey    # M → O → N → K → E → Y
python3 keyboard_test.py --calibrate # measure the real zone-ID mapping
```

`--calibrate` matters: the zone-ID encoding is the one part of the protocol
that can vary per device, so the tool walks the IDs and lets you record which
one lights which key instead of trusting the default.

---

## How it plays

**Four difficulty levels**, each removing one more support — that progression
*is* the product:

| Level | Keyboard | Voice | Screen |
|---|---|---|---|
| **Guided** | Bright pulse | Every key | Big target letter + keyboard map |
| **Learning** | Soft pulse | Only on mistakes | Target + keyboard map |
| **Independent** | Dim, static | Silent | Target only |
| **Challenge** | Off | Off | Plain sentence |

**Rewards** are for finishing and for accuracy, never for speed. Every
completed sentence gets a celebration. A flawless run gets five stars.

**Independence** is tracked as its own metric and shown as "By myself" stars —
a more meaningful number than WPM for this purpose.

**Attention cues**: if nothing happens for a few seconds, a quiet
"M is waiting." Then, later, "Find M." Spaced out so it never nags.
Configurable, off-switchable.

**Capitals** target the letter key, not `Shift`+letter. A beginner is learning
*where keys are*; the Shift lesson is a switch in settings for later.

---

## Project layout

```
app/
  main.py            entry point
  config.py          settings, persisted as JSON
  paths.py           per-user data locations
  game/              pure logic — no Qt, no hardware, fully testable
    engine.py          cursor, mistakes, accuracy, timing
    sentence.py        text preparation and character states
    scoring.py         stars, accuracy, independence
    session.py         orchestration: lighting + voice + attention
    difficulty.py      the four levels
  keyboard/          vendor-independent lighting
    base.py            the interface the game depends on
    keymap.py          characters → physical keys → per-backend names
    hidpp.py           Logitech HID++ 2.0 (primary)
    logitech.py        official LED SDK via ctypes
    openrgb.py         OpenRGB wire protocol, no third-party dep
    hid.py             enumeration and diagnostics
    noop.py            always-works fallback
    manager.py         detection, pulse animation, guaranteed restore
  ui/                PySide6 views and custom widgets
  audio/             OS text-to-speech, sounds synthesised at runtime
  data/              sentence library, SQLite progress
tests/               126 tests, no hardware required
packaging/           PyInstaller spec, Info.plist, build script, icon
docs/                hardware research
keyboard_test.py     hardware test utility
install_mac.sh       one-command macOS install
```

The game never imports a vendor backend directly — only
`app/keyboard/base.py`. Adding a Wooting means adding one file.

---

## Development

```bash
pip install -r requirements.txt
python -m app.main -v            # verbose logging
python -m pytest tests/ -q       # 126 tests, ~0.4s
```

Useful flags:

```bash
python -m app.main --sentence "Dad is making pancakes."
python -m app.main --backend openrgb
```

Tests cover game rules, the character/key/zone mapping, scoring and
independence, session orchestration and attention timing, SQLite persistence,
and the OpenRGB protocol parser across four protocol versions. None of them
need a keyboard attached.

### Building the app

```bash
./packaging/build_mac.sh          # dist/Type Scholar.app
./packaging/build_mac.sh --dmg    # ...and a .dmg
```

The build refuses to package if the tests fail, and ad-hoc signs the bundle so
Gatekeeper on Apple Silicon will launch it.

---

## Privacy

Built for a child, so:

- No network calls, no accounts, no login, no cloud
- No analytics, no telemetry, no advertising
- Speech uses the local macOS engine, never a cloud API
- All data is a single SQLite file in
  `~/Library/Application Support/TypeScholar/`

Deleting that folder removes everything the app has ever stored.

---

## Keyboard ownership

The game takes control of the lighting while it runs and **puts it back when
it exits** — including on crash, via an `atexit` hook. It never leaves the
keyboard in a modified state.

If Logitech G HUB is running it may also be driving the lights. The app
detects this and mentions it, but does not kill G HUB. Quitting G HUB while
playing gives the cleanest result.

---

## Status

Everything below runs today, with or without the keyboard:

- Native Mac window, sentence display, per-character target highlighting
- Correct/incorrect handling with no progress loss on mistakes
- Voice coaching, sound effects, attention reminders
- Celebrations, stars, accuracy, independence metric
- 62 built-in sentences across 7 categories, plus parent-written ones
- Free Play mode, parent settings, local SQLite progress
- `.app` bundle, `.dmg`, one-command installer
- Hardware test utility with calibration

Waiting on hardware: the end-to-end confirmation that `M` lights up on a real
PRO X 60. The protocol is implemented and the test utility is ready for it.
