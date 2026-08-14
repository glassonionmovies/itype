# Controlling PRO X 60 per-key RGB from macOS

Research notes behind the keyboard layer. Written up because the conclusion is
non-obvious, and because the next person to touch this should not have to
re-derive it.

**The question is not whether the keyboard has individually addressable LEDs.**
It does — Logitech sells it on that. The question is which interface a
third-party macOS application can drive them through.

## Conclusion first

Use **Logitech's own HID++ 2.0 protocol, feature `0x8081`
(PER_KEY_LIGHTING_V2)**, over the device's vendor HID collection. It is the
only route that is documented, reachable from an unprivileged macOS process,
and works over both USB and the LIGHTSPEED receiver.

Implemented in [`app/keyboard/hidpp.py`](../app/keyboard/hidpp.py).

## The routes, and why they rank the way they do

### 1. Logitech LED Illumination SDK — not viable on macOS

The handoff asks for the official SDK first, and that is the right instinct.
The functions it names (`LogiLedSetLightingForKeyWithKeyName`,
`LogiLedSetLightingForKeyWithScanCode`, …) are real and are exactly the
per-key API we want.

The problem is distribution. Every binding, sample and wrapper in the wild
loads a **Windows DLL** (`LogitechLedEnginesWrapper.dll` /
`LogitechLed.dll`). G HUB for Mac ships no equivalent `.dylib`, and Logitech
publishes no macOS build of the LED SDK. There is nothing to `dlopen`.

The backend is implemented anyway
([`app/keyboard/logitech.py`](../app/keyboard/logitech.py)) because it costs
little, it probes the paths a Mac library *would* live at, and if Logitech
ever ships one the game picks it up with no other change. Expect it to report
"library not found" today.

### 2. OpenRGB — a genuine long shot for this device

OpenRGB is the obvious "just use the community tool" answer, and for many
keyboards it is the right one. Two problems for this one:

- **The PRO X 60 is not on the supported list.** OpenRGB's Logitech keyboard
  support covers the G213 / G410 / G413 / G512 / G513 / G610 / G810 / G815 /
  G910 / GPRO generation. The PRO X 60 is a later design and is absent.
- **macOS Logitech support is shaky.** There is a filed report of a Logitech
  G Pro X on an Apple Silicon MacBook not enumerating at all, with OpenRGB
  crashing on "Rescan Devices".

The backend is still implemented
([`app/keyboard/openrgb.py`](../app/keyboard/openrgb.py)), speaking the SDK
wire protocol directly over a socket rather than depending on
`openrgb-python`. If OpenRGB adds the device, this starts working immediately.
Requires the OpenRGB app running with its SDK server on (default port 6742).

### 3. HID++ 2.0 — the route that should work

