"""
Lógica do Reset Epson (sem interface gráfica).

Usa a biblioteca aberta epson_print_conf (Ircama, licença EUPL-1.2) para falar
com a impressora por Wi-Fi/rede (SNMP) ou por cabo USB.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import sys
from typing import Callable, Optional

import epson_print_conf as _epc

log = logging.getLogger("reset_epson")

WIFI = "wifi"
USB = "usb"


# --------------------------------------------------------------------------
# Pastas
# --------------------------------------------------------------------------
def pasta_app() -> str:
    """Pasta onde está o .exe (ou o script)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _documentos() -> str:
    """Pasta Documentos do usuário (respeita redirecionamento/OneDrive no Windows)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5 (Documentos)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:  # noqa: BLE001
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def pasta_dados() -> str:
    """Onde ficam backups, fotos, histórico e os arquivos .json editáveis.

    - Programa instalado (.exe): Documentos\\Printer's 3D Utility
      (a pasta de instalação não é gravável e o técnico acha fácil).
    - Rodando pelo script: a própria pasta do script.
    - Variável P3D_DADOS sobrescreve as duas.
    """
    p = os.environ.get("P3D_DADOS")
    if not p:
        p = (os.path.join(_documentos(), "Printer's 3D Utility")
             if getattr(sys, "frozen", False) else pasta_app())
    os.makedirs(p, exist_ok=True)
    _semear(p)
    return p


def _semear(destino: str) -> None:
    """Na primeira execução, copia os .json padrão que vêm dentro do programa."""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return
    import shutil
    for nome in ("modelos_extra.json", "diagnosticos.json"):
        alvo = os.path.join(destino, nome)
        orig = os.path.join(base, nome)
        if not os.path.exists(alvo) and os.path.exists(orig):
            try:
                shutil.copy2(orig, alvo)
            except OSError:
                pass


def pasta_backups() -> str:
    p = os.path.join(pasta_dados(), "backups")
    os.makedirs(p, exist_ok=True)
    return p


def arquivo_modelos_extra() -> str:
    return os.path.join(pasta_dados(), "modelos_extra.json")


# --------------------------------------------------------------------------
# Banco de modelos extra (editável pela assistência)
# --------------------------------------------------------------------------
def _converte_entrada(entrada: dict) -> dict:
    """JSON não guarda bytes nem chaves inteiras: converte para o formato
    que a biblioteca espera."""
    e = {k: v for k, v in entrada.items() if not k.startswith("_")}
    if isinstance(e.get("write_key"), str):
        e["write_key"] = e["write_key"].encode("latin-1")
    for campo in ("raw_waste_reset", "waste_reset_commit"):
        if isinstance(e.get(campo), dict):
            e[campo] = {int(k, 0): int(v) for k, v in e[campo].items()}
    for campo in ("serial_number",):
        v = e.get(campo)
        if isinstance(v, dict) and "de" in v and "ate" in v:
            e[campo] = range(int(v["de"]), int(v["ate"]))
    return e


def carregar_modelos_extra(caminho: Optional[str] = None) -> dict:
    caminho = caminho or arquivo_modelos_extra()
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError) as exc:
        log.error("Não consegui ler %s: %s", caminho, exc)
        return {}
    modelos = dados.get("modelos", {}) if isinstance(dados, dict) else {}
    return {
        nome: _converte_entrada(ent)
        for nome, ent in modelos.items()
        if isinstance(ent, dict) and not nome.startswith("_")
    }


# --------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------
def _base() -> _epc.EpsonPrinter:
    return _epc.EpsonPrinter(conf_dict=carregar_modelos_extra())


def lista_modelos() -> list[str]:
    def chave(n):
        m = re.match(r"([A-Za-z\- ]*?)(\d+)", n)
        return (m.group(1), int(m.group(2)), n) if m else (n, 0, n)
    return sorted(_base().valid_printers, key=chave)


def modelo_suportado(nome: str) -> bool:
    return nome in _base().valid_printers


def normaliza_nome_modelo(texto: str) -> Optional[str]:
    """'EPSON L3150 Series' -> 'L3150'. Devolve o nome se estiver no banco,
    senão o nome limpo (para mostrar ao usuário)."""
    if not texto:
        return None
    t = texto.upper().replace("EPSON", "").replace("SERIES", "")
    t = t.replace("ECOTANK", "").strip()
    validos = {v.upper(): v for v in _base().valid_printers}
    for parte in [t] + t.split():
        parte = parte.strip()
        if parte in validos:
            return validos[parte]
    return t.split()[0] if t.split() else None


# --------------------------------------------------------------------------
# Conexão
# --------------------------------------------------------------------------
def criar_impressora(modelo: Optional[str], conexao: str,
                     ip: Optional[str] = None,
                     timeout: float = 4.0, retries: int = 2,
                     **usb_kwargs):
    extra = carregar_modelos_extra()
    if conexao == USB:
        cls = _epc.enable_usb_transport()
        if not hasattr(cls, "usb_describe"):
            raise RuntimeError(
                "Suporte USB indisponível (falta a biblioteca epson-usb).")
        return cls(conf_dict=extra, model=modelo, **usb_kwargs)
    if not ip:
        raise ValueError("Informe o IP da impressora.")
    cls = getattr(_epc, "NetworkEpsonPrinter", None) or _epc.EpsonPrinter
    return cls(conf_dict=extra, model=modelo, hostname=ip,
               timeout=timeout, retries=retries)


def fechar(impressora) -> None:
    fechar_fn = getattr(impressora, "close", None)
    if callable(fechar_fn):
        try:
            fechar_fn()
        except Exception:  # noqa: BLE001
            pass


def procurar_na_rede(progresso: Optional[Callable[[str], None]] = None) -> list[dict]:
    from find_printers import PrinterScanner
    if progresso:
        progresso("Procurando impressoras na rede (pode levar ~30 s)...")
    achadas = PrinterScanner().get_all_printers()
    resultado = []
    for p in achadas:
        nome = p.get("name") or ""
        if nome and "EPSON" not in nome.upper():
            continue
        resultado.append({
            "ip": p["ip"],
            "nome": nome or "(sem resposta SNMP)",
            "modelo": normaliza_nome_modelo(nome),
        })
    return resultado


def detectar_modelo(conexao: str, ip: Optional[str] = None) -> Optional[str]:
    """Pergunta à impressora qual é o modelo."""
    imp = criar_impressora(None, conexao, ip)
    try:
        nome = None
        try:
            di = imp.get_device_identification()
            if di and di.get("Model"):
                nome = di["Model"][0]
        except Exception as exc:  # noqa: BLE001
            log.debug("di falhou: %s", exc)
        if not nome and conexao == WIFI:
            try:
                nome = imp.get_snmp_info("Model").get("Model")
            except Exception as exc:  # noqa: BLE001
                log.debug("snmp Model falhou: %s", exc)
        return normaliza_nome_modelo(nome) if nome else None
    finally:
        fechar(imp)


# --------------------------------------------------------------------------
# Leitura
# --------------------------------------------------------------------------
def numero_serie(imp) -> Optional[str]:
    try:
        s = imp.get_serial_number()
        if s and "?" not in s:
            return s
    except Exception:  # noqa: BLE001
        pass
    try:
        st = imp.get_printer_status() or {}
        return st.get("serial_number_info")
    except Exception:  # noqa: BLE001
        return None


def ler_informacoes(imp) -> dict:
    info: dict = {"modelo": imp.model}
    try:
        info["firmware"] = imp.get_firmware_version()
    except Exception:  # noqa: BLE001
        info["firmware"] = None
    info["serie"] = numero_serie(imp)
    try:
        info["almofadas"] = imp.get_waste_ink_levels()
    except Exception as exc:  # noqa: BLE001
        log.debug("leitura almofadas: %s", exc)
        info["almofadas"] = None
    try:
        st = imp.get_printer_status() or {}
        info["status"] = st.get("status")
        info["caixa_manutencao"] = {
            k: v for k, v in st.items()
            if k.startswith("maintenance_box") and not k.endswith("counter")
        } or None
        info["erros"] = st.get("errcode")
    except Exception:  # noqa: BLE001
        pass
    if not (info.get("firmware") or info.get("serie") or info.get("status")
            or info.get("almofadas")):
        raise RuntimeError(
            "A impressora não respondeu.\nConfira se ela está ligada, o IP "
            "(ou o cabo USB) e se o PC está na mesma rede.")
    # EEPROM liberada? (firmware novo bloqueia gravação pela rede)
    info["eeprom_acessivel"] = info.get("almofadas") is not None
    return info


NOMES_ALMOFADA = {
    "main_waste": "Almofada principal",
    "borderless_waste": "Almofada sem margem",
    "first_waste": "Almofada 1",
    "second_waste": "Almofada 2",
    "third_waste": "Almofada 3",
}


# --------------------------------------------------------------------------
# Backup / restauração
# --------------------------------------------------------------------------
def celulas_do_reset(imp) -> list[int]:
    p = imp.parm or {}
    cel: set[int] = set()
    cel.update(p.get("raw_waste_reset", {}).keys())
    for t in NOMES_ALMOFADA:
        cel.update(p.get(t, {}).get("oids", []))
    cel.update(p.get("waste_reset_commit", {}).keys())
    return sorted(cel)


def fazer_backup(imp, conexao: str, ip: Optional[str] = None,
                 serie: Optional[str] = None) -> str:
    celulas = celulas_do_reset(imp)
    if not celulas:
        raise RuntimeError("Modelo sem endereços de contador no banco.")
    valores = imp.read_eeprom_many(celulas, label="backup")
    if not valores or any(v is None for v in valores):
        raise RuntimeError(
            "Não consegui ler a EEPROM para o backup. Por segurança o reset "
            "permanente foi cancelado.\nSe for Wi-Fi, o firmware pode estar "
            "bloqueando: tente o reset temporário ou o cabo USB.")
    agora = _dt.datetime.now()
    dados = {
        "app": "Printers3DUtility",
        "data": agora.isoformat(timespec="seconds"),
        "modelo": imp.model,
        "serie": serie,
        "conexao": conexao,
        "ip": ip,
        "eeprom": {str(c): int(v, 16) for c, v in zip(celulas, valores)},
    }
    nome = f"{imp.model}_{serie or 'semserie'}_{agora:%Y%m%d_%H%M%S}.json"
    nome = re.sub(r"[^\w.\-]", "_", nome)
    caminho = os.path.join(pasta_backups(), nome)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    return caminho


def restaurar_backup(imp, caminho: str) -> list:
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    if dados.get("modelo") and imp.model and dados["modelo"] != imp.model:
        raise RuntimeError(
            f"Backup é da {dados['modelo']}, mas o modelo escolhido é "
            f"{imp.model}.")
    relatorio: list = []
    for cel, val in sorted(dados["eeprom"].items(), key=lambda kv: int(kv[0])):
        if not imp.write_eeprom(int(cel), int(val), label="restaurar",
                                report=relatorio):
            raise RuntimeError(f"Falha ao gravar o endereço {cel}.")
    return relatorio


# --------------------------------------------------------------------------
# Resets
# --------------------------------------------------------------------------
def reset_permanente(imp, conexao: str, ip: Optional[str] = None) -> dict:
    if not imp.parm or not celulas_do_reset(imp):
        raise RuntimeError(
            f"O modelo {imp.model} ainda não tem os endereços do contador no "
            "banco. Use o reset temporário ou cadastre o modelo em "
            "modelos_extra.json.")
    serie = numero_serie(imp)
    backup = fazer_backup(imp, conexao, ip, serie)
    relatorio: list = []
    ok = imp.reset_waste_ink_levels(report=relatorio)
    alterados = [r for r in relatorio if len(r) >= 4 and r[3]]
    return {
        "ok": bool(ok),
        "backup": backup,
        "celulas_gravadas": len(relatorio),
        "celulas_alteradas": len(alterados),
        "depois": _seguro(imp.get_waste_ink_levels),
    }


def reset_temporario(imp) -> bool:
    """Comando 'rw' da Epson: só precisa do nº de série (não usa chave), por
    isso funciona até nos modelos fora do banco e nos com EEPROM bloqueada."""
    import hashlib
    import struct
    serie = None
    try:
        serie = (imp.get_printer_status() or {}).get("serial_number_info")
    except Exception:  # noqa: BLE001
        pass
    if (not serie or "?" in serie) and imp.parm:
        serie = numero_serie(imp)
    if not serie or "?" in serie:
        raise RuntimeError("Não consegui ler o número de série da impressora.")
    log.info("Número de série: %s", serie)
    oid = imp.epctrl_snmp_oid(
        "rw", struct.pack("<H", 1) + hashlib.sha1(serie.encode()).digest())
    resposta = imp.fetch_oid_values(oid, label="temp_reset_waste")[0][1]
    return (isinstance(resposta, (bytes, bytearray))
            and b"rw:" in bytes(resposta) and b":OK;" in bytes(resposta))


def descobrir_chave(imp, progresso: Optional[Callable[[str], None]] = None):
    def prog(tentativa, total, chave):
        if progresso:
            progresso(f"Testando chave {chave} ({tentativa}/{total})...")
    return imp.brute_force_read_key(progress=prog)


def _seguro(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None
