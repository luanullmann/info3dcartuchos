"""Manutenção: limpeza de cabeçote (CL1/CL2/CL3), carga de tinta, teste de
bicos e firmware.

Os comandos são do "modo remoto" ESC/P2 da Epson (o mesmo que o utilitário
do driver usa em "Limpeza do cabeçote"). A sequência segue o projeto
epson_print_conf / epson_escp2 (Ircama, EUPL-1.2).

Envio:
- Wi-Fi/rede: direto para o IP, porta 9100 (RAW); se fechada, LPR (515).
- USB: pela fila de impressão do Windows em modo RAW (precisa do driver
  instalado, igual ao teste de impressão).

ATENÇÃO: o comportamento exato de cada nível varia por modelo. Teste na
bancada antes de usar em impressora de cliente.
"""
from __future__ import annotations

import datetime
import os
import socket
import struct
import sys
import webbrowser
from urllib.parse import quote

# ----------------------------------------------------------------- ESC/P2
ESC = b"\x1b"
INIT = ESC + b"@"
SAIR_PACOTE = b"\x00\x00\x00\x1b\x01@EJL 1284.4\n@EJL     \n"
SAIR_REMOTO = b"\x1b\x00\x00\x00"


def _rc(cmd: str, args: bytes) -> bytes:
    return cmd.encode() + struct.pack("<H", len(args)) + args


ENTRAR_REMOTO = INIT + INIT + ESC + _rc("(R", b"\x00REMOTE1")
FIM_TRABALHO = _rc("JE", b"\x00")


def _relogio() -> bytes:
    n = datetime.datetime.now()
    return _rc("TI", b"\x00" + struct.pack(">H", n.year)
               + bytes([n.month, n.day, n.hour, n.minute, n.second]))


def _limpeza(grupo: int) -> bytes:
    return b"".join([
        SAIR_PACOTE, ENTRAR_REMOTO, _relogio(),
        _rc("CH", b"\x00" + bytes([grupo])),
        SAIR_REMOTO, ENTRAR_REMOTO, FIM_TRABALHO, SAIR_REMOTO,
    ])


def _teste_bicos() -> bytes:
    return b"".join([SAIR_PACOTE, ENTRAR_REMOTO, _rc("NC", b"\x00\x00"),
                     SAIR_REMOTO, FIM_TRABALHO])


# Carga de tinta: sequência usada pela Epson em parte da linha EcoTank
# (epson_escp2: "Ink charge"). Gasta MUITA tinta e enche a almofada.
_CARGA = INIT + bytes.fromhex("1B 7C 00 06 00 19 07 84 7B 42 0A")

ROTINAS = {
    "cl1": {"nome": "CL1 - Limpeza normal",
            "dados": lambda: _limpeza(0x00),
            "aviso": "Limpeza comum de todas as cores (~1 min)."},
    "cl2": {"nome": "CL2 - Limpeza forte (power clean)",
            "dados": lambda: _limpeza(0x10),
            "aviso": "Gasta mais tinta e enche mais a almofada. Use se a CL1 não resolveu."},
    "cl3": {"nome": "CL3 - Carga de tinta (initial ink charge)",
            "dados": lambda: _CARGA,
            "aviso": "Enche todas as mangueiras de novo: gasta MUITA tinta e enche a "
                     "almofada. Só depois de trocar cabeçote, damper ou mangueira, ou com "
                     "ar na linha. Confira se os tanques estão cheios."},
    "bicos": {"nome": "Teste de bicos (nozzle check)",
              "dados": _teste_bicos,
              "aviso": "Imprime o padrão de bicos da Epson. Coloque papel A4."},
}


# ------------------------------------------------------------- transporte
def _enviar_raw_9100(ip: str, dados: bytes, timeout: float = 15) -> None:
    with socket.create_connection((ip, 9100), timeout=timeout) as s:
        s.sendall(dados)


def _enviar_lpr(ip: str, dados: bytes, timeout: float = 30) -> None:
    """Cliente LPR mínimo (RFC 1179), fila 'PASSTHRU' aceita pelas Epson."""
    def ok(s):
        r = s.recv(1)
        if r != b"\x00":
            raise RuntimeError("LPR recusou o trabalho")
    host = "P3D"
    ctrl = f"H{host}\nPprinters3d\nldfA001{host}\n".encode()
    with socket.create_connection((ip, 515), timeout=timeout) as s:
        s.sendall(b"\x02PASSTHRU\n"); ok(s)
        s.sendall(f"\x02{len(ctrl)} cfA001{host}\n".encode()); ok(s)
        s.sendall(ctrl + b"\x00"); ok(s)
        s.sendall(f"\x03{len(dados)} dfA001{host}\n".encode()); ok(s)
        s.sendall(dados + b"\x00"); ok(s)


