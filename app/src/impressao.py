"""
Teste de impressão: manda uma imagem (página de teste) para uma impressora
instalada no Windows, usando o próprio Windows (PowerShell + .NET), sem
programas extras. A impressora precisa estar instalada com o driver.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

SEM_JANELA = 0x08000000 if sys.platform == "win32" else 0

PAGINAS = [
    {
        "id": "qualidade",
        "nome": "Qualidade completa",
        "arquivo": "qualidade.png",
        "como_avaliar": [
            ("1 Cores sólidas", "Linhas brancas finas dentro de um bloco = bicos entupidos daquela cor. "
             "Faça limpeza de cabeça; se não sair, limpeza de cabeça a fundo / desentupimento."),
            ("Cor faltando", "Uma cor inteira não sai: tanque vazio, ar na mangueira, damper ou cabeça. "
             "Faça carga/limpeza a fundo e confira o caminho da tinta."),
            ("2 Degradês", "Faixas ou degraus no degradê = bicos falhando ou papel/modo de qualidade errado."),
            ("3 Escala de cinza", "Cinza puxando para uma cor = falta de uma das outras cores (bico entupido)."),
            ("4 Linhas finas", "Linhas verticais tortas ou dobradas = alinhamento da cabeça. "
             "Linhas horizontais com espaçamento irregular = alimentação do papel / encoder."),
            ("5 Texto pequeno", "Texto borrado ou duplicado = alinhamento da cabeça ou cabeça suja."),
            ("6 Faixa preta", "Manchas, riscos ou marcas repetidas = rolete sujo, almofada encharcada "
             "tocando o papel ou cabeça raspando."),
        ],
    },
    {
        "id": "barras_cmyk",
        "nome": "Barras CMYK (página cheia)",
        "arquivo": "barras_cmyk.png",
        "como_avaliar": [
            ("Para que serve", "Gasta bastante tinta de propósito: ajuda a puxar tinta depois de "
             "desentupimento ou troca de mangueira, e mostra falhas em toda a altura da página."),
            ("Listras brancas horizontais", "Bicos entupidos daquela cor. Faça limpeza e repita."),
            ("Cor clareando ao longo da folha", "A tinta não está chegando rápido: ar na mangueira, "
             "damper ou respiro do tanque."),
            ("Atenção", "Use em impressoras de tanque (EcoTank). Em cartucho gasta muita tinta."),
        ],
    },
]

COMO_AVALIAR_WINDOWS = [
    ("Página de teste do Windows", "É a mesma página de Propriedades da impressora > Imprimir página de teste. "
     "Confirma que o driver e a comunicação com o Windows estão funcionando."),
    ("Não saiu nada", "Verifique a fila de impressão, se a impressora certa está escolhida e se o driver está instalado."),
    ("Saiu, mas com falhas", "Use a página de Qualidade completa para identificar o defeito."),
]


def _recurso(nome: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "img", "testes", nome)


def caminho_pagina(pagina: dict, mini: bool = False) -> str:
    nome = pagina["arquivo"]
    if mini:
        nome = nome.replace(".png", "_mini.png")
    return _recurso(nome)


def _powershell(script: str, timeout: int = 60) -> str:
    if sys.platform != "win32":
        raise RuntimeError("A impressão do teste só funciona no Windows.")
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig") as f:
        f.write(script)
        arq = f.name
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", arq],
            capture_output=True, text=True, timeout=timeout, creationflags=SEM_JANELA)
    finally:
        try:
            os.remove(arq)
        except OSError:
            pass
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "Falha no PowerShell").strip()[-600:])
    return r.stdout


def listar_impressoras() -> tuple[list[str], str | None]:
    """(impressoras instaladas, impressora padrão). As conectadas vêm primeiro."""
    saida = _powershell(
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8\n"
        "Add-Type -AssemblyName System.Drawing\n"
        "$p = New-Object System.Drawing.Printing.PrinterSettings\n"
        "Write-Output ('PADRAO|' + $p.PrinterName)\n"
        "try {\n"
        "  foreach ($i in Get-CimInstance Win32_Printer) {\n"
        "    $off = [int]($i.WorkOffline -or $i.PrinterStatus -eq 7 -or $i.ExtendedPrinterStatus -eq 7)\n"
        "    Write-Output ('INFO|' + $off + '|' + $i.Name)\n"
        "  }\n"
        "} catch { }\n"
        "foreach ($n in [System.Drawing.Printing.PrinterSettings]::InstalledPrinters) { Write-Output ('IMP|' + $n) }\n")
    lista, padrao, offline = [], None, set()
    for linha in saida.splitlines():
        if linha.startswith("IMP|"):
            lista.append(linha[4:].strip())
        elif linha.startswith("PADRAO|"):
            padrao = linha[7:].strip() or None
        elif linha.startswith("INFO|"):
            _, off, nome = linha.split("|", 2)
            if off.strip() == "1":
                offline.add(nome.strip())
    global DESCONECTADAS
    DESCONECTADAS = offline
    # conectadas primeiro, mantendo a ordem do Windows
    lista.sort(key=lambda n: n in offline)
    return lista, padrao


DESCONECTADAS: set[str] = set()


def escolher_impressora(lista: list[str], padrao: str | None, modelo: str | None,
                        atual: str | None = None, lembrada: str | None = None) -> str | None:
    """Escolha da impressora, nesta ordem:
    1) a que já está escolhida na tela; 2) a última usada (salva);
    3) a do modelo que está conectada (padrão do Windows primeiro); 4) qualquer Epson conectada."""
    for n in (atual, lembrada):
        if n and n in lista:
            return n
    ligadas = [n for n in lista if n not in DESCONECTADAS] or lista
    for grupo in ([n for n in ligadas if modelo and modelo.upper() in n.upper()],
                  [n for n in ligadas if "EPSON" in n.upper()]):
        if grupo:
            return padrao if padrao in grupo else grupo[0]
    return padrao or (lista[0] if lista else None)


LOJA = {
    "nome": "Info 3D Cartuchos Express",
    "contato": "WhatsApp (21) 98660-0466  •  info3dcartuchos.com.br",
}


def _fonte(tam, negrito=False):
    from PIL import ImageFont
    nomes = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if negrito
             else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for n in nomes:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def preparar_pagina(caminho: str, impressora: str = "", modelo: str = "",
                    com_loja: bool = True) -> str:
    """Copia a página de teste e acrescenta um rodapé com o logo da loja,
    data/hora e a impressora testada. Devolve o caminho do arquivo pronto."""
    if not com_loja:
        return caminho
    import datetime as _dt
    from PIL import Image, ImageDraw
    im = Image.open(caminho).convert("RGB")
    w, h = im.size
    esc = w / 2480  # páginas geradas a 300 dpi (A4 = 2480 px)
    faixa = int(330 * esc)
    d = ImageDraw.Draw(im)
    y0 = h - faixa
    d.rectangle([0, y0, w, h], fill="white")
    d.line([int(150 * esc), y0 + int(10 * esc), w - int(150 * esc), y0 + int(10 * esc)],
           fill=(200, 200, 200), width=max(1, int(4 * esc)))
    x = int(150 * esc)
    try:
        bruto = Image.open(_recurso("logo_loja.png")).convert("RGBA")
        logo = Image.new("RGB", bruto.size, "white")
        logo.paste(bruto, mask=bruto.split()[3])  # fundo transparente vira branco
        lado = int(250 * esc)
        logo = logo.resize((lado, lado))
        im.paste(logo, (x, y0 + int(45 * esc)))
        x += lado + int(45 * esc)
    except OSError:
        pass
    agora = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        (f"Teste realizado com Printer's 3D Utility", _fonte(int(54 * esc), True), (20, 20, 20)),
        (LOJA["nome"], _fonte(int(44 * esc), True), (31, 63, 166)),
        (LOJA["contato"], _fonte(int(38 * esc)), (60, 60, 60)),
        (f"{agora}   •   {modelo or impressora or ''}".strip(" •"), _fonte(int(36 * esc)), (110, 110, 110)),
    ]
    y = y0 + int(50 * esc)
    for txt, f, cor in linhas:
        d.text((x, y), txt, fill=cor, font=f)
        y += int(f.size * 1.32) if hasattr(f, "size") else 20
    destino = os.path.join(tempfile.gettempdir(), "p3d_teste_" + os.path.basename(caminho))
    im.save(destino, dpi=(300, 300))
    return destino


def pagina_teste_windows(impressora: str) -> None:
    """Imprime a página de teste padrão do Windows (a mesma de
    Propriedades da impressora > Imprimir página de teste)."""
    if sys.platform != "win32":
        raise RuntimeError("A página de teste do Windows só funciona no Windows.")
    r = subprocess.run(["rundll32", "printui.dll,PrintUIEntry", "/k", "/n", impressora],
                       capture_output=True, text=True, timeout=60, creationflags=SEM_JANELA)
    if r.returncode != 0:
        raise RuntimeError("O Windows não conseguiu imprimir a página de teste.")


def _ps_texto(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def imprimir_imagem(caminho: str, impressora: str, copias: int = 1,
                    titulo: str = "Teste Printer's 3D Utility") -> None:
    if not os.path.exists(caminho):
        raise RuntimeError(f"Arquivo não encontrado: {caminho}")
    script = f"""
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile({_ps_texto(caminho)})
$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.DocumentName = {_ps_texto(titulo)}
$doc.PrinterSettings.PrinterName = {_ps_texto(impressora)}
if (-not $doc.PrinterSettings.IsValid) {{ throw 'Impressora não encontrada no Windows.' }}
$doc.PrinterSettings.Copies = {max(1, int(copias))}
$doc.DefaultPageSettings.Color = $true
$doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0,0,0,0)
$doc.add_PrintPage({{
  param($s, $e)
  $a = $e.PageSettings.PrintableArea
  $r = [Math]::Min($a.Width / $img.Width, $a.Height / $img.Height)
  $w = $img.Width * $r; $h = $img.Height * $r
  $x = ($e.PageBounds.Width - $w) / 2 - $e.PageSettings.HardMarginX
  $y = ($e.PageBounds.Height - $h) / 2 - $e.PageSettings.HardMarginY
  $e.Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $e.Graphics.DrawImage($img, [single]$x, [single]$y, [single]$w, [single]$h)
  $e.HasMorePages = $false
}})
try {{ $doc.Print() }} finally {{ $img.Dispose() }}
Write-Output 'OK'
"""
    _powershell(script, timeout=120)
