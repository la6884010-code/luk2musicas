# -*- mode: python ; coding: utf-8 -*-
#
# luk2.spec — PyInstaller spec para LUK2 Visualizer
#
# Como usar:
#   pip install pyinstaller
#   pyinstaller luk2.spec
#
# O executável final ficará em:  dist/LUK2/LUK2.exe
#
# IMPORTANTE: coloque seus arquivos de música (.mp3/.wav/etc)
# na mesma pasta que LUK2.exe antes de rodar o app.

block_cipher = None

a = Analysis(
    ['didiyprincipalpagina2.0.py'],
    pathex=['.'],
    binaries=[],
    datas=[],          # sem assets bundled — usuário coloca músicas ao lado do .exe
    hiddenimports=[
        'soundfile',
        'soundfile.sndfile',
        'numpy',
        'numpy.core._multiarray_umath',
        'colorama',
        'pygame',
        'moderngl',
        'multiprocessing.util',
        'multiprocessing.managers',
        # descomente abaixo se opencv ou panda3d estiverem instalados
        # 'cv2',
        # 'panda3d',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'email',
        'html',
        'http',
        'xml',
        'pydoc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LUK2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,      # DEVE ser True — o app usa input() no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,         # substitua por 'assets/images/LUK2(1).png' se quiser ícone .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LUK2',
)