def _enviar_windows(impressora: str, dados: bytes) -> None:
    """Manda bytes crus para uma fila do Windows (modo RAW)."""
    if sys.platform != "win32":
        raise RuntimeError("Envio pela fila do Windows só funciona no Windows.")
    import ctypes
    from ctypes import wintypes

    ws = ctypes.WinDLL("winspool.drv", use_last_error=True)

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [("pDocName", wintypes.LPWSTR),
                    ("pOutputFile", wintypes.LPWSTR),
                    ("pDatatype", wintypes.LPWSTR)]

    h = wintypes.HANDLE()
    if not ws.OpenPrinterW(impressora, ctypes.byref(h), None):
        raise RuntimeError(f"Não abri a impressora '{impressora}'.")
    try:
        di = DOC_INFO_1("Printer's 3D Utility - manutenção", None, "RAW")
        if not ws.StartDocPrinterW(h, 1, ctypes.byref(di)):
            raise RuntimeError("O Windows recusou o trabalho RAW.")
        try:
            ws.StartPagePrinter(h)
            escrito = wintypes.DWORD()
            buf = ctypes.create_string_buffer(dados, len(dados))
            if not ws.WritePrinter(h, buf, len(dados), ctypes.byref(escrito)):
                raise RuntimeError("Falha ao enviar os dados para a impressora.")
            ws.EndPagePrinter(h)
        finally:
            ws.EndDocPrinter(h)
    finally:
        ws.ClosePrinter(h)


def executar(rotina: str, ip: str | None = None, impressora_windows: str | None = None) -> str:
    """Envia a rotina. Retorna por onde foi enviada."""
    dados = ROTINAS[rotina]["dados"]()
    if ip:
        try:
            _enviar_raw_9100(ip, dados)
            return f"rede ({ip}:9100)"
        except OSError:
            _enviar_lpr(ip, dados)
            return f"rede ({ip}, LPR)"
    if impressora_windows:
        _enviar_windows(impressora_windows, dados)
        return f"Windows ({impressora_windows})"
    raise RuntimeError("Informe o IP (Wi-Fi) ou escolha a impressora do Windows (USB).")


# --------------------------------------------------------------- firmware
SUPORTE_EPSON = {
    "L355": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L355/s/SPT_C11CC86201",
    "L395": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L395/s/SPT_C11CF46301",
    "L1250": "https://epson.com.br/Suporte/Impressoras/Impressoras-de-fun%C3%A7%C3%A3o-%C3%BAnica/Epson-L/Epson-L1250/s/SPT_C11CJ71301",
    "L3110": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L3110/s/SPT_C11CG87301",
    "L3150": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L3150/s/SPT_C11CG86301",
    "L3210": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L3210/s/SPT_C11CJ68301",
    "L3250": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L3250/s/SPT_C11CJ67301",
    "L4160": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L4160/s/SPT_C11CG23301",
    "L4260": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L4260/s/SPT_C11CJ63301",
    "L5190": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L5190/s/SPT_C11CG85301",
    "L6191": "https://epson.com.br/Suporte/Impressoras/Impressoras-multifuncionais/Epson-L/Epson-L6191/s/SPT_C11CG19302",
    "L8050": "https://epson.com.br/Suporte/Impressoras/Impressoras-de-fun%C3%A7%C3%A3o-%C3%BAnica/Epson-L/Epson-L8050/s/SPT_C11CK37301",
}

AVISO_FIRMWARE = (
    "ANTES DE ATUALIZAR:\n"
    "• Firmware novo da Epson costuma BLOQUEAR o reset pela rede/USB "
    "(foi o que aconteceu com a L3250). Depois de atualizar, a Epson não deixa voltar.\n"
    "• Faça o reset das almofadas e o backup da EEPROM ANTES de atualizar.\n"
    "• Não desligue a impressora nem o PC durante a gravação: pode travar a placa.\n"
    "• Use só o firmware oficial do modelo exato (L3250 ≠ L3251).\n\n"
    "Impressora travada depois de atualização? O pacote oficial da Epson tem o "
    "modo de recuperação: desligue, segure o botão indicado pelo manual do "
    "modelo e ligue, depois rode o atualizador pelo USB."
)


def pagina_suporte(modelo: str) -> str:
    m = (modelo or "").upper().replace("EPSON", "").replace("SERIES", "").strip()
    m = m.split()[0] if m else ""
    return SUPORTE_EPSON.get(m) or f"https://epson.com.br/search/?text={quote(m or 'EcoTank')}"


def abrir_suporte(modelo: str) -> str:
    url = pagina_suporte(modelo)
    webbrowser.open(url)
    return url


def abrir_painel_web(ip: str) -> str:
    """Web Config da impressora (tem 'Atualização de firmware' em vários modelos)."""
    url = f"http://{ip}/"
    webbrowser.open(url)
    return url


def ler_firmware_e_contadores(imp) -> dict:
    r: dict = {}
    for chave, fn in (("firmware", "get_firmware_version"),
                      ("cabecote", "get_printer_head_id"),
                      ("contadores", "get_stats")):
        try:
            r[chave] = getattr(imp, fn)()
        except Exception:  # noqa: BLE001
            r[chave] = None
    return r
