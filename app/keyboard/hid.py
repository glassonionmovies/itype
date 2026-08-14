"""Raw HID enumeration and diagnostics.

This module deliberately does **not** invent a lighting protocol. Writing
speculative vendor frames to a keyboard cannot be validated without the
hardware in hand, and shipping code that pretends to work is worse than
shipping none. Actual per-key writes live in :mod:`app.keyboard.hidpp`, which
implements Logitech's documented HID++ 2.0 feature 0x8081.

What this module provides is the evidence-gathering step the handoff asks for
in section 4C: enumerate the device and report vendor ID, product ID,
manufacturer, product string, serial, usage page, usage, interface and
transport, so the mapping can be recorded from the real device rather than
guessed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

LOGITECH_VENDOR_ID = 0x046D

#: Usage page 0xFF00 carries Logitech's HID++ vendor collection.
VENDOR_USAGE_PAGE = 0xFF00
KEYBOARD_USAGE_PAGE = 0x01


@dataclass
class HidInterface:
    """One HID interface as reported by hidapi."""

    path: str
    vendor_id: int
    product_id: int
    manufacturer: str = ""
    product: str = ""
    serial: str = ""
    usage_page: int = 0
    usage: int = 0
    interface_number: int = -1
    release_number: int = 0

    @property
    def is_vendor_collection(self) -> bool:
        return self.usage_page == VENDOR_USAGE_PAGE

    @property
    def likely_hidpp(self) -> bool:
        return self.vendor_id == LOGITECH_VENDOR_ID and self.is_vendor_collection

    def describe(self) -> str:
        role = "vendor/HID++" if self.is_vendor_collection else f"usage page 0x{self.usage_page:04x}"
        return (
            f"{self.product or 'Unknown'} "
            f"[{self.vendor_id:04x}:{self.product_id:04x}] "
            f"iface {self.interface_number} {role}"
        )

    def as_report(self) -> dict[str, str]:
        """Flatten to the field list the handoff asks to record."""
        return {
            "Vendor ID": f"0x{self.vendor_id:04x}",
            "Product ID": f"0x{self.product_id:04x}",
            "Manufacturer": self.manufacturer or "(none)",
            "Product string": self.product or "(none)",
            "Serial number": self.serial or "(not exposed)",
            "Usage page": f"0x{self.usage_page:04x}",
            "Usage": f"0x{self.usage:04x}",
            "Interface": str(self.interface_number),
            "Release": f"0x{self.release_number:04x}",
            "Path": self.path,
        }


@dataclass
class HidScan:
    """Result of a HID enumeration sweep."""

    available: bool
    error: str = ""
    interfaces: list[HidInterface] = field(default_factory=list)

    @property
    def logitech(self) -> list[HidInterface]:
        return [i for i in self.interfaces if i.vendor_id == LOGITECH_VENDOR_ID]

    @property
    def hidpp_capable(self) -> list[HidInterface]:
        return [i for i in self.interfaces if i.likely_hidpp]


def scan(vendor_id: int | None = None) -> HidScan:
    """Enumerate HID interfaces, optionally filtered by vendor.

    Never raises: a missing hidapi or a permission error is reported through
    the returned :class:`HidScan`.
    """
    try:
        import hid
    except ImportError:
        return HidScan(False, "hidapi not installed (pip install hidapi)")

    try:
        entries = hid.enumerate(vendor_id or 0, 0)
    except Exception as exc:  # pragma: no cover - platform specific
        return HidScan(False, f"hid.enumerate failed: {exc}")

    interfaces = []
    for entry in entries:
        interfaces.append(
            HidInterface(
                path=_decode(entry.get("path", b"")),
                vendor_id=entry.get("vendor_id", 0),
                product_id=entry.get("product_id", 0),
                manufacturer=_decode(entry.get("manufacturer_string", "")),
                product=_decode(entry.get("product_string", "")),
                serial=_decode(entry.get("serial_number", "")),
                usage_page=entry.get("usage_page", 0),
                usage=entry.get("usage", 0),
                interface_number=entry.get("interface_number", -1),
                release_number=entry.get("release_number", 0),
            )
        )
    return HidScan(True, "", interfaces)


def _decode(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value or "")


def probe_open(interface: HidInterface) -> tuple[bool, str]:
    """Try to open *interface*, reporting why if it fails.

    On macOS this is where the interesting failures surface: opening a
    keyboard collection can return ``kIOReturnNotPermitted`` under Apple's
    ``protectedDeviceAccess`` policy, while the vendor collection normally
    opens without special privileges.
    """
    try:
        import hid
    except ImportError:
        return False, "hidapi not installed"

    try:
        handle = hid.Device(path=interface.path.encode() if isinstance(interface.path, str) else interface.path)
    except Exception as exc:
        hint = ""
        if interface.usage_page == KEYBOARD_USAGE_PAGE:
            hint = " (expected: macOS protects keyboard collections)"
        return False, f"{exc}{hint}"
    handle.close()
    return True, "opened successfully"