Logitech's devices speak **HID++**, their own protocol, over a vendor-specific
HID collection. Logitech publishes feature documentation themselves in
[`Logitech/cpg-docs`](https://github.com/Logitech/cpg-docs), which lists among
the gaming features:

| Feature | Name |
|---------|------|
| `0x1981` / `0x1982` | Backlight 1 / 2 |
| `0x8070` | Color LED Effects |
| `0x8071` | RGB Effects |
| `0x8080` | Per Key Lighting |
| `0x8081` | Per Key Lighting v2 |

`0x8081` is the one that paints individual keys. It is implemented and tested
in [Solaar](https://github.com/pwr-Solaar/Solaar), whose per-key code is the
reference this implementation follows. The G915 TKL — same modern LIGHTSPEED
generation as the PRO X 60 — is confirmed to support both `0x8071` and
`0x8081`.

#### Why this works on macOS specifically

This is the crux. macOS gates HID access with a policy
(`com.apple.iohid.protectedDeviceAccess`) that makes `IOHIDDeviceOpen` return
`kIOReturnNotPermitted` for **keyboard** collections — you cannot just open a
keyboard and read or write to it from an ordinary app. That restriction is
what sinks most naive HID approaches.

HID++ does not travel over the keyboard collection. It travels over the
**vendor-specific collection, usage page `0xFF00`**, which is *not* gated. So
this route needs:

- no root
- no kernel extension
- no Input Monitoring permission

`app/keyboard/hid.py` enumerates both and reports which ones open, so the
distinction is visible rather than assumed.

## The protocol

Transport is a HID report, short (7 bytes, report ID `0x10`) or long
(20 bytes, report ID `0x11`):

```
[report_id] [device_index] [feature_index] [function|software_id] [payload...]
```

`device_index` is `0xFF` for a directly-connected device, or `0x01`–`0x03` for
a device paired to a receiver — the code tries all of them. `feature_index` is
resolved at runtime by asking the root feature (index `0`, function `0`) for a
feature ID; a returned index of `0` means the device does not support it.

Feature `0x8081` sub-functions:

| Sub-fn | Purpose | Payload |
|--------|---------|---------|
| `0x10` | Set individual zones | `[key_id, r, g, b]` × up to 4 |
| `0x50` | Set a contiguous range | `[first, last, r, g, b]` |
| `0x60` | One colour, many keys | `[r, g, b]` + up to 13 key ids |
| `0x70` | **FrameEnd** | `[0x00]` |

**FrameEnd is not optional.** Writes accumulate into a buffer and appear only
when the frame is committed. Skipping it is the single most likely reason a
per-key implementation looks completely dead while every write returns
success.

Two other practical notes, both learned from Solaar's implementation:

- The device returns a **BUSY** error (`0x07`) under rapid updates. Back off
  and retry — the code uses 30/60/90 ms.
- If the device is running its own RGB effect, per-key paint is invisible.
  Take software control through feature `0x8071` first.

### Zone IDs

Zone IDs are **the USB HID usage ID minus three**:

| Key | HID usage | Zone |
|-----|-----------|------|
| A | `0x04` | 1 |
| E | `0x08` | 5 |
| K | `0x0E` | 11 |
| M | `0x10` | 13 |
| N | `0x11` | 14 |
| O | `0x12` | 15 |
| Y | `0x1C` | 25 |
| Enter | `0x28` | 37 |
| Space | `0x2C` | 41 |

Verified against Solaar's table across letters, digits, Enter and Space, and
asserted in `tests/test_keyboard_mapping.py`.

**Caveat worth taking seriously:** Solaar allows this table to be *overridden
per device* via a YAML file, which means the encoding is not guaranteed to be
identical on every model. The code therefore supports two schemes (`hid-3` and
raw `hid`), and `keyboard_test.py --calibrate` walks zone IDs one at a time so
the real mapping can be *measured* on the actual keyboard rather than assumed.

## What to do when the keyboard arrives

```bash
python3 keyboard_test.py --scan     # is it visible? which interfaces?
python3 keyboard_test.py --auto     # which backend wins?
python3 keyboard_test.py            # interactive: light M, then MONKEY
```

Test USB first, then the LIGHTSPEED receiver, and only bother with Bluetooth
if both work — macOS is most restrictive there and it is the least important
transport for a stationary desk setup.

If `--scan` shows the keyboard but no `0xFF00` vendor interface, try the other
transport before concluding anything: the vendor collection is exposed
differently over USB than through the receiver.

## If none of it works

The game does not care. `LightingManager` falls through to
`NoOpKeyboardLighting`, the UI says so in plain language, and the on-screen
60% keyboard carries the hand-eye coordination goal on its own. Per-key RGB is
an enhancement to this game, not a dependency of it — which was the point of
putting the abstraction in before the hardware arrived.

## Sources

- [Logitech PRO X 60 product page](https://www.logitechg.com/en-us/shop/p/pro-x-60-wireless-keyboard)
- [Logitech `cpg-docs` HID++ 2.0 feature documentation](https://github.com/Logitech/cpg-docs/tree/master/hidpp20)
- [Solaar](https://github.com/pwr-Solaar/Solaar) — `settings_templates.py` (`PerKeyLighting`), `special_keys.py`
- [Solaar feature list](https://github.com/pwr-Solaar/Solaar/blob/master/docs/features.md)
- [OpenRGB](https://github.com/CalcProgrammer1/OpenRGB) and its [Logitech keyboard support list](https://openrgb-wiki.readthedocs.io/en/latest/Logitech-Keyboards/)
- [OpenRGB issue: G Pro X undetected on M1 Mac, crash on rescan](https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/2754)
- [macOS IOHIDManager permission behaviour](https://nachtimwald.com/2020/11/08/macos-iohidmanager-permission-issue/)
- [Apple Developer Forums: exclusive HID capture from keyboards](https://developer.apple.com/forums/thread/795686)
