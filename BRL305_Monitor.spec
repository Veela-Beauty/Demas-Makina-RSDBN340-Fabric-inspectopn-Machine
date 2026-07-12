# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Bundle certifi's CA bundle so the frozen exe verifies TLS without the Windows cert store
# (a frozen app can't rely on certifi.where() unless the data file is collected).
certifi_datas, certifi_binaries, certifi_hiddenimports = collect_all('certifi')
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')

# pywebview (Edge WebView2 backend) powers the in-app Prime Textile view. It's a Windows-only,
# optional dependency: collect it if present so the frozen build embeds it, but never fail the
# build when it's absent (e.g. non-Windows CI). At runtime the app degrades to the system browser.
try:
    webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')
except Exception:
    webview_datas, webview_binaries, webview_hiddenimports = [], [], []

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=certifi_binaries + ctk_binaries + webview_binaries,
    datas=certifi_datas + ctk_datas + webview_datas,
    hiddenimports=['gui.main_window', 'gui.dashboard', 'gui.error_panel', 'gui.config_panel', 'gui.erpnext_panel', 'gui.login_view', 'gui.web_panel', 'models.data_models', 'utils.logger', 'serial_handler', 'erpnext_client', 'outbox', 'defect_map', 'inspection_flow', 'app_settings', 'preflight', 'theme', 'web_view_support', 'web_launcher', 'customtkinter', 'darkdetect', 'PIL', 'webview', 'webview.platforms.edgechromium', 'clr', 'clr_loader'] + certifi_hiddenimports + ctk_hiddenimports + webview_hiddenimports,
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
    name='BRL305_Monitor',
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
    icon=['assets\\icon.ico'],
)
