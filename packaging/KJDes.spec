# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for KJ Des (one-folder, windowed, requires administrator).
#   pyinstaller --noconfirm --clean packaging/KJDes.spec
import os
import re
import sys

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
    StringStruct, VarFileInfo, VarStruct,
)

spec_dir = os.path.abspath(SPECPATH)
root_dir = os.path.dirname(spec_dir)
app_dir = os.path.join(root_dir, 'app')
assets_dir = os.path.join(app_dir, 'assets')

# Single version source: app/core/app_info.py
with open(os.path.join(app_dir, 'core', 'app_info.py'), encoding='utf-8') as _f:
    _m = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', _f.read(), re.MULTILINE)
_app_version = _m.group(1) if _m else '0.0.0'
_nums = ([int(n) for n in re.findall(r'\d+', _app_version)] + [0, 0, 0, 0])[:4]
_vers_tuple = tuple(_nums)
_vers_str = '.'.join(str(n) for n in _vers_tuple)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_vers_tuple, prodvers=_vers_tuple, mask=0x3f, flags=0x0,
                      OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', 'Lucas'),
            StringStruct('FileDescription', 'KJ Des - A Windows desktop connectivity utility for Discord'),
            StringStruct('FileVersion', _vers_str),
            StringStruct('InternalName', 'KJDes'),
            StringStruct('LegalCopyright',
                         'Copyright (c) 2026 Lucas. Includes third-party components; see NOTICE.md.'),
            StringStruct('OriginalFilename', 'KJDes.exe'),
            StringStruct('ProductName', 'KJ Des'),
            StringStruct('ProductVersion', _vers_str),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)

datas = [
    (assets_dir, 'assets'),
    (os.path.join(app_dir, 'locales'), 'locales'),
    (os.path.join(app_dir, 'ui', 'styles.qss'), 'ui'),
    (os.path.join(app_dir, 'branding.json'), '.'),
    (os.path.join(root_dir, 'licenses'), 'licenses'),
    (os.path.join(root_dir, 'LICENSE'), '.'),
    (os.path.join(root_dir, 'NOTICE.md'), '.'),
]
binaries = [
    (os.path.join(sys.base_prefix, name), '.')
    for name in ('python3.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
    if os.path.exists(os.path.join(sys.base_prefix, name))
]

# Only QtCore/QtGui/QtWidgets are used; keep the bundle small.
excludes = [
    'tkinter', 'numpy', 'pandas', 'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtMultimedia',
    'PySide6.QtPdf', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets', 'PySide6.QtSvg', 'PySide6.QtDBus', 'PySide6.QtXml',
]

a = Analysis(
    [os.path.join(app_dir, 'main.py')],
    pathex=[app_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=['ui.app', 'core.system_ops'],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

# Drop Qt translations and unused image-format/plugins to reduce size.
_drop = ('translations', 'qtwebengine', 'Qt6Quick', 'Qt6Qml', 'Qt6Pdf', 'Qt6Network',
         'opengl32sw', 'Qt6OpenGL', 'Qt6Svg', 'qsvg', 'qpdf', 'qtiff', 'qwebp', 'qicns',
         'qtga', 'qwbmp', 'qjpeg', 'qgif', 'Qt6VirtualKeyboard')
a.datas = [d for d in a.datas if not any(k.lower() in d[0].lower() for k in _drop)]
a.binaries = [b for b in a.binaries if not any(k.lower() in b[0].lower() for k in _drop)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='KJDes',
    debug=False,
    strip=False,
    upx=False,
    console=False,                 # no console window in normal GUI mode
    disable_windowed_traceback=False,
    uac_admin=True,                # DNS/hosts/recovery task need administrator
    icon=[os.path.join(assets_dir, 'icon.ico')],
    version=version_info,
    exclude_binaries=True,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='KJDes')
