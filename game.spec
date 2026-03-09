# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# --- ASSET CONFIGURATION ---
# 1. Add your image files here.
# Format: ('Source Path', 'Destination Path in Bundle')
added_files = [
    ('flash_screen.jpg', '.'),
    ('background.jpg', '.'),
    ('arrow_up.png', '.'),
    ('arrow_down.png', '.'),
    ('balloon.png', '.'),
    ('balloon_green.png', '.')
]

# 2. Collect MediaPipe model files automatically
added_files += collect_data_files('mediapipe')

a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    name='NoddingBalloon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='balloon.ico'  
)