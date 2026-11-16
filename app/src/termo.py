"""Gera o Termo de Garantia do serviço (HTML para imprimir ou salvar em PDF).

Texto baseado no Código de Defesa do Consumidor (Lei 8.078/1990, art. 26):
garantia legal de 90 dias para serviços e produtos duráveis. O termo detalha
cliente, OS, modelo, nº de série e o serviço realizado.
"""
from __future__ import annotations

import base64
import datetime as _dt
import html
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser

import core
import impressao


def _logo_b64() -> str:
    for c in (os.path.join(core.pasta_dados(), "logo_loja.png"),
              impressao._recurso("logo_loja.png")):
        try:
            with open(c, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except OSError:
            continue
    return ""


def _hoje_mais(dias: int) -> str:
    return (_dt.date.today() + _dt.timedelta(days=dias)).strftime("%d/%m/%Y")


def gerar_termo(dados: dict) -> str:
    """Gera o HTML do termo, salva em Documentos/.../termos e devolve o caminho."""
    e = html.escape
    loja = impressao.LOJA
    dias = int(dados.get("garantia_dias") or 90)
    hoje = _dt.date.today().strftime("%d/%m/%Y")
    logo = _logo_b64()

    linhas_os = [
        ("Cliente", dados.get("cliente")),
        ("WhatsApp / contato", dados.get("contato")),
        ("Ordem de serviço nº", dados.get("os")),
        ("Aparelho", dados.get("modelo")),
        ("Nº de série", dados.get("serie")),
        ("Serviço realizado", dados.get("servico")),
        ("Data do serviço", hoje),
        ("Garantia", f"{dias} dias (até {_hoje_mais(dias)})"),
        ("Técnico responsável", dados.get("tecnico")),
    ]
    tabela = "".join(
        f"<tr><th>{e(k)}</th><td>{e(str(v))}</td></tr>"
        for k, v in linhas_os if v)

    condicoes = [
        "Esta garantia cobre exclusivamente o serviço executado e as peças "
        "substituídas descritos nesta ordem de serviço.",
        "A garantia legal é de 90 (noventa) dias, conforme o art. 26, inciso II, "
        "do Código de Defesa do Consumidor (Lei nº 8.078/1990), contados a partir "
        "da entrega do aparelho.",
        "A garantia NÃO cobre: mau uso, quedas, contato com líquidos, uso de tinta "
        "ou cartucho de má qualidade, oscilação ou descarga elétrica, problemas em "
        "peças ou defeitos diferentes do serviço descrito acima, e violação do lacre "
        "de garantia da assistência.",
        "Para acionar a garantia, o cliente deve apresentar este termo ou a via da "
        "ordem de serviço.",
        "O prazo para retirada do aparelho após o aviso de conclusão é de 90 dias; "
        "após esse período, poderá ser cobrada taxa de armazenagem.",
    ]
    cond_html = "".join(f"<li>{e(c)}</li>" for c in condicoes)

    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Termo de Garantia - OS {e(str(dados.get('os') or ''))}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;color:#14161a;margin:0;background:#f4f5f8}}
.pag{{max-width:780px;margin:20px auto;background:#fff;padding:34px 40px;box-shadow:0 1px 4px #0002}}
.top{{display:flex;gap:16px;align-items:center;border-bottom:3px solid #14213d;padding-bottom:16px}}
.top img{{width:90px;height:90px;object-fit:contain}}
.top h1{{margin:0;font-size:22px}}
.top small{{display:block;color:#4a5163;font-size:12px;line-height:1.5;margin-top:3px}}
h2{{font-size:20px;text-align:center;margin:22px 0 4px;letter-spacing:.5px}}
.data{{text-align:center;color:#4a5163;font-size:13px;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #d5d9e2;padding:9px 11px;text-align:left;vertical-align:top}}
th{{width:34%;background:#f4f5f8;font-weight:600}}
h3{{font-size:15px;margin:22px 0 6px}}
ol{{font-size:13px;line-height:1.6;padding-left:20px;margin:0}}
.ass{{display:flex;gap:50px;margin-top:60px}}
.ass div{{flex:1;border-top:1px solid #000;text-align:center;padding-top:6px;font-size:13px}}
.rod{{margin-top:26px;font-size:11px;color:#6b7280;text-align:center;border-top:1px solid #e1e4eb;padding-top:10px}}
.bt{{position:fixed;right:20px;top:20px;padding:10px 16px;background:#2563eb;color:#fff;border:0;border-radius:8px;font-size:14px;cursor:pointer}}
@media print{{body{{background:#fff}}.pag{{box-shadow:none;margin:0;max-width:none}}.bt{{display:none}}}}
</style></head><body>
<button class="bt" onclick="window.print()">Imprimir / salvar PDF</button>
<div class="pag">
  <div class="top">
    {f'<img src="{logo}" alt="Logo">' if logo else ''}
    <div>
      <h1>{e(loja['nome'])}</h1>
      <small>{f"CNPJ {e(loja.get('cnpj',''))}<br>" if loja.get('cnpj') else ''}
        {e(loja.get('endereco',''))}<br>{e(loja.get('contato',''))}</small>
    </div>
  </div>

  <h2>TERMO DE GARANTIA</h2>
  <div class="data">Emitido em {hoje}</div>

  <table>{tabela}</table>

  <h3>Condições da garantia</h3>
  <ol>{cond_html}</ol>

  <p style="font-size:13px;margin-top:18px">Declaro estar ciente e de acordo com as
  condições de garantia acima e confirmo o recebimento do aparelho.</p>

  <div class="ass">
    <div>Cliente{f" — {e(dados['cliente'])}" if dados.get('cliente') else ''}</div>
    <div>{e(loja['nome'])}</div>
  </div>

  <div class="rod">Termo gerado pelo Printer's 3D Utility — {e(loja['nome'])}</div>
</div></body></html>"""

    pasta = core.pasta_cliente(dados, "Garantia")
    nome = f"Termo de garantia {_dt.datetime.now().strftime('%Y-%m-%d')}.html"
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(doc)
    return caminho


def abrir(caminho: str) -> None:
    webbrowser.open("file:///" + caminho.replace("\\", "/"))


def _navegador() -> str | None:
    """Edge (vem em todo Windows 10/11) ou Chrome, para gerar o PDF sem abrir janela."""
    cands = []
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    cands += [shutil.which("msedge") or "", shutil.which("chrome") or "", shutil.which("chromium") or ""]
    return next((c for c in cands if c and os.path.isfile(c)), None)


def gerar_pdf(caminho_html: str) -> str | None:
    """Converte o termo em PDF na mesma pasta do cliente. Devolve o caminho do PDF (ou None)."""
    nav = _navegador()
    if not nav:
        return None
    pdf = os.path.splitext(caminho_html)[0] + ".pdf"
    perfil = tempfile.mkdtemp(prefix="p3d-pdf-")  # perfil separado: não interfere no Edge aberto
    try:
        if os.path.exists(pdf):
            os.remove(pdf)
        from pathlib import Path
        url = Path(os.path.abspath(caminho_html)).as_uri()  # trata espaços e apóstrofo ("Printer's 3D Utility")
        subprocess.run([nav, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                        "--print-to-pdf-no-header", f"--user-data-dir={perfil}", f"--print-to-pdf={pdf}", url],
                       timeout=60, capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0)
        return pdf if os.path.isfile(pdf) and os.path.getsize(pdf) > 1000 else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        shutil.rmtree(perfil, ignore_errors=True)
