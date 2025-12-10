# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec to build a standalone bcfeed macOS app bundle.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = []
hiddenimports = (
    collect_submodules("googleapiclient")
    + collect_submodules("google.auth")
    + collect_submodules("google_auth_oauthlib")
    + collect_submodules("tkinter")
)

a = Analysis(
    ["app_gui.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="bcfeed",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
app = BUNDLE(
    exe,
    name="bcfeed.app",
    icon=None,
    bundle_identifier="com.bcfeed.app",
)
