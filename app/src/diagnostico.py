"""
Diagnóstico: lê o status da impressora e o histórico de erros fatais e
transforma em mensagens em português, com o que verificar/trocar.

O conteúdo vem de duas fontes:
  1. Tabela embutida abaixo (status padrão Epson, que a impressora informa).
  2. diagnosticos.json (editável pela assistência): causa, solução e fotos de
     cada código. O que estiver no JSON complementa/substitui a tabela.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

import core

# --------------------------------------------------------------------------
# Tabela embutida: códigos de status padrão Epson (bloco ST2)
# chave -> (titulo, gravidade, o que fazer)
# gravidade: "erro", "aviso", "ok"
# --------------------------------------------------------------------------
STATUS_ERRO = {
    "Fatal error": ("st:00", "Erro fatal", "erro",
                    "A impressora travou com erro de hardware. Veja abaixo o "
                    "código no histórico de erros fatais para saber a causa."),
    "Other I/F is selected": ("st:01", "Outra interface em uso", "aviso",
                              "Outra conexão (USB/rede) está ocupando a impressora. "
                              "Cancele trabalhos pendentes e tente de novo."),
    "Cover Open": ("st:02", "Tampa aberta", "erro",
                   "Feche a tampa. Se já estiver fechada, verificar o sensor "
                   "da tampa e o cabo dele."),
    "Paper jam": ("st:04", "Papel atolado", "erro",
                  "Retire o papel e procure pedaços no caminho do papel. Se "
                  "persistir sem papel, verificar o sensor PE e os roletes."),
    "Ink out": ("st:05", "Sem tinta", "erro",
                "Complete/troque a tinta indicada e reinicie o contador de "
                "tinta no painel, se o modelo pedir."),
    "Paper out": ("st:06", "Sem papel / não puxa papel", "erro",
                  "Coloque papel. Se tiver papel e não puxar, verificar rolete "
                  "de alimentação (gasto/sujo) e sensor PE."),
    "Paper size or paper type or paper path error": (
        "st:0c", "Erro de tamanho/tipo/caminho do papel", "erro",
        "Confira o tamanho do papel configurado no driver e o papel na bandeja."),
    "Ink overflow error (Waste ink pad counter overflow)": (
        "st:10", "Almofada de tinta cheia", "erro",
        "Trocar ou lavar a almofada (ou instalar coletor externo) e depois "
        "fazer o Reset PERMANENTE."),
    "Double Feed": ("st:12", "Puxou duas folhas", "aviso",
                    "Verificar o separador de papel (pad de fricção) e os roletes."),
    "Cartridge cover is opened error": ("st:1a", "Tampa dos cartuchos/tanques aberta", "erro",
                                       "Feche a tampa. Se já estiver fechada, verificar o sensor."),
    "Maintenance cartridge is missing error": ("st:22", "Caixa de manutenção ausente", "erro",
                                               "Instale ou encaixe direito a caixa de manutenção."),
    "Rear cover is opened error": ("st:25", "Tampa traseira aberta", "erro",
                                   "Feche/encaixe a tampa traseira."),
    "Tray cover is opened": ("st:2b", "Tampa da bandeja aberta", "aviso",
                             "Feche a tampa da bandeja."),
    "Ink cartridge overflow error": ("st:2c", "Transbordamento de tinta", "erro",
                                     "Verificar vazamento nos tanques/mangueiras e a almofada."),
    "Initial filling is impossible error": ("st:33", "Carga inicial de tinta impossível", "erro",
                                            "Verificar se os tanques têm tinta suficiente para a carga inicial."),
    "Maintenance cartridge cover is opened error": ("st:36", "Tampa da caixa de manutenção aberta", "erro",
                                                    "Feche a tampa da caixa de manutenção."),
    "Scanner or front cover is opened error": ("st:37", "Scanner ou tampa frontal aberta", "erro",
                                               "Feche o scanner/tampa. Se fechado, verificar sensor."),
    "Maintenance request": ("st:41", "Pedido de manutenção (almofada)", "erro",
                            "Almofadas no fim da vida útil: trocar/lavar a almofada e fazer o "
                            "Reset PERMANENTE (ou temporário para liberar agora)."),
    "Printing disable error": ("st:47", "Impressão desabilitada", "erro",
                               "Leia os contadores: normalmente é almofada cheia."),
    "Maintenance Box near End error": ("st:4a", "Almofada/caixa quase cheia", "aviso",
                                       "Programe a troca ou limpeza da almofada."),
    "Driver mismatch error ": ("st:4b", "Driver incompatível", "aviso",
                               "Reinstale o driver correto do modelo."),
}

AVISOS = {
    "Ink low": ("Tinta baixa", "Complete a tinta indicada."),
    "Cleaning Disabled": ("Limpeza desabilitada (tinta baixa)",
                          "Complete a tinta antes de fazer limpeza de cabeça."),
    "Black print mode": ("Modo só preto", "A impressora está imprimindo só em preto."),
}

TRADUZ_CORES = {
    "Black": "Preto", "Cyan": "Ciano", "Magenta": "Magenta", "Yellow": "Amarelo",
    "Photo Black": "Preto foto", "Matte Black": "Preto fosco", "Red": "Vermelho",
    "Blue": "Azul", "Gloss optimizer": "Otimizador de brilho",
}


STATUS_PT = {
    "Error": "Erro", "Self Printing": "Imprimindo teste", "Busy": "Ocupada",
    "Waiting": "Aguardando", "Idle (ready to print)": "Pronta",
    "Paused": "Pausada", "Cleaning": "Limpando cabeça",
    "Factory shipment (not initialized)": "Nova (sem carga inicial)",
    "Shutdown": "Desligando", "Nozzle Check": "Teste de bicos", "Charging": "Carregando tinta",
}


# --------------------------------------------------------------------------
# Banco da assistência (diagnosticos.json + pasta fotos/)
# --------------------------------------------------------------------------
def arquivo_banco() -> str:
    return os.path.join(core.pasta_dados(), "diagnosticos.json")


def pasta_fotos() -> str:
    p = os.path.join(core.pasta_dados(), "fotos")
    os.makedirs(p, exist_ok=True)
    return p


def pasta_historico() -> str:
    p = os.path.join(core.pasta_dados(), "historico")
    os.makedirs(p, exist_ok=True)
    return p


def carregar_banco() -> dict:
    try:
        with open(arquivo_banco(), encoding="utf-8") as f:
            dados = json.load(f)
        return {k: v for k, v in dados.get("codigos", {}).items()
                if not k.startswith("_")}
    except (OSError, ValueError):
        return {}


def salvar_entrada(chave: str, titulo: str, causa: str, solucao: str,
                   fotos: list[str]) -> None:
    try:
        with open(arquivo_banco(), encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        dados = {}
    dados.setdefault("codigos", {})[chave] = {
        "titulo": titulo, "causa": causa, "solucao": solucao, "fotos": fotos,
    }
    with open(arquivo_banco(), "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def caminho_foto(nome: str) -> str:
    return nome if os.path.isabs(nome) else os.path.join(pasta_fotos(), nome)


# --------------------------------------------------------------------------
# Diagnóstico
# --------------------------------------------------------------------------
def _achado(chave, titulo, gravidade, solucao, causa="", detalhe=""):
    return {"chave": chave, "titulo": titulo, "gravidade": gravidade,
            "causa": causa, "solucao": solucao, "detalhe": detalhe, "fotos": []}


def _aplica_banco(achados: list[dict]) -> list[dict]:
    banco = carregar_banco()
    for a in achados:
        e = banco.get(a["chave"])
        if not e:
            continue
        a["titulo"] = e.get("titulo") or a["titulo"]
        a["causa"] = e.get("causa") or a["causa"]
        a["solucao"] = e.get("solucao") or a["solucao"]
        a["fotos"] = [caminho_foto(n) for n in e.get("fotos", [])]
        a["da_assistencia"] = True
    return achados


def diagnosticar(imp) -> dict:
    achados: list[dict] = []
    st = {}
    try:
        st = imp.get_printer_status() or {}
        if not isinstance(st, dict):
            st = {}
    except Exception:  # noqa: BLE001
        st = {}
    if not st:
        raise RuntimeError(
            "A impressora não respondeu ao pedido de status.\n"
            "Confira se está ligada, o IP (ou cabo USB) e a rede.")

    # 1. Erro atual
    err = st.get("errcode")
    if err:
        if err in STATUS_ERRO:
            chave, tit, grav, sol = STATUS_ERRO[err]
            achados.append(_achado(chave, tit, grav, sol,
                                   detalhe=f"Código de status {chave[3:].upper()}"))
        else:
            num = err.split(":")[-1].strip()
            achados.append(_achado(f"st:{num}", f"Código de status {num}", "erro",
                                   "Código ainda não cadastrado. Clique em "
                                   "'Editar solução' para registrar.", detalhe=err))

    # 2. Avisos
    for w in st.get("warning_code") or []:
        for prefixo, (tit, sol) in AVISOS.items():
            if w.startswith(prefixo):
                cor = w[len(prefixo):].strip(" ()")
                for en, pt in TRADUZ_CORES.items():
                    cor = cor.replace(en, pt)
                achados.append(_achado(f"aviso:{w}", f"{tit} {('- ' + cor) if cor else ''}".strip(),
                                       "aviso", sol, detalhe=w))
                break

    # 3. Papel / tampas
    pj = st.get("paper_jam")
    if isinstance(pj, str) and pj != "No jams":
        traduz = {"Paper jammed at ejecting": "Papel preso na saída",
                  "Paper jam in rear ASF or no feed": "Atolamento na alimentação traseira ou não puxa",
                  "No papers at rear ASF": "Sem papel na alimentação traseira"}
        achados.append(_achado("papel:" + pj, traduz.get(pj, pj), "erro",
                               "Verificar caminho do papel, roletes e sensor PE."))
    if st.get("tray_open") == "Open":
        achados.append(_achado("bandeja:aberta", "Bandeja de saída aberta/fechada errado",
                               "aviso", "Confira a bandeja de saída."))

    # 4. Caixa de manutenção (almofadas) pelo status
    for k, v in st.items():
        if k.startswith("maintenance_box_") and not k.startswith("maintenance_box_reset") \
                and isinstance(v, str) and not v.startswith("not full"):
            n = k.rsplit("_", 1)[-1]
            cheia = v.startswith("full")
            achados.append(_achado(
                f"almofada:{'cheia' if cheia else 'quase'}",
                f"Almofada {n} {'CHEIA' if cheia else 'quase cheia'}",
                "erro" if cheia else "aviso",
                "Trocar/lavar a almofada (ou coletor externo) e fazer o Reset "
                "PERMANENTE." if cheia else "Programe a troca/limpeza da almofada.",
                detalhe=v))

    # 5. Tinta
    for ink in st.get("ink_level") or []:
        try:
            _, _, nome, _, nivel = ink
        except ValueError:
            continue
        if isinstance(nivel, int) and nivel <= 10:
            cor = TRADUZ_CORES.get(nome, nome)
            achados.append(_achado(f"tinta:{nome}", f"Tinta {cor} em {nivel}%", "aviso",
                                   "Complete a tinta."))

    # 6. Contadores da EEPROM (se o modelo estiver no banco)
    almofadas = None
    if imp.parm:
        try:
            almofadas = imp.get_waste_ink_levels()
        except Exception:  # noqa: BLE001
            almofadas = None
        for k, v in (almofadas or {}).items():
            if v >= 90 and not any(a["chave"].startswith("almofada:") for a in achados):
                achados.append(_achado(
                    "almofada:cheia" if v >= 100 else "almofada:quase",
                    f"{core.NOMES_ALMOFADA.get(k, k)} em {v:.0f}%",
                    "erro" if v >= 100 else "aviso",
                    "Trocar/lavar a almofada e fazer o Reset PERMANENTE."))

    # 7. Histórico de erros fatais (EEPROM, só alguns modelos têm o endereço)
    fatais = []
    if imp.parm and "last_printer_fatal_errors" in imp.parm:
        try:
            fatais = [f for f in (imp.get_last_printer_fatal_errors() or [])
                      if f and f.upper() not in ("00", "FF")]
        except Exception:  # noqa: BLE001
            fatais = []
    banco = carregar_banco()
    for f in dict.fromkeys(fatais):
        chave = f"fatal:0x{f.upper()}"
        achados.append(_achado(
            chave, f"Erro fatal registrado: 0x{f.upper()}", "erro",
            "" if chave in banco else
            "Código ainda não cadastrado. Clique em 'Editar solução' para "
            "registrar a causa e a peça trocada.",
            detalhe="Histórico de erros fatais gravado na impressora"))

    if not achados:
        achados.append(_achado("ok", "Nenhum defeito informado pela impressora", "ok",
                               "Se o defeito é de impressão (falhas, listras, cores), "
                               "faça o teste de bicos pelo painel ou driver."))

    _aplica_banco(achados)
    status_txt = st.get("status")
    resultado = {
        "status": STATUS_PT.get(status_txt[1], status_txt[1])
        if isinstance(status_txt, tuple) else status_txt,
        "serie": st.get("serial_number_info") or core.numero_serie(imp),
        "modelo": imp.model,
        "almofadas": almofadas,
        "fatais": fatais,
        "achados": achados,
    }
    _registra_historico(resultado)
    return resultado


def _registra_historico(r: dict) -> None:
    serie = r.get("serie") or "sem_serie"
    nome = "".join(c if c.isalnum() else "_" for c in serie) + ".txt"
    try:
        with open(os.path.join(pasta_historico(), nome), "a", encoding="utf-8") as f:
            f.write(f"\n=== {_dt.datetime.now():%d/%m/%Y %H:%M}  {r.get('modelo') or ''} ===\n")
            for a in r["achados"]:
                f.write(f"[{a['gravidade']}] {a['titulo']}\n")
    except OSError:
        pass


def historico(serie: Optional[str]) -> str:
    if not serie:
        return ""
    nome = "".join(c if c.isalnum() else "_" for c in serie) + ".txt"
    try:
        with open(os.path.join(pasta_historico(), nome), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""
