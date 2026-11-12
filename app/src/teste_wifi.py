"""Assistente de teste de Wi-Fi: verificação automática e relatório (laudo).

Os passos manuais (folha de status, Wi-Fi Direct, WPS) são respondidos pelo
técnico na tela; a verificação pela rede é feita aqui; no fim sai um relatório
HTML com a logo da loja, pronto para imprimir ou salvar em PDF.
"""
from __future__ import annotations

import base64
import datetime as _dt
import html
import os
import socket
import webbrowser

import core
import impressao

# ---------------------------------------------------------------- perguntas
PASSOS = [
    {
        "id": "folha",
        "titulo": "1. Folha de status da rede",
        "instrucao": (
            "Coloque papel A4 e imprima a folha de status da rede.\n\n"
            "• Modelos sem tela (L3150, L3250, L4160…): segure o botão de estado de rede "
            "(o do \"i\") por uns 7 segundos.\n"
            "• Modelos com tela: Configurações > Status da rede > Imprimir folha de status.\n\n"
            "Veja o campo SSID e o Link Status (ou \"Estado\")."),
        "opcoes": [
            ("padrao", "SSID \"EpsonNet\": sem nenhuma rede salva (padrão de fábrica)"),
            ("procurando", "Tem a rede do cliente, mas Link Status \"Searching\" / desconectada"),
            ("conectada", "Tem a rede do cliente e está \"Connected\""),
            ("nao_imprimiu", "A folha não imprimiu"),
        ],
        "campo": "SSID que apareceu na folha (opcional)",
    },
    {
        "id": "direct",
        "titulo": "2. Wi-Fi Direct (testa o rádio, sem roteador)",
        "instrucao": (
            "Ative o Wi-Fi Direct (sem tela: segure o botão Wi-Fi e aperte o estado de rede "
            "até as luzes piscarem alternadas). Imprima a folha de novo: na parte "
            "<Wi-Fi Direct> estão o nome (DIRECT-…) e a senha.\n\n"
            "Conecte um celular ou o PC nessa rede."),
        "opcoes": [
            ("ok", "Conectou na rede DIRECT-…"),
            ("senha", "A rede aparece, mas não conecta"),
            ("nao_aparece", "A rede DIRECT-… nem aparece"),
            ("pulou", "Não testei"),
        ],
    },
    {
        "id": "roteador",
        "titulo": "3. Conexão no roteador da loja",
        "instrucao": (
            "Aperte o WPS do roteador (toque RÁPIDO de 1–2 s; segurar pode resetar o roteador) e, "
            "em até 2 minutos, segure o botão Wi-Fi da impressora por ~5 s. "
            "Ou conecte pelo app Epson Smart Panel.\n\n"
            "Conectou quando a luz do Wi-Fi fica acesa fixa. Imprima a folha de novo e anote o IP."),
        "opcoes": [
            ("ok", "Conectou (luz do Wi-Fi fixa / IP 192.168.x.x na folha)"),
            ("falhou", "Não conectou"),
            ("pulou", "Não testei"),
        ],
        "campo": "Sinal na folha (Excelente / Bom / Razoável / Fraco), opcional",
    },
]

RESULTADO_TXT = {(p["id"], o[0]): o[1] for p in PASSOS for o in p["opcoes"]}


# ---------------------------------------------------------------- verificação automática
def _porta_aberta(ip: str, porta: int, tempo: float = 2.0) -> bool:
    try:
        with socket.create_connection((ip, porta), timeout=tempo):
            return True
    except OSError:
        return False


def verificar_rede(ip: str) -> dict:
    """Testa a impressora pelo IP: portas, modelo, nº de série e firmware."""
    r: dict = {"ip": ip, "quando": _dt.datetime.now().isoformat(timespec="seconds")}
    r["porta_9100"] = _porta_aberta(ip, 9100)
    r["porta_80"] = _porta_aberta(ip, 80)
    r["modelo"] = None
    try:
        r["modelo"] = core.detectar_modelo(core.WIFI, ip)
    except Exception as exc:  # noqa: BLE001
        r["erro_snmp"] = str(exc)
    r["serie"] = r["firmware"] = None
    if r["modelo"] or r["porta_9100"] or r["porta_80"]:
        imp = None
        try:
            imp = core.criar_impressora(r["modelo"], core.WIFI, ip)
            r["serie"] = core.numero_serie(imp)
            try:
                r["firmware"] = imp.get_firmware_version()
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            r.setdefault("erro_snmp", str(exc))
        finally:
            if imp is not None:
                core.fechar(imp)
    r["respondeu"] = bool(r["modelo"] or r["porta_9100"] or r["porta_80"])
    return r


