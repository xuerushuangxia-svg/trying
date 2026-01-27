# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 跨平台打包配置
macOS: pyinstaller build.spec --noconfirm
Windows: pyinstaller build.spec --noconfirm
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all, copy_metadata

block_cipher = None
is_windows = sys.platform == 'win32'
is_mac = sys.platform == 'darwin'

# 收集 streamlit 所有相关文件，包括 metadata
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
altair_datas, altair_binaries, altair_hiddenimports = collect_all('altair')

# 合并所有数据
datas = []
datas += streamlit_datas
datas += altair_datas
datas += collect_data_files('pandas')
datas += collect_data_files('pyarrow')

# 添加包的 metadata（解决 PackageNotFoundError）
datas += copy_metadata('streamlit')
datas += copy_metadata('altair')
datas += copy_metadata('pandas')
datas += copy_metadata('numpy')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')

# importlib_metadata 可能不存在，安全处理
try:
    datas += copy_metadata('importlib_metadata', recursive=True)
except Exception:
    pass

# 添加项目文件
datas += [
    ('main.py', '.'),
    ('config', 'config'),
    ('services', 'services'),
    ('ui', 'ui'),
    ('utils', 'utils'),
]

# 收集所有子模块
hiddenimports = []
hiddenimports += streamlit_hiddenimports
hiddenimports += altair_hiddenimports
hiddenimports += [
    'pandas',
    'pandas._libs',
    'requests',
    'difflib',
    'config',
    'config.settings',
    'services',
    'services.data_service',
    'services.risk_analyzer',
    'ui',
    'ui.components',
    'ui.styles',
    'utils',
    'utils.helpers',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner',
]

binaries = []
binaries += streamlit_binaries
binaries += altair_binaries

a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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

# Windows: 生成单文件 .exe（onefile 模式）
# macOS: 生成 .app bundle
if is_windows:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='XUE风险穿透终端',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='icon.ico' if os.path.exists('icon.ico') else None,
    )
else:
    # macOS: 使用 COLLECT + BUNDLE
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='XUE风险穿透终端',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='XUE风险穿透终端',
    )

    app = BUNDLE(
        coll,
        name='XUE风险穿透终端.app',
        icon=None,
        bundle_identifier='com.xue.risk.terminal',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
        },
    )
