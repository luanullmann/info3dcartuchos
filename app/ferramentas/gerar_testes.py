"""Gera as páginas de teste (A4, 300 dpi) usadas na aba 'Teste de impressão'.
Rode:  python ferramentas/gerar_testes.py   (precisa do Pillow)"""
import os
from PIL import Image, ImageDraw, ImageFont

DPI = 300
W, H = 2480, 3508  # A4 a 300 dpi
SAIDA = os.path.join(os.path.dirname(__file__), "..", "src", "img", "testes")
C, M, Y, K = (0, 160, 228), (230, 0, 126), (255, 237, 0), (35, 31, 32)
R, G, B = (228, 30, 38), (0, 150, 64), (40, 60, 160)


def fonte(tam, negrito=False):
    for nome in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if negrito else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def barras_cmyk():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    larg = W // 4
    for i, cor in enumerate([C, M, Y, K]):
        d.rectangle([i * larg, 0, (i + 1) * larg if i < 3 else W, H], fill=cor)
    d.text((W - 80, H - 70), "Printer's 3D Utility • Barras CMYK", fill="white",
           font=fonte(34), anchor="rs")
    return im


def qualidade():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    mx = 150
    y = 130
    d.text((mx, y), "Teste de qualidade de impressão", fill=K, font=fonte(84, True))
    y += 110
    d.text((mx, y), "Printer's 3D Utility  •  compare cada bloco com a legenda", fill=(90, 90, 90), font=fonte(38))
    y += 110

    def titulo(txt):
        nonlocal y
        d.text((mx, y), txt, fill=K, font=fonte(42, True))
        y += 62

    largura = W - 2 * mx
    # 1. Blocos sólidos
    titulo("1  Cores sólidas (falha = linhas brancas → bico entupido)")
    cores = [C, M, Y, K, R, G, B]
    lb = largura // len(cores)
    for i, cor in enumerate(cores):
        d.rectangle([mx + i * lb, y, mx + (i + 1) * lb - 12, y + 330], fill=cor)
    for i, n in enumerate(["C", "M", "Y", "K", "R", "G", "B"]):
        d.text((mx + i * lb + 20, y + 340), n, fill=K, font=fonte(36, True))
    y += 440

    # 2. Degradês
    titulo("2  Degradês (deve ser suave, sem degraus nem faixas)")
    for cor in [C, M, Y, K]:
        for x in range(largura):
            t = x / (largura - 1)
            c = tuple(int(255 + (v - 255) * t) for v in cor)
            d.line([mx + x, y, mx + x, y + 120], fill=c)
        y += 140
    y += 30

    # 3. Escala de cinza
    titulo("3  Escala de cinza 0–100% (cinza não pode puxar para uma cor)")
    passos = 11
    lp = largura // passos
    for i in range(passos):
        v = int(255 - 255 * i / (passos - 1))
        d.rectangle([mx + i * lp, y, mx + (i + 1) * lp - 6, y + 170], fill=(v, v, v), outline=(200, 200, 200))
        d.text((mx + i * lp + lp // 2, y + 185), f"{i*10}%", fill=K, font=fonte(30), anchor="ma")
    y += 270

    # 4. Linhas finas
    titulo("4  Linhas finas (tortas/serrilhadas = alinhamento da cabeça)")
    meio = mx + largura // 2
    for i in range(0, largura // 2 - 20, 12):  # verticais
        d.line([mx + i, y, mx + i, y + 300], fill=K, width=2)
    for j in range(0, 300, 12):  # horizontais
        d.line([meio + 20, y + j, mx + largura, y + j], fill=K, width=2)
    y += 340
    for i in range(0, largura - 160, 40):  # diagonais coloridas
        d.line([mx + i, y, mx + i + 160, y + 160], fill=[C, M, Y, K][(i // 40) % 4], width=4)
    y += 210

    # 5. Texto pequeno
    titulo("5  Texto pequeno (deve ser legível e sem borrão)")
    for tam, pt in [(25, 6), (33, 8), (42, 10), (50, 12)]:
        d.text((mx, y), f"{pt} pt  —  A impressora Epson imprime este texto nítido. 0123456789",
               fill=K, font=fonte(tam))
        y += tam + 24
    y += 30

    # 6. Faixa de cobertura (borrão / rolete)
    titulo("6  Faixa preta (manchas ou marcas de rolete = rolete/almofada)")
    d.rectangle([mx, y, mx + largura, y + 160], fill=K)
    return im


if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    for nome, fn in [("barras_cmyk", barras_cmyk), ("qualidade", qualidade)]:
        im = fn()
        im.save(os.path.join(SAIDA, nome + ".png"), dpi=(DPI, DPI), optimize=True)
        p = im.copy(); p.thumbnail((300, 424)); p.save(os.path.join(SAIDA, nome + "_mini.png"))
        print(nome, "ok")