# ---------------------------------------------------------------- conclusão
def concluir(resp: dict, auto: dict | None) -> tuple[str, str, list[str]]:
    """(situação: ok|rede_cliente|roteador|defeito|incompleto, laudo, recomendações)"""
    folha = resp.get("folha")
    direct = resp.get("direct")
    roteador = resp.get("roteador")
    rede_ok = (auto or {}).get("respondeu") or roteador == "ok"
    rec: list[str] = []

    if rede_ok:
        partes = ["Wi-Fi da impressora testado na loja e funcionando: conectou no roteador"]
        if (auto or {}).get("respondeu"):
            partes[-1] += f" e respondeu pela rede no IP {auto['ip']}"
        if direct == "ok":
            partes.append("o Wi-Fi Direct também funcionou")
        laudo = "; ".join(partes) + "."
        if folha == "padrao":
            laudo += (" A impressora estava sem nenhuma rede salva (configuração de fábrica), "
                      "por isso não conectava na residência.")
        elif folha == "procurando":
            laudo += (" A impressora tinha a rede da residência salva, mas não a encontrava: "
                      "o problema está no roteador/rede do cliente (alcance, banda 5 GHz, senha ou "
                      "segurança alterada).")
        laudo += " Não há defeito no Wi-Fi da impressora."
        rec = [
            "Conectar a impressora no Wi-Fi da residência (app Epson Smart Panel ou WPS do roteador).",
            "Usar rede de 2,4 GHz: a impressora não conecta em 5 GHz. Se o roteador junta as duas "
            "bandas no mesmo nome, separar ou criar uma rede só 2,4 GHz.",
            "Segurança WPA2 (ou WPA2/WPA3 misto). Evitar só WPA3.",
            "Deixar a impressora a uma distância razoável do roteador.",
        ]
        return ("rede_cliente" if folha in ("padrao", "procurando") else "ok"), laudo, rec

    if direct == "ok" and roteador == "falhou":
        laudo = ("O rádio Wi-Fi da impressora funciona (conectou pelo Wi-Fi Direct), mas ela não "
                 "conseguiu entrar no roteador da loja.")
        rec = [
            "Restaurar as configurações de rede da impressora e repetir o WPS.",
            "Testar em outro roteador ou pelo app Epson Smart Panel.",
            "Se continuar falhando, verificar o módulo Wi-Fi e o cabo até a placa (falha intermitente).",
        ]
        return "roteador", laudo, rec

    if direct in ("nao_aparece", "senha") and roteador in ("falhou", None, "pulou"):
        laudo = ("A impressora não criou ou não aceitou conexão no Wi-Fi Direct e não conectou no "
                 "roteador da loja. Defeito provável no módulo Wi-Fi, antena ou cabo de ligação "
                 "com a placa principal.")
        rec = [
            "Restaurar as configurações de rede e repetir os testes.",
            "Conferir o cabo/conector do módulo Wi-Fi e a antena.",
            "Trocar o módulo Wi-Fi (ou a placa, se o módulo for integrado).",
        ]
        return "defeito", laudo, rec

    return "incompleto", ("Teste incompleto: faltam respostas para concluir. Repita os passos 2 e 3 "
                          "e a verificação pela rede."), []


# ---------------------------------------------------------------- relatório
SITUACAO = {
    "ok": ("APROVADO", "#16a34a"),
    "rede_cliente": ("APROVADO: problema na rede do cliente", "#16a34a"),
    "roteador": ("ATENÇÃO", "#d97706"),
    "defeito": ("REPROVADO: defeito no Wi-Fi", "#dc2626"),
    "incompleto": ("INCOMPLETO", "#6b7280"),
}


