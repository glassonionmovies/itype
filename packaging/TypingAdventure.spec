# PyInstaller spec for Typing Adventure.
#
# Build with:  pyinstaller packaging/TypingAdventure.spec --noconfirm
# or just run: ./packaging/build_mac.sh

import sys
from pathlib import Path

# SPECPATH is injected by PyInstaller and points at this file's directory.
ROOT = Path(SPECPATH).resolve().parent  # noqa: F821

block_cipher = None

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app" / "assets"), "assets"),
    ],
    hiddenimports=[
        "hid",
        "app.keyboard.hidpp",
        "app.keyboard.openrgb",
        "app.keyboard.logitech",
        "app.keyboard.noop",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim the parts of Qt the game never touches; the bundle is ~40% smaller
    # without them and nothing here is imported at runtime.
    excludes=[
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtQuick3D",
        "PySide6.QtBluetooth",
        "PySide6.QtPositioning",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtDesigner",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Typing Adventure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # follows the building machine (arm64 or x86_64)
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "packaging" / "icon.ico") if (ROOT / "packaging" / "icon.ico").exists() else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Typing Adventure",
)

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="Typing Adventure.app",
        icon=str(ROOT / "packaging" / "icon.icns")
        if (ROOT / "packaging" / "icon.icns").exists()
        else None,
        bundle_identifier="com.typingadventure.app",
        info_plist={
            "CFBundleName": "Typing Adventure",
            "CFBundleDisplayName": "Typing Adventure",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.educational-games",
            "NSHumanReadableCopyright": "Local-only. No accounts, no network, no telemetry.",
            # The game reads key events from its own focused window, so it does
            # not need Input Monitoring. This string is here only in case a
            # future build enables global capture.
            "NSAppleEventsUsageDescription": "Typing Adventure does not send Apple Events.",
        },
    )
