# -*- mode: python ; coding: utf-8 -*-
# Gera dist/Printers3DUtility.exe  ->  pyinstaller Printers3DUtility.spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ocultos = [
    n for n in collect_submodules("epson_usb") if not n.startswith("epson_usb.tests")
] + collect_submodules("pysnmp") + collect_submodules("pysnmp_sync_adapter") + [
    "epson_usb_bridge", "find_printers", "core", "diagnostico", "erros_epson",
    "sv_ttk", "PIL.ImageTk", "impressao",
]

a = Analysis(
    ["src/printers3d.py"],
    pathex=["src"],
    datas=collect_data_files("sv_ttk") + [("src/img/*.png", "img"), ("src/img/icone.ico", "img"), ("src/img/testes/*.png", "img/testes"), ("src/modelos_extra.json", "."), ("src/diagnosticos.json", ".")],
    hiddenimports=ocultos,
    excludes=["black", "blib2to3", "yaml", "pyprintlpr", "epson_escp2"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Printers3DUtility",
    console=False,
    upx=False,
    icon="src/img/icone.ico",
)