def _logo_b64() -> str:
    for c in (os.path.join(core.pasta_dados(), "logo_loja.png"), impressao._recurso("logo_loja.png")):
        try:
            with open(c, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except OSError:
            continue
    return ""


def gerar_relatorio(dados: dict) -> str:
    """Gera o HTML do relatório, salva em Documentos e devolve o caminho."""
    e = html.escape
    resp = dados.get("respostas", {})
    extras = dados.get("extras", {})
    auto = dados.get("auto") or {}
    sit, laudo, rec = dados["situacao"], dados["laudo"], dados.get("recomendacoes", [])
    rot, cor = SITUACAO.get(sit, SITUACAO["incompleto"])
    agora = _dt.datetime.now()
    logo = _logo_b64()

    linhas = []
    for p in PASSOS:
        v = resp.get(p["id"])
        txt = RESULTADO_TXT.get((p["id"], v), "Não respondido")
        extra = extras.get(p["id"])
        if extra:
            txt += f" ({extra})"
        icone = "✔" if v in ("ok", "conectada") else ("–" if v in (None, "pulou") else "•")
        linhas.append(f"<tr><td>{e(p['titulo'])}</td><td>{icone} {e(txt)}</td></tr>")
    if auto:
        if auto.get("respondeu"):
            t = (f"✔ Respondeu no IP {auto['ip']}"
                 + (f" · modelo {auto['modelo']}" if auto.get("modelo") else "")
                 + (" · porta de impressão 9100 aberta" if auto.get("porta_9100") else "")
                 + (" · painel web (80) aberto" if auto.get("porta_80") else ""))
        else:
            t = f"✖ Não respondeu no IP {auto.get('ip', '')}"
        linhas.append(f"<tr><td>4. Verificação pelo programa</td><td>{e(t)}</td></tr>")
        if auto.get("teste_bicos"):
            linhas.append(f"<tr><td>Impressão pela rede</td><td>✔ Teste de bicos enviado pelo Wi-Fi ({e(auto['teste_bicos'])})</td></tr>")

    imp = [("Modelo", dados.get("modelo") or auto.get("modelo")),
           ("Nº de série", auto.get("serie")), ("Firmware", auto.get("firmware")),
           ("IP na loja", auto.get("ip") if auto.get("respondeu") else None)]
    imp_html = "".join(f"<div><span>{e(k)}</span><b>{e(str(v))}</b></div>" for k, v in imp if v)
    os_ = [("OS nº", dados.get("os")), ("Cliente", dados.get("cliente")), ("Queixa", dados.get("queixa")),
           ("Técnico", dados.get("tecnico"))]
    os_html = "".join(f"<div><span>{e(k)}</span><b>{e(str(v))}</b></div>" for k, v in os_ if v)
    rec_html = "".join(f"<li>{e(r)}</li>" for r in rec)

    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório de teste de Wi-Fi</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;color:#14161a;margin:0;background:#f4f5f8}}
.pag{{max-width:780px;margin:20px auto;background:#fff;padding:32px 36px;box-shadow:0 1px 4px #0002}}
.top{{display:flex;gap:16px;align-items:center;border-bottom:2px solid #14213d;padding-bottom:14px}}
.top img{{width:84px;height:84px;object-fit:contain}}.top h1{{margin:0;font-size:20px}}
.top small{{display:block;color:#4a5163;font-size:12px;margin-top:2px}}
h2{{font-size:18px;margin:22px 0 6px}}.data{{color:#4a5163;font-size:13px}}
.selo{{display:inline-block;padding:8px 14px;border-radius:8px;color:#fff;font-weight:700;background:{cor};margin:12px 0}}
.grade{{display:grid;grid-template-columns:1fr 1fr;gap:6px 24px;font-size:14px;margin:8px 0 4px}}
.grade span{{color:#4a5163;display:block;font-size:12px}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px}}
td{{border:1px solid #d5d9e2;padding:8px 10px;vertical-align:top}}td:first-child{{width:38%;font-weight:600}}
.laudo{{background:#f4f5f8;border-left:4px solid {cor};padding:12px 14px;line-height:1.5;font-size:14px}}
ul{{font-size:14px;line-height:1.55;padding-left:20px}}
.ass{{display:flex;gap:40px;margin-top:48px}}.ass div{{flex:1;border-top:1px solid #000;text-align:center;padding-top:4px;font-size:13px}}
.rod{{margin-top:24px;font-size:11px;color:#6b7280;text-align:center}}
.bt{{position:fixed;right:20px;top:20px;padding:10px 16px;background:#2563eb;color:#fff;border:0;border-radius:8px;font-size:14px;cursor:pointer}}
@media print{{body{{background:#fff}}.pag{{box-shadow:none;margin:0;max-width:none}}.bt{{display:none}}}}
</style></head><body>
<button class="bt" onclick="window.print()">Imprimir / salvar PDF</button>
<div class="pag">
  <div class="top">{f'<img src="{logo}" alt="Logo">' if logo else ''}
    <div><h1>{e(impressao.LOJA['nome'])}</h1><small>{e(impressao.LOJA['contato'])}</small></div></div>
  <h2>Relatório de teste de Wi-Fi</h2>
  <div class="data">{agora.strftime('%d/%m/%Y às %H:%M')}</div>
  <div class="selo">{e(rot)}</div>
  {f'<div class="grade">{os_html}</div>' if os_html else ''}
  <div class="grade">{imp_html}</div>
  <h2>Testes realizados</h2>
  <table>{''.join(linhas)}</table>
  <h2>Laudo</h2>
  <div class="laudo">{e(laudo)}</div>
  {f'<h2>Recomendações</h2><ul>{rec_html}</ul>' if rec_html else ''}
  <div class="ass"><div>Técnico{(': ' + e(dados['tecnico'])) if dados.get('tecnico') else ''}</div><div>Cliente</div></div>
  <div class="rod">Relatório gerado pelo Printer's 3D Utility</div>
</div></body></html>"""

    pasta = os.path.join(core.pasta_dados(), "relatorios")
    os.makedirs(pasta, exist_ok=True)
    nome = "wifi_{}_{}.html".format(
        "".join(c for c in (auto.get("serie") or dados.get("modelo") or "impressora") if c.isalnum()),
        agora.strftime("%Y%m%d_%H%M"))
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(doc)
    return caminho


def abrir(caminho: str) -> None:
    webbrowser.open("file:///" + caminho.replace("\\", "/"))
