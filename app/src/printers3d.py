"""
Printer's 3D Utility - reset de almofadas, diagnóstico e tabela de erros
para impressoras Epson, por Wi-Fi ou USB.

A comunicação com a impressora usa a biblioteca aberta epson_print_conf
(Ircama, EUPL-1.2).
"""
from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core
import diagnostico as dg
import erros_epson
import impressao
import manutencao
import teste_wifi

try:
    import sv_ttk
except ImportError:  # tema moderno é opcional
    sv_ttk = None
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

NOME = "Printer's 3D Utility"
VERSAO = "2.7"

COR = {
    "acento": "#2563eb", "acento2": "#1e40af",
    "erro": "#dc2626", "aviso": "#d97706", "ok": "#16a34a",
    "cinza": "#6b7280",
}

AVISO_ALMOFADA = (
    "ATENÇÃO: zerar o contador só libera a impressora.\n\n"
    "Se a almofada (ou o coletor de tinta) não for trocada ou limpa, a tinta "
    "pode vazar dentro da impressora e sobre a placa.\n\n"
    "Um backup da EEPROM será salvo antes de gravar.\n\nContinuar?"
)


def _recurso(nome: str) -> str:
    """Caminho de um arquivo da pasta img (funciona no .exe e no script)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "img", nome)


def _imagem(nome: str):
    try:
        return tk.PhotoImage(file=_recurso(nome))
    except Exception:  # noqa: BLE001
        return None


def _imagem_arquivo(caminho: str, altura: int):
    try:
        if Image:
            im = Image.open(caminho)
            im.thumbnail((altura * 2, altura))
            return ImageTk.PhotoImage(im)
        return tk.PhotoImage(file=caminho)
    except Exception:  # noqa: BLE001
        return None


class LogHandler(logging.Handler):
    def __init__(self, fila):
        super().__init__(logging.INFO)
        self.fila = fila

    def emit(self, record):
        self.fila.put(("log", self.format(record)))


# ======================================================================
# Painel de detalhe com foto (usado no Diagnóstico e na Tabela de erros)
# ======================================================================
class PainelDetalhe(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=(12, 8))
        self.app = app
        self.item: dict | None = None
        self.fotos: list[str] = []
        self.idx = 0
        self._img = None

        self.lb_titulo = ttk.Label(self, text="Selecione um item", font=("Segoe UI", 13, "bold"),
                                   wraplength=360, justify="left")
        self.lb_titulo.pack(anchor="w")
        self.lb_sub = ttk.Label(self, text="", foreground=COR["cinza"], wraplength=360)
        self.lb_sub.pack(anchor="w", pady=(0, 6))

        nav = ttk.Frame(self)
        nav.pack(side="bottom", fill="x", pady=(6, 0))
        self.foto = ttk.Label(self, text="Sem foto cadastrada", anchor="center",
                              foreground=COR["cinza"])
        self.foto.pack(side="bottom", fill="x", pady=4)

        sb = ttk.Scrollbar(self)
        sb.pack(side="right", fill="y")
        self.txt = tk.Text(self, height=6, wrap="word", relief="flat", borderwidth=0,
                           font=("Segoe UI", 10), padx=6, pady=6, yscrollcommand=sb.set)
        sb.configure(command=self.txt.yview)
        self.txt.tag_configure("cab", font=("Segoe UI", 10, "bold"))
        self.txt.tag_configure("nota", foreground=COR["acento"])
        self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")

        self.bt_ant = ttk.Button(nav, text="◀", width=3, command=lambda: self._muda(-1))
        self.bt_prox = ttk.Button(nav, text="▶", width=3, command=lambda: self._muda(1))
        self.lb_n = ttk.Label(nav, text="")
        self.bt_ant.pack(side="left")
        self.lb_n.pack(side="left", padx=6)
        self.bt_prox.pack(side="left")
        ttk.Button(nav, text="Editar solução", command=self.editar).pack(side="right")
        ttk.Button(nav, text="Adicionar foto", command=self.add_foto).pack(side="right", padx=6)

    # item: chave, titulo, sub, linhas[(cab, texto)], fotos
    def mostrar(self, item: dict):
        self.item = item
        self.lb_titulo.configure(text=item.get("titulo", ""))
        self.lb_sub.configure(text=item.get("sub", ""))
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for cab, texto, *tag in item.get("linhas", []):
            if not texto:
                continue
            self.txt.insert("end", cab + "\n", "cab")
            self.txt.insert("end", texto + "\n\n", tuple(tag))
        self.txt.configure(state="disabled")
        self.fotos = [f for f in item.get("fotos", []) if os.path.exists(f)]
        self.idx = 0
        self._desenha()

    def _muda(self, d):
        if self.fotos:
            self.idx = (self.idx + d) % len(self.fotos)
            self._desenha()

    def _desenha(self):
        if not self.fotos:
            self._img = None
            self.foto.configure(image="", text="Sem foto cadastrada.\n"
                                "Use 'Adicionar foto' para mostrar a peça/defeito.")
            self.lb_n.configure(text="")
            return
        caminho = self.fotos[self.idx]
        try:
            if Image:
                im = Image.open(caminho)
                im.thumbnail((360, 170))
                self._img = ImageTk.PhotoImage(im)
            else:
                self._img = tk.PhotoImage(file=caminho)
            self.foto.configure(image=self._img, text="")
        except Exception:  # noqa: BLE001
            self._img = None
            self.foto.configure(image="", text=f"Não consegui abrir {os.path.basename(caminho)}")
        self.lb_n.configure(text=f"{self.idx + 1}/{len(self.fotos)}")

    def _entrada_atual(self):
        banco = dg.carregar_banco()
        chave = self.item["chave"]
        e = banco.get(chave, {})
        return chave, e

    def add_foto(self):
        if not self.item:
            return
        arqs = filedialog.askopenfilenames(
            title="Escolha a(s) foto(s)",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("Todos", "*.*")])
        if not arqs:
            return
        chave, e = self._entrada_atual()
        nomes = list(e.get("fotos", []))
        base = re.sub(r"[^\w\-]", "_", chave)
        for a in arqs:
            ext = os.path.splitext(a)[1].lower()
            n = 1
            while os.path.exists(os.path.join(dg.pasta_fotos(), f"{base}_{n}{ext}")):
                n += 1
            nome = f"{base}_{n}{ext}"
            shutil.copy2(a, os.path.join(dg.pasta_fotos(), nome))
            nomes.append(nome)
        dg.salvar_entrada(chave, e.get("titulo", ""), e.get("causa", ""),
                          e.get("solucao", ""), nomes)
        self.app.recarregar_item(self.item)

    def editar(self):
        if not self.item:
            return
        chave, e = self._entrada_atual()
        win = tk.Toplevel(self)
        win.title("Solução da assistência")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        fr = ttk.Frame(win, padding=14)
        fr.pack(fill="both", expand=True)
        ttk.Label(fr, text=f"Código: {chave}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        campos = {}
        for rotulo, k, h in [("Título (opcional)", "titulo", 1),
                             ("Causa encontrada", "causa", 4),
                             ("O que resolveu / peça trocada", "solucao", 6)]:
            ttk.Label(fr, text=rotulo).pack(anchor="w", pady=(8, 2))
            t = tk.Text(fr, height=h, width=56, wrap="word", font=("Segoe UI", 10))
            t.insert("1.0", e.get(k, ""))
            t.pack(fill="x")
            campos[k] = t

        def salvar():
            dg.salvar_entrada(chave, campos["titulo"].get("1.0", "end").strip(),
                              campos["causa"].get("1.0", "end").strip(),
                              campos["solucao"].get("1.0", "end").strip(),
                              e.get("fotos", []))
            win.destroy()
            self.app.recarregar_item(self.item)
        bts = ttk.Frame(fr)
        bts.pack(fill="x", pady=(12, 0))
        ttk.Button(bts, text="Salvar", style="Accent.TButton", command=salvar).pack(side="right")
        ttk.Button(bts, text="Cancelar", command=win.destroy).pack(side="right", padx=6)


# ======================================================================
# Janela principal
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{NOME} {VERSAO}")
        self.geometry("1000x760")
        self.minsize(900, 640)
        self._icone = _imagem("logo_janela.png")
        if self._icone:
            self.iconphoto(True, self._icone)
        if sys.platform == "win32":
            try:
                self.iconbitmap(default=_recurso("icone.ico"))
            except tk.TclError:
                pass
        self.fila: queue.Queue = queue.Queue()
        self.ocupado = False
        self.modelos = core.lista_modelos()
        self.ultimo_diag: dict | None = None
        self.barras: dict[str, tuple] = {}
        self.botoes: list = []
        self.imp_nome_m = tk.StringVar()

        h = LogHandler(self.fila)
        h.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(h)
        logging.getLogger().setLevel(logging.WARNING)
        core.log.setLevel(logging.INFO)

        if sv_ttk:
            sv_ttk.set_theme("light")
        self._estilos()
        self._cabecalho()
        self._conexao()
        self._abas()
        self._rodape()
        self.after(100, self._processa_fila)
        self.escreve(f"{NOME} {VERSAO} - {len(self.modelos)} modelos Epson no banco.")

    # ------------------------------------------------------------ estilo
    def _estilos(self):
        s = ttk.Style(self)
        if not sv_ttk:
            try:
                s.theme_use("vista" if sys.platform == "win32" else "clam")
            except tk.TclError:
                pass
        s.configure("Perigo.TButton", foreground=COR["erro"])
        s.configure("Titulo.TLabel", font=("Segoe UI", 11, "bold"))
        s.configure("Treeview", rowheight=26)

    def _cabecalho(self):
        cab = tk.Frame(self, bg=COR["acento"], height=64)
        cab.pack(fill="x")
        self._logo_cab = _imagem("logo_cab.png")
        if self._logo_cab:
            tk.Label(cab, image=self._logo_cab, bg=COR["acento"]).pack(side="left", padx=(14, 10), pady=6)
        txt = tk.Frame(cab, bg=COR["acento"])
        txt.pack(side="left", pady=8)
        tk.Label(txt, text=NOME, bg=COR["acento"], fg="white",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(txt, text="Reset de almofadas • Diagnóstico • Tabela de erros Epson",
                 bg=COR["acento"], fg="#dbeafe", font=("Segoe UI", 9)).pack(anchor="w")
        if sv_ttk:
            self.tema = tk.StringVar(value="light")
            tk.Button(cab, text="◐ Tema", bg=COR["acento2"], fg="white", relief="flat",
                      activebackground=COR["acento"], activeforeground="white",
                      font=("Segoe UI", 9), padx=10, command=self._troca_tema
                      ).pack(side="right", padx=16)

    def _troca_tema(self):
        sv_ttk.toggle_theme()
        self._estilos()
        escuro = sv_ttk.get_theme() == "dark"
        for t in (self.txt_log, self.det_diag.txt, self.det_tab.txt, self.txt_avaliar):
            t.configure(bg="#1c1c1c" if escuro else "white", fg="#e5e5e5" if escuro else "black",
                        insertbackground="white" if escuro else "black")

    # ------------------------------------------------------------ conexão
    def _conexao(self):
        fr = ttk.Frame(self, padding=(14, 10, 14, 4))
        fr.pack(fill="x")
        c1 = ttk.LabelFrame(fr, text=" Conexão ", padding=(10, 6))
        c1.pack(side="left", fill="both", expand=True)
        self.conexao = tk.StringVar(value=core.WIFI)
        ttk.Radiobutton(c1, text="Wi-Fi / rede", value=core.WIFI, variable=self.conexao,
                        command=self._troca_conexao).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(c1, text="Cabo USB", value=core.USB, variable=self.conexao,
                        command=self._troca_conexao).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(c1, text="IP:").grid(row=1, column=0, sticky="w", pady=6)
        self.ip = tk.StringVar()
        self.ent_ip = ttk.Entry(c1, textvariable=self.ip, width=16)
        self.ent_ip.grid(row=1, column=0, sticky="e", padx=(28, 0))
        self.bt_procurar = ttk.Button(c1, text="Procurar na rede", command=self.procurar)
        self.bt_procurar.grid(row=1, column=1, sticky="w", padx=10)
        ttk.Label(c1, text="Sem roteador: conecte no Wi-Fi Direct da impressora (192.168.223.1)",
                  foreground=COR["cinza"], font=("Segoe UI", 8)).grid(row=2, column=0,
                                                                      columnspan=3, sticky="w")

        c2 = ttk.LabelFrame(fr, text=" Modelo ", padding=(10, 6))
        c2.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.modelo = tk.StringVar()
        self.cb_modelo = ttk.Combobox(c2, textvariable=self.modelo, values=self.modelos, width=18)
        self.cb_modelo.grid(row=0, column=0, sticky="w")
        self.cb_modelo.bind("<<ComboboxSelected>>", lambda e: self._atualiza_suporte())
        self.cb_modelo.bind("<KeyRelease>", self._filtra_modelos)
        ttk.Button(c2, text="Detectar", command=self.detectar).grid(row=0, column=1, padx=8)
        self.lb_suporte = ttk.Label(c2, text="Escolha ou detecte o modelo.",
                                    foreground=COR["cinza"], wraplength=380)
        self.lb_suporte.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _troca_conexao(self):
        estado = "normal" if self.conexao.get() == core.WIFI else "disabled"
        self.ent_ip.configure(state=estado)
        self.bt_procurar.configure(state=estado)

    def _filtra_modelos(self, _e):
        t = self.modelo.get().upper()
        self.cb_modelo["values"] = [m for m in self.modelos if t in m.upper()] or self.modelos
        self._atualiza_suporte()

    def _atualiza_suporte(self):
        m = self.modelo.get().strip()
        if not m:
            self.lb_suporte.configure(text="Escolha ou detecte o modelo.", foreground=COR["cinza"])
        elif m in core.EQUIVALENTES:
            self.lb_suporte.configure(foreground=COR["acento"],
                                      text=f"✔ {m} = mesma impressora da {core.EQUIVALENTES[m]}: leitura e reset "
                                           "permanente pelo USB (novo, confira na 1ª vez).")
        elif core.modelo_suportado(m):
            self.lb_suporte.configure(foreground=COR["ok"],
                                      text=f"✔ {m} no banco: leitura e reset permanente.")
        else:
            self.lb_suporte.configure(foreground=COR["aviso"],
                                      text=f"⚠ {m} fora do banco: só reset temporário e diagnóstico.")

    # ------------------------------------------------------------ abas
    def _abas(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(6, 4))
        self._aba_reset()
        self._aba_manut()
        self._aba_diag()
        self._aba_tabela()
        self._aba_teste()
        self._aba_wifi()
        self._aba_log()

    def _aba_reset(self):
        f = ttk.Frame(self.nb, padding=14)
        self.nb.add(f, text="  Reset de almofadas  ")
        topo = ttk.Frame(f)
        topo.pack(fill="x")
        self.botoes = []
        for txt, cmd, st in [("Ler contadores", self.ler, "Accent.TButton"),
                             ("Reset PERMANENTE", self.reset_perm, "Perigo.TButton"),
                             ("Reset temporário", self.reset_temp, None)]:
            b = ttk.Button(topo, text=txt, command=cmd, **({"style": st} if st else {}))
            b.pack(side="left", fill="x", expand=True, padx=4, ipady=6)
            self.botoes.append(b)

        self.card_info = ttk.LabelFrame(f, text=" Impressora ", padding=12)
        self.card_info.pack(fill="x", pady=12)
        self.lb_info = ttk.Label(self.card_info, text="Clique em 'Ler contadores'.",
                                 font=("Segoe UI", 10))
        self.lb_info.pack(anchor="w")
        self.fr_barras = ttk.Frame(self.card_info)
        self.fr_barras.pack(fill="x", pady=(8, 0))

        mais = ttk.Frame(f)
        mais.pack(fill="x")
        for txt, cmd in [("Restaurar backup", self.restaurar),
                         ("Abrir pasta de backups", self.abrir_backups),
                         ("Descobrir chave (avançado)", self.chave)]:
            b = ttk.Button(mais, text=txt, command=cmd)
            b.pack(side="left", padx=4)
            self.botoes.append(b)
        ttk.Label(f, foreground=COR["cinza"], wraplength=880, justify="left",
                  text="Lembre: o reset só libera a impressora. Troque ou lave a almofada "
                       "(ou instale coletor externo) para a tinta não vazar na placa."
                  ).pack(anchor="w", pady=(14, 0))

    # ------------------------------------------------------------ manutenção
    def _aba_manut(self):
        f = ttk.Frame(self.nb, padding=12)
        self.nb.add(f, text="  Manutenção / Firmware  ")
        esq = ttk.Frame(f)
        esq.pack(side="left", fill="both", expand=True)

        lp = ttk.LabelFrame(esq, text=" Limpeza do cabeçote e carga de tinta ", padding=10)
        lp.pack(fill="x")
        ttk.Label(lp, wraplength=470, justify="left", foreground=COR["cinza"],
                  text="Wi-Fi: vai direto pelo IP. USB: escolha a impressora do Windows "
                       "(precisa do driver instalado).").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(lp, text="Impressora (USB):").grid(row=1, column=0, sticky="w", pady=6)
        self.cb_imp_m = ttk.Combobox(lp, textvariable=self.imp_nome_m, width=30, state="readonly")
        self.cb_imp_m.bind("<<ComboboxSelected>>", lambda _e: self._lembrar_impressora(self.imp_nome_m.get()))
        self.cb_imp_m.grid(row=1, column=1, sticky="w")
        ttk.Button(lp, text="Atualizar", command=self.carregar_impressoras).grid(row=1, column=2, padx=6)
        for i, chave in enumerate(("bicos", "cl1", "cl2", "cl3")):
            r = manutencao.ROTINAS[chave]
            estilo = "Accent.TButton" if chave == "cl1" else "TButton"
            b = ttk.Button(lp, text=r["nome"], style=estilo, width=34,
                           command=lambda c=chave: self.rodar_manut(c))
            b.grid(row=2 + i, column=0, columnspan=2, sticky="w", pady=3)
            self.botoes.append(b)
            ttk.Label(lp, text=r["aviso"], wraplength=300, foreground=COR["cinza"],
                      font=("Segoe UI", 8), justify="left").grid(row=2 + i, column=2, sticky="w", padx=6)

        fw = ttk.LabelFrame(esq, text=" Firmware ", padding=10)
        fw.pack(fill="x", pady=10)
        b = ttk.Button(fw, text="Ler firmware, cabeçote e contadores", command=self.ler_firmware)
        b.grid(row=0, column=0, sticky="w")
        self.botoes.append(b)
        ttk.Button(fw, text="Baixar firmware oficial do modelo",
                   command=self.abrir_firmware).grid(row=0, column=1, padx=8)
        ttk.Button(fw, text="Atualizar pelo painel web (Wi-Fi)",
                   command=self.abrir_painel).grid(row=0, column=2)
        self.lb_fw = ttk.Label(fw, text="Firmware: —", style="Titulo.TLabel")
        self.lb_fw.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Separator(f, orient="vertical").pack(side="left", fill="y", padx=12)
        dir_ = ttk.Frame(f)
        dir_.pack(side="left", fill="both", expand=True)
        ttk.Label(dir_, text="Leia antes", style="Titulo.TLabel").pack(anchor="w")
        t = tk.Text(dir_, wrap="word", relief="flat", borderwidth=0, font=("Segoe UI", 10),
                    padx=6, pady=6, height=20)
        t.pack(fill="both", expand=True, pady=(6, 0))
        t.insert("end", "LIMPEZA\n• Faça o teste de bicos primeiro. Falhou? CL1, espere 1 min e "
                        "teste de novo. Até 2 vezes CL1, depois uma CL2.\n• Não repita sem parar: "
                        "cada limpeza enche a almofada.\n• Continuou falhando depois da CL2? "
                        "Deixe descansar 6 h ou mais, ou faça limpeza manual do cabeçote.\n"
                        "• CL3 (carga de tinta) só depois de troca de peças ou com ar na linha.\n"
                        "• O efeito exato de cada nível varia por modelo; teste na bancada antes.\n\n")
        t.insert("end", manutencao.AVISO_FIRMWARE)
        t.configure(state="disabled")
        self.contadores_txt = t

    def _destino_manut(self):
        if self.conexao.get() == core.WIFI:
            ip = self.ip.get().strip()
            if not ip:
                messagebox.showwarning("Falta o IP", "Informe o IP ou use 'Procurar na rede'.")
                return None
            return {"ip": ip}
        imp = self.imp_nome_m.get().strip()
        if not imp:
            messagebox.showwarning("Impressora", "No USB escolha a impressora do Windows (clique em Atualizar).")
            return None
        return {"impressora_windows": imp}

    def rodar_manut(self, chave):
        r = manutencao.ROTINAS[chave]
        dest = self._destino_manut()
        if not dest:
            return
        if chave in ("cl2", "cl3") and not messagebox.askyesno(
                r["nome"], r["aviso"] + "\n\nContinuar?"):
            return
        self.executar(r["nome"], lambda: manutencao.executar(chave, **dest),
                      lambda via: self.escreve(f"✔ {r['nome']} enviado por {via}. "
                                               "Aguarde a impressora parar antes de outro comando."))

    def ler_firmware(self):
        p = self._parametros(precisa_modelo=False)
        if not p:
            return
        con, ip, modelo = p

        def fim(r):
            self.lb_fw.configure(text=f"Firmware: {r.get('firmware') or 'não informado'}")
            self.escreve(f"Firmware: {r.get('firmware') or '?'}")
            if r.get("cabecote"):
                self.escreve(f"ID do cabeçote (parcial): {r['cabecote']}")
            for k, v in (r.get("contadores") or {}).items():
                self.escreve(f"  {k}: {v}")
            if not r.get("contadores"):
                self.escreve("  Contadores: modelo fora do banco ou EEPROM bloqueada.")
        self.executar("Lendo firmware",
                      lambda: self._com_impressora(manutencao.ler_firmware_e_contadores, modelo, con, ip),
                      fim)

    def abrir_firmware(self):
        m = self.modelo.get().strip()
        if not m:
            messagebox.showwarning("Modelo", "Escolha ou detecte o modelo primeiro.")
            return
        if not messagebox.askokcancel("Firmware", manutencao.AVISO_FIRMWARE):
            return
        url = manutencao.abrir_suporte(m)
        self.escreve(f"Abrindo suporte Epson: {url}  (aba Downloads > Firmware)")

    def abrir_painel(self):
        ip = self.ip.get().strip()
        if not ip:
            messagebox.showwarning("Falta o IP", "Informe o IP da impressora.")
            return
        if not messagebox.askokcancel("Firmware", manutencao.AVISO_FIRMWARE):
            return
        self.escreve(f"Painel web: {manutencao.abrir_painel_web(ip)}  "
                     "(Configurações > Atualização de firmware, se o modelo tiver)")

    def _aba_diag(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="  Diagnóstico  ")
        esq = ttk.Frame(f)
        esq.pack(side="left", fill="both", expand=True)
        topo = ttk.Frame(esq)
        topo.pack(fill="x", pady=(0, 8))
        b = ttk.Button(topo, text="🔍  Diagnosticar impressora", style="Accent.TButton",
                       command=self.diagnosticar)
        b.pack(side="left", ipady=4)
        self.botoes.append(b)
        ttk.Button(topo, text="Histórico desta impressora",
                   command=self.ver_historico).pack(side="left", padx=8)
        self.lb_diag = ttk.Label(esq, text="Conecte, escolha o modelo e clique em Diagnosticar.",
                                 foreground=COR["cinza"])
        self.lb_diag.pack(anchor="w", pady=(0, 6))
        self.tv_diag = ttk.Treeview(esq, columns=("g",), show="tree", selectmode="browse")
        self.tv_diag.column("#0", width=420)
        self.tv_diag.column("g", width=0, stretch=False)
        for g in ("erro", "aviso", "ok"):
            self.tv_diag.tag_configure(g, foreground=COR[g])
        self.tv_diag.pack(fill="both", expand=True)
        self.tv_diag.bind("<<TreeviewSelect>>", self._sel_diag)
        ttk.Separator(f, orient="vertical").pack(side="left", fill="y", padx=8)
        self.det_diag = PainelDetalhe(f, self)
        self.det_diag.pack(side="left", fill="both", expand=True)

    def _aba_tabela(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="  Tabela de erros Epson  ")
        esq = ttk.Frame(f)
        esq.pack(side="left", fill="both", expand=True)
        busca = ttk.Frame(esq)
        busca.pack(fill="x", pady=(0, 8))
        ttk.Label(busca, text="Buscar:").pack(side="left")
        self.busca = tk.StringVar()
        e = ttk.Entry(busca, textvariable=self.busca)
        e.pack(side="left", fill="x", expand=True, padx=6)
        e.bind("<KeyRelease>", lambda _e: self._preenche_tabela())
        self.tv_tab = ttk.Treeview(esq, show="tree", selectmode="browse")
        self.tv_tab.pack(fill="both", expand=True)
        self.tv_tab.tag_configure("grupo", font=("Segoe UI", 10, "bold"))
        self.tv_tab.tag_configure("naooficial", foreground=COR["aviso"])
        self.tv_tab.bind("<<TreeviewSelect>>", self._sel_tab)
        ttk.Label(esq, foreground=COR["cinza"], font=("Segoe UI", 8), wraplength=420,
                  text="Códigos de tela e luzes: manuais Epson (resumidos). "
                       "Códigos internos em laranja: fontes não oficiais.").pack(anchor="w", pady=4)
        ttk.Separator(f, orient="vertical").pack(side="left", fill="y", padx=8)
        self.det_tab = PainelDetalhe(f, self)
        self.det_tab.pack(side="left", fill="both", expand=True)
        self._preenche_tabela()

    def _aba_teste(self):
        f = ttk.Frame(self.nb, padding=12)
        self.nb.add(f, text="  Teste de impressão  ")
        esq = ttk.Frame(f)
        esq.pack(side="left", fill="y")
        imp = ttk.LabelFrame(esq, text=" Impressora do Windows ", padding=10)
        imp.pack(fill="x")
        self.imp_nome = tk.StringVar()
        self.cb_imp = ttk.Combobox(imp, textvariable=self.imp_nome, width=34, state="readonly")
        self.cb_imp.bind("<<ComboboxSelected>>", lambda _e: self._lembrar_impressora(self.imp_nome.get()))
        self.cb_imp.grid(row=0, column=0, sticky="w")
        ttk.Button(imp, text="Atualizar", command=self.carregar_impressoras).grid(row=0, column=1, padx=6)
        ttk.Label(imp, text="A impressora precisa estar instalada com o driver no Windows.",
                  foreground=COR["cinza"], font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=2,
                                                                    sticky="w", pady=(4, 0))

        pg = ttk.LabelFrame(esq, text=" Página de teste ", padding=10)
        pg.pack(fill="x", pady=10)
        self.pagina = tk.StringVar(value=impressao.PAGINAS[0]["id"])
        self._minis = []
        for i, p in enumerate(impressao.PAGINAS):
            fr = ttk.Frame(pg)
            fr.grid(row=0, column=i, padx=6, sticky="n")
            mini = _imagem_arquivo(impressao.caminho_pagina(p, mini=True), 150)
            self._minis.append(mini)
            lb = tk.Label(fr, image=mini, bd=1, relief="solid", cursor="hand2") if mini else ttk.Label(fr, text="(sem prévia)")
            lb.pack()
            lb.bind("<Button-1>", lambda _e, pid=p["id"]: self._sel_pagina(pid))
            ttk.Radiobutton(fr, text=p["nome"], value=p["id"], variable=self.pagina,
                            command=lambda pid=p["id"]: self._sel_pagina(pid)).pack(pady=(6, 0))

        ac = ttk.Frame(esq)
        ac.pack(fill="x")
        ttk.Label(ac, text="Cópias:").pack(side="left")
        self.copias = tk.IntVar(value=1)
        ttk.Spinbox(ac, from_=1, to=10, width=4, textvariable=self.copias).pack(side="left", padx=6)
        b = ttk.Button(ac, text="🖨  Imprimir teste", style="Accent.TButton", command=self.imprimir_teste)
        b.pack(side="left", padx=8, ipady=4)
        self.botoes.append(b)
        self.com_loja = tk.BooleanVar(value=True)
        ttk.Checkbutton(esq, text="Incluir logo da loja, data e impressora no rodapé",
                        variable=self.com_loja).pack(anchor="w", pady=(10, 0))
        outros = ttk.Frame(esq)
        outros.pack(fill="x", pady=(10, 0))
        b3 = ttk.Button(outros, text="Página de teste do Windows", command=self.imprimir_windows)
        b3.pack(side="left")
        self.botoes.append(b3)
        b2 = ttk.Button(outros, text="Imprimir imagem minha...", command=self.imprimir_propria)
        b2.pack(side="left", padx=8)
        self.botoes.append(b2)
        ttk.Label(esq, foreground=COR["cinza"], wraplength=360, justify="left",
                  text="Dica: o teste de bicos da própria Epson também pode ser impresso pelo "
                       "driver (Manutenção > Verificação dos jatos) ou pelo painel da impressora."
                  ).pack(anchor="w", pady=(14, 0))

        ttk.Separator(f, orient="vertical").pack(side="left", fill="y", padx=12)
        dir_ = ttk.Frame(f)
        dir_.pack(side="left", fill="both", expand=True)
        ttk.Label(dir_, text="Como avaliar a folha impressa", style="Titulo.TLabel").pack(anchor="w")
        sb = ttk.Scrollbar(dir_)
        sb.pack(side="right", fill="y", pady=(6, 0))
        self.txt_avaliar = tk.Text(dir_, wrap="word", relief="flat", borderwidth=0,
                                   font=("Segoe UI", 10), padx=6, pady=6, yscrollcommand=sb.set)
        sb.configure(command=self.txt_avaliar.yview)
        self.txt_avaliar.tag_configure("cab", font=("Segoe UI", 10, "bold"))
        self.txt_avaliar.pack(fill="both", expand=True, pady=(6, 0))
        self._sel_pagina(self.pagina.get())
        self._impressoras_carregadas = False
        self.nb.bind("<<NotebookTabChanged>>", self._ao_trocar_aba)

    def _ao_trocar_aba(self, _e):
        aba = self.nb.tab(self.nb.select(), "text")
        if ("Teste" in aba or "Manuten" in aba) and not self._impressoras_carregadas:
            self.carregar_impressoras()

    def _sel_pagina(self, pid):
        self.pagina.set(pid)
        p = next(x for x in impressao.PAGINAS if x["id"] == pid)
        t = self.txt_avaliar
        t.configure(state="normal")
        t.delete("1.0", "end")
        for cab, txt in p["como_avaliar"]:
            t.insert("end", cab + "\n", "cab")
            t.insert("end", txt + "\n\n")
        t.configure(state="disabled")

    def _lembrar_impressora(self, nome):
        nome = (nome or "").strip()
        if not nome:
            return
        self.imp_nome.set(nome)
        self.imp_nome_m.set(nome)
        core.salvar_ajuste("impressora_windows", nome)
        if nome in impressao.DESCONECTADAS:
            self.escreve(f"Atenção: o Windows diz que '{nome}' está desconectada/offline.")

    def carregar_impressoras(self):
        self._impressoras_carregadas = True

        def fim(r):
            lista, padrao = r
            self.cb_imp["values"] = lista
            self.cb_imp_m["values"] = lista
            esc = impressao.escolher_impressora(
                lista, padrao, self.modelo.get().strip(),
                atual=self.imp_nome.get().strip(), lembrada=core.ler_ajuste("impressora_windows"))
            if esc:
                self.imp_nome.set(esc)
                self.imp_nome_m.set(esc)
            off = len([n for n in lista if n in impressao.DESCONECTADAS])
            self.escreve(f"{len(lista)} impressora(s) instalada(s) no Windows"
                         + (f" ({off} desconectada(s), listadas no fim)." if off else ".")
                         + (f" Usando: {esc}" if esc else ""))
        self.executar("Listando impressoras", impressao.listar_impressoras, fim)

    def imprimir_teste(self):
        p = next(x for x in impressao.PAGINAS if x["id"] == self.pagina.get())
        self._imprimir(impressao.caminho_pagina(p), p["nome"], com_loja=self.com_loja.get())

    def imprimir_windows(self):
        impn = self.imp_nome.get().strip()
        if not impn:
            messagebox.showwarning("Impressora", "Escolha a impressora (clique em Atualizar).")
            return
        self.executar("Página de teste do Windows",
                      lambda: impressao.pagina_teste_windows(impn),
                      lambda _r: self.escreve(f"✔ Página de teste do Windows enviada para {impn}."))

    def imprimir_propria(self):
        arq = filedialog.askopenfilename(title="Escolha a imagem",
                                         filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if arq:
            self._imprimir(arq, os.path.basename(arq))

    def _imprimir(self, caminho, nome, com_loja=False):
        impn = self.imp_nome.get().strip()
        if not impn:
            messagebox.showwarning("Impressora", "Escolha a impressora (clique em Atualizar).")
            return
        try:
            n = max(1, min(10, int(self.copias.get())))
        except (tk.TclError, ValueError):
            n = 1

        def fim(_r):
            self.escreve(f"✔ '{nome}' enviado para {impn} ({n} cópia(s)).")
            self.status.set("Teste enviado para a impressora.")
        modelo = self.modelo.get().strip()

        def tarefa():
            arq = impressao.preparar_pagina(caminho, impn, modelo, com_loja)
            impressao.imprimir_imagem(arq, impn, n)
        self.executar(f"Imprimindo '{nome}'", tarefa, fim)

    # ------------------------------------------------------------ teste de Wi-Fi
    def _aba_wifi(self):
        f = ttk.Frame(self.nb, padding=12)
        self.nb.add(f, text="  Teste de Wi-Fi  ")
        self.wf = {"passo": 0, "auto": None}
        self.wf_resp = {p["id"]: tk.StringVar() for p in teste_wifi.PASSOS}
        self.wf_extra = {p["id"]: tk.StringVar() for p in teste_wifi.PASSOS}
        self.wf_dados = {k: tk.StringVar() for k in ("os", "cliente", "queixa", "tecnico", "servico")}
        self.wf_dados["queixa"].set("Não conecta ao Wi-Fi")
        self.wf_titulos = ["Dados do atendimento"] + [p["titulo"] for p in teste_wifi.PASSOS] + [
            "4. Verificação pelo programa", "5. Laudo e relatório"]

        esq = ttk.Frame(f)
        esq.pack(side="left", fill="y")
        ttk.Label(esq, text="Passo a passo", style="Titulo.TLabel").pack(anchor="w", pady=(0, 8))
        self.wf_lbs = []
        for t in self.wf_titulos:
            lb = ttk.Label(esq, text="○  " + t, wraplength=230, foreground=COR["cinza"])
            lb.pack(anchor="w", pady=4)
            self.wf_lbs.append(lb)
        ttk.Separator(f, orient="vertical").pack(side="left", fill="y", padx=14)

        dir_ = ttk.Frame(f)
        dir_.pack(side="left", fill="both", expand=True)
        self.wf_corpo = ttk.Frame(dir_)
        self.wf_corpo.pack(fill="both", expand=True)
        nav = ttk.Frame(dir_)
        nav.pack(fill="x", pady=(10, 0))
        self.wf_volta = ttk.Button(nav, text="← Voltar", command=lambda: self._wf_ir(-1))
        self.wf_volta.pack(side="left")
        self.wf_prox = ttk.Button(nav, text="Próximo →", style="Accent.TButton", command=lambda: self._wf_ir(1))
        self.wf_prox.pack(side="right")
        ttk.Button(nav, text="Recomeçar", command=self._wf_novo).pack(side="right", padx=8)
        self._wf_mostra()

    def _wf_novo(self):
        for v in list(self.wf_resp.values()) + list(self.wf_extra.values()):
            v.set("")
        for k in ("os", "cliente", "tecnico", "servico"):
            self.wf_dados[k].set("")
        self.wf_dados["queixa"].set("Não conecta ao Wi-Fi")
        self.wf.update(passo=0, auto=None)
        self._wf_mostra()

    def _wf_ir(self, d):
        self.wf["passo"] = max(0, min(len(self.wf_titulos) - 1, self.wf["passo"] + d))
        self._wf_mostra()

    def _wf_mostra(self):
        i = self.wf["passo"]
        for n, lb in enumerate(self.wf_lbs):
            marca = "●" if n == i else ("✔" if n < i else "○")
            lb.configure(text=f"{marca}  {self.wf_titulos[n]}",
                         foreground=COR["acento"] if n == i else (COR["ok"] if n < i else COR["cinza"]))
        for w in self.wf_corpo.winfo_children():
            w.destroy()
        c = self.wf_corpo
        ttk.Label(c, text=self.wf_titulos[i], style="Titulo.TLabel").pack(anchor="w", pady=(0, 8))
        self.wf_volta.state(["disabled"] if i == 0 else ["!disabled"])
        self.wf_prox.state(["disabled"] if i == len(self.wf_titulos) - 1 else ["!disabled"])

        if i == 0:
            ttk.Label(c, wraplength=620, justify="left", foreground=COR["cinza"],
                      text="Opcional: estes dados saem no relatório. O modelo vem do campo Modelo lá em cima.").pack(anchor="w")
            g = ttk.Frame(c)
            g.pack(anchor="w", pady=10)
            for r, (k, t) in enumerate((("os", "Nº da OS"), ("cliente", "Cliente"),
                                         ("queixa", "Queixa do cliente"), ("tecnico", "Técnico"),
                                         ("servico", "Serviço realizado / peça trocada"))):
                ttk.Label(g, text=t).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
                ttk.Entry(g, textvariable=self.wf_dados[k], width=44).grid(row=r, column=1, sticky="w")
            ttk.Label(c, wraplength=620, justify="left", foreground=COR["cinza"], text=(
                "Trocou alguma peça (ex.: \"Troca da placa Wi-Fi\")? Preencha o serviço: o laudo sai como "
                "\"aprovado após reparo\". Os testes dos próximos passos são os feitos DEPOIS do reparo."
            )).pack(anchor="w", pady=(4, 0))
        elif 1 <= i <= len(teste_wifi.PASSOS):
            p = teste_wifi.PASSOS[i - 1]
            ttk.Label(c, text=p["instrucao"], wraplength=640, justify="left").pack(anchor="w")
            ttk.Label(c, text="Resultado:", style="Titulo.TLabel").pack(anchor="w", pady=(14, 4))
            for val, txt in p["opcoes"]:
                ttk.Radiobutton(c, text=txt, value=val, variable=self.wf_resp[p["id"]]).pack(anchor="w", pady=2)
            if p.get("campo"):
                ttk.Label(c, text=p["campo"]).pack(anchor="w", pady=(12, 2))
                ttk.Entry(c, textvariable=self.wf_extra[p["id"]], width=40).pack(anchor="w")
        elif i == len(teste_wifi.PASSOS) + 1:
            ttk.Label(c, wraplength=640, justify="left", text=(
                "Com a impressora no Wi-Fi da loja e o PC na mesma rede, informe o IP da folha "
                "(ou use Procurar na rede lá em cima) e clique em Verificar. O programa confere se ela "
                "responde, lê modelo, nº de série e firmware, e pode imprimir o teste de bicos pelo Wi-Fi.")).pack(anchor="w")
            g = ttk.Frame(c)
            g.pack(anchor="w", pady=10)
            ttk.Label(g, text="IP:").pack(side="left")
            ttk.Entry(g, textvariable=self.ip, width=18).pack(side="left", padx=6)
            b1 = ttk.Button(g, text="Procurar na rede", command=self.procurar)
            b1.pack(side="left")
            b2 = ttk.Button(g, text="Verificar", style="Accent.TButton", command=self._wf_verificar)
            b2.pack(side="left", padx=6)
            b3 = ttk.Button(g, text="Imprimir teste de bicos pelo Wi-Fi", command=self._wf_bicos)
            b3.pack(side="left")
            self.wf_res = ttk.Label(c, text=self._wf_texto_auto(), wraplength=640, justify="left")
            self.wf_res.pack(anchor="w", pady=8)
        else:
            sit, laudo, rec = teste_wifi.concluir({k: v.get() or None for k, v in self.wf_resp.items()},
                                                  self.wf["auto"], self.wf_dados["servico"].get())
            rot, cor = teste_wifi.SITUACAO[sit]
            ttk.Label(c, text=rot, foreground=cor, font=("Segoe UI", 14, "bold")).pack(anchor="w")
            ttk.Label(c, text="Laudo (pode editar):").pack(anchor="w", pady=(10, 2))
            self.wf_laudo = tk.Text(c, height=6, wrap="word", font=("Segoe UI", 10))
            self.wf_laudo.insert("1.0", laudo)
            self.wf_laudo.pack(fill="x")
            if rec:
                ttk.Label(c, text="Recomendações:").pack(anchor="w", pady=(10, 2))
                ttk.Label(c, text="\n".join("• " + r for r in rec), wraplength=640, justify="left").pack(anchor="w")
            self.wf["concl"] = (sit, rec)
            g = ttk.Frame(c)
            g.pack(anchor="w", pady=12)
            ttk.Button(g, text="Gerar relatório", style="Accent.TButton", command=self._wf_relatorio).pack(side="left")
            ttk.Button(g, text="Copiar laudo", command=self._wf_copiar).pack(side="left", padx=8)

    def _wf_texto_auto(self):
        a = self.wf["auto"]
        if not a:
            return "Ainda não verificado."
        if not a.get("respondeu"):
            return f"✖ A impressora não respondeu no IP {a['ip']}. Confira se o PC está na mesma rede."
        partes = [f"✔ Respondeu no IP {a['ip']}"]
        for k, t in (("modelo", "Modelo"), ("serie", "Nº de série"), ("firmware", "Firmware")):
            if a.get(k):
                partes.append(f"{t}: {a[k]}")
        partes.append("Porta de impressão (9100): " + ("aberta" if a.get("porta_9100") else "fechada"))
        if a.get("teste_bicos"):
            partes.append(f"✔ Teste de bicos enviado pelo Wi-Fi ({a['teste_bicos']})")
        return "\n".join(partes)

    def _wf_verificar(self):
        ip = self.ip.get().strip()
        if not ip:
            messagebox.showwarning("Falta o IP", "Informe o IP da folha de status ou use Procurar na rede.")
            return

        def fim(r):
            antigo = self.wf.get("auto") or {}
            if antigo.get("teste_bicos") and antigo.get("ip") == ip:
                r["teste_bicos"] = antigo["teste_bicos"]
            self.wf["auto"] = r
            if r.get("modelo") and not self.modelo.get().strip():
                self.modelo.set(r["modelo"])
                self._atualiza_suporte()
            self.wf_res.configure(text=self._wf_texto_auto())
            self.escreve(self._wf_texto_auto())
        self.executar("Verificando a impressora pela rede", lambda: teste_wifi.verificar_rede(ip), fim)

    def _wf_bicos(self):
        ip = self.ip.get().strip()
        if not ip:
            messagebox.showwarning("Falta o IP", "Informe o IP primeiro.")
            return

        def fim(via):
            self.wf["auto"] = self.wf["auto"] or {"ip": ip, "respondeu": True}
            self.wf["auto"]["teste_bicos"] = via
            self.wf["auto"]["respondeu"] = True
            self.wf_res.configure(text=self._wf_texto_auto())
            self.escreve(f"✔ Teste de bicos enviado por {via}.")
        self.executar("Imprimindo teste de bicos pelo Wi-Fi", lambda: manutencao.executar("bicos", ip=ip), fim)

    def _wf_laudo_atual(self):
        try:
            return self.wf_laudo.get("1.0", "end").strip()
        except tk.TclError:
            return ""

    def _wf_copiar(self):
        self.clipboard_clear()
        self.clipboard_append(self._wf_laudo_atual())
        self.status.set("Laudo copiado. Cole na OS.")

    def _wf_relatorio(self):
        sit, rec = self.wf.get("concl", ("incompleto", []))
        dados = {k: v.get().strip() for k, v in self.wf_dados.items()}
        dados.update(
            modelo=self.modelo.get().strip(), situacao=sit, laudo=self._wf_laudo_atual(), recomendacoes=rec,
            respostas={k: v.get() or None for k, v in self.wf_resp.items()},
            extras={k: v.get().strip() for k, v in self.wf_extra.items() if v.get().strip()},
            auto=self.wf["auto"])
        try:
            caminho = teste_wifi.gerar_relatorio(dados)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Relatório", f"Não consegui gerar o relatório: {exc}")
            return
        self.escreve(f"✔ Relatório salvo: {caminho}")
        teste_wifi.abrir(caminho)

    def _aba_log(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="  Registro  ")
        self.txt_log = tk.Text(f, wrap="word", state="disabled", font=("Consolas", 10),
                               relief="flat", padx=8, pady=6)
        sb = ttk.Scrollbar(f, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=sb.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _rodape(self):
        barra = ttk.Frame(self, padding=(14, 0, 14, 8))
        barra.pack(fill="x")
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(barra, textvariable=self.status).pack(side="left")
        self.prog = ttk.Progressbar(barra, mode="indeterminate", length=140)
        self.prog.pack(side="right")

    # ------------------------------------------------------------ util
    def escreve(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _processa_fila(self):
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == "log":
                    self.escreve(dado)
                elif tipo == "status":
                    self.status.set(dado)
                elif tipo == "fim":
                    dado()
        except queue.Empty:
            pass
        self.after(100, self._processa_fila)

    def _parametros(self, precisa_modelo=True):
        con = self.conexao.get()
        ip = self.ip.get().strip()
        modelo = self.modelo.get().strip() or None
        if con == core.WIFI and not ip:
            messagebox.showwarning("Falta o IP", "Informe o IP ou use 'Procurar na rede'.")
            return None
        if precisa_modelo and not modelo:
            messagebox.showwarning("Falta o modelo", "Escolha o modelo ou clique em 'Detectar'.")
            return None
        return con, ip, modelo

    def executar(self, titulo, tarefa, ao_terminar=None):
        if self.ocupado:
            return
        self.ocupado = True
        for b in self.botoes:
            b.state(["disabled"])
        self.prog.start(12)
        self.status.set(titulo + "...")
        self.escreve(f"\n▶ {titulo}")

        def roda():
            try:
                res, erro = tarefa(), None
            except Exception as exc:  # noqa: BLE001
                res, erro = None, exc

            def fim():
                self.ocupado = False
                for b in self.botoes:
                    b.state(["!disabled"])
                self.prog.stop()
                if erro:
                    self.status.set("Erro.")
                    self.escreve(f"✖ {erro}")
                    messagebox.showerror("Erro", str(erro))
                else:
                    self.status.set("Concluído.")
                    if ao_terminar:
                        ao_terminar(res)
            self.fila.put(("fim", fim))
        threading.Thread(target=roda, daemon=True).start()

    def _com_impressora(self, func, modelo, con, ip):
        imp = core.criar_impressora(modelo, con, ip)
        try:
            return func(imp)
        finally:
            core.fechar(imp)

    # ------------------------------------------------------------ conexão
    def procurar(self):
        def fim(lista):
            if not lista:
                self.escreve("Nenhuma Epson encontrada. Confira se o PC está na mesma rede/Wi-Fi Direct.")
                messagebox.showinfo("Procurar", "Nenhuma impressora Epson encontrada na rede.")
                return
            for p in lista:
                self.escreve(f"  • {p['ip']}  {p['nome']}")
            p = lista[0]
            self.ip.set(p["ip"])
            if p.get("modelo"):
                self.modelo.set(p["modelo"])
                self._atualiza_suporte()
            self.status.set(f"Encontrada: {p['nome']} ({p['ip']})")
        self.executar("Procurando impressoras",
                      lambda: core.procurar_na_rede(lambda m: self.fila.put(("status", m))), fim)

    def detectar(self):
        par = self._parametros(precisa_modelo=False)
        if not par:
            return
        con, ip, _ = par

        def fim(modelo):
            if not modelo:
                self.escreve("A impressora não informou o modelo. Escolha na lista.")
                return
            self.modelo.set(modelo)
            self._atualiza_suporte()
            self.escreve(f"Modelo detectado: {modelo}")
        self.executar("Detectando modelo", lambda: core.detectar_modelo(con, ip), fim)

    # ------------------------------------------------------------ reset
    def _mostra_barras(self, alm):
        for w in self.fr_barras.winfo_children():
            w.destroy()
        if not alm:
            return
        for i, (k, v) in enumerate(alm.items()):
            cor = "erro" if v >= 100 else "aviso" if v >= 80 else "ok"
            ttk.Label(self.fr_barras, text=core.NOMES_ALMOFADA.get(k, k), width=22
                      ).grid(row=i, column=0, sticky="w", pady=3)
            pb = ttk.Progressbar(self.fr_barras, length=420, maximum=100, value=min(v, 100))
            pb.grid(row=i, column=1, sticky="we", padx=8)
            ttk.Label(self.fr_barras, text=f"{v:.1f}%" + ("  CHEIA" if v >= 100 else ""),
                      foreground=COR[cor], font=("Segoe UI", 10, "bold")).grid(row=i, column=2, sticky="w")
        self.fr_barras.columnconfigure(1, weight=1)

    def ler(self):
        par = self._parametros()
        if not par:
            return
        con, ip, modelo = par

        def fim(info):
            self.lb_info.configure(
                text=f"{info.get('modelo')}   •   Série: {info.get('serie') or '?'}   •   "
                     f"Firmware: {info.get('firmware') or '?'}")
            alm = info.get("almofadas")
            self._mostra_barras(alm)
            if alm:
                for k, v in alm.items():
                    self.escreve(f"  {core.NOMES_ALMOFADA.get(k, k)}: {v:.2f}%")
            elif core.modelo_suportado(modelo):
                msg = ("Não consegui ler os contadores na EEPROM. Provável firmware com "
                       "bloqueio pela rede: use o reset temporário ou o cabo USB.")
                self.escreve("⚠ " + msg)
                ttk.Label(self.fr_barras, text="⚠ " + msg, foreground=COR["aviso"],
                          wraplength=820).grid(row=0, column=0, sticky="w")
            else:
                ttk.Label(self.fr_barras, text="Modelo fora do banco: contadores não podem ser lidos.",
                          foreground=COR["cinza"]).grid(row=0, column=0, sticky="w")
        self.executar("Lendo contadores",
                      lambda: self._com_impressora(core.ler_informacoes, modelo, con, ip), fim)

    def reset_perm(self):
        par = self._parametros()
        if not par:
            return
        con, ip, modelo = par
        if not core.modelo_suportado(modelo):
            messagebox.showinfo("Modelo fora do banco",
                                f"A {modelo} ainda não tem os endereços do contador cadastrados.\n"
                                "Use o reset temporário ou cadastre em modelos_extra.json.")
            return
        if not messagebox.askyesno("Reset permanente", AVISO_ALMOFADA, icon="warning"):
            return

        def fim(r):
            self.escreve(f"Backup salvo em: {r['backup']}")
            self.escreve(f"Células gravadas: {r['celulas_gravadas']} (alteradas: {r['celulas_alteradas']})")
            if r["ok"]:
                self._mostra_barras(r.get("depois"))
                self.escreve("✔ Reset permanente concluído. DESLIGUE e LIGUE a impressora.")
                messagebox.showinfo("Pronto", "Reset concluído.\nDesligue e ligue a impressora.")
            else:
                self.escreve("✖ A impressora recusou a gravação (firmware bloqueado?). "
                             "Tente o cabo USB ou o reset temporário.")
                messagebox.showwarning("Não gravou", "A impressora recusou a gravação.\nVeja a aba Registro.")
        self.executar("Reset permanente",
                      lambda: self._com_impressora(lambda imp: core.reset_permanente(imp, con, ip),
                                                   modelo, con, ip), fim)

    def reset_temp(self):
        par = self._parametros(precisa_modelo=False)
        if not par:
            return
        con, ip, modelo = par
        if not messagebox.askyesno("Reset temporário",
                                   "Libera a impressão até a impressora ser desligada.\n"
                                   "Funciona até nos modelos com bloqueio pela rede.\n\nContinuar?"):
            return

        def fim(ok):
            if ok:
                self.escreve("✔ Liberada até desligar. Ao religar, a trava volta.")
                messagebox.showinfo("Pronto", "Impressora liberada até ser desligada.")
            else:
                self.escreve("✖ A impressora não aceitou (algumas só aceitam com a almofada já cheia).")
        self.executar("Reset temporário",
                      lambda: self._com_impressora(core.reset_temporario, modelo, con, ip), fim)

    def restaurar(self):
        par = self._parametros()
        if not par:
            return
        con, ip, modelo = par
        arq = filedialog.askopenfilename(title="Escolha o backup", initialdir=core.pasta_backups(),
                                         filetypes=[("Backup", "*.json")])
        if not arq or not messagebox.askyesno("Restaurar",
                                              f"Gravar de volta os valores de\n{os.path.basename(arq)}?"):
            return
        self.executar("Restaurando backup",
                      lambda: self._com_impressora(lambda imp: core.restaurar_backup(imp, arq),
                                                   modelo, con, ip),
                      lambda rel: self.escreve(f"✔ Backup restaurado ({len(rel)} células). Desligue e ligue."))

    def abrir_backups(self):
        self._abrir(core.pasta_backups())

    @staticmethod
    def _abrir(p):
        if sys.platform == "win32":
            os.startfile(p)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", p])

    def chave(self):
        par = self._parametros()
        if not par:
            return
        con, ip, modelo = par
        if not messagebox.askyesno("Descobrir chave",
                                   "Testa as chaves de leitura (até 65.536 tentativas, vários minutos). "
                                   "Só lê, não grava.\n\nEscolha antes um modelo PARECIDO que esteja "
                                   "no banco.\nContinuar?"):
            return

        if not core.modelo_suportado(modelo):
            messagebox.showwarning(
                "Descobrir chave",
                f"A busca de chave precisa partir de um modelo do banco.\n\nEscolha no campo Modelo um "
                f"modelo PARECIDO com a {modelo} (mesma linha/ano) e tente de novo.")
            return

        def fim(k):
            msg = (f"✔ Chave de leitura encontrada: {list(k)}" if k else
                   "✖ Nenhuma chave encontrada. O firmware pode estar bloqueando a leitura da memória.")
            self.escreve(msg)
            messagebox.showinfo("Descobrir chave", msg)
        self.executar("Procurando chave",
                      lambda: self._com_impressora(
                          lambda imp: core.descobrir_chave(imp, lambda m: self.fila.put(("status", m))),
                          modelo, con, ip), fim)

    # ------------------------------------------------------------ diagnóstico
    def diagnosticar(self):
        par = self._parametros(precisa_modelo=False)
        if not par:
            return
        con, ip, modelo = par

        def fim(r):
            self.ultimo_diag = r
            self.tv_diag.delete(*self.tv_diag.get_children())
            icone = {"erro": "●", "aviso": "▲", "ok": "✔"}
            for i, a in enumerate(r["achados"]):
                extra = "  ★" if a.get("da_assistencia") else ""
                self.tv_diag.insert("", "end", iid=str(i), tags=(a["gravidade"],),
                                    text=f"  {icone.get(a['gravidade'], '•')}  {a['titulo']}{extra}")
            erros = sum(a["gravidade"] == "erro" for a in r["achados"])
            self.lb_diag.configure(
                text=f"{r.get('modelo') or 'Modelo ?'}  •  Série {r.get('serie') or '?'}  •  "
                     f"Status: {r.get('status') or '?'}  •  {erros} erro(s)",
                foreground=COR["erro"] if erros else COR["ok"])
            if r["achados"]:
                self.tv_diag.selection_set("0")
            self.escreve(f"Diagnóstico: {len(r['achados'])} item(ns).")
        self.executar("Diagnosticando",
                      lambda: self._com_impressora(dg.diagnosticar, modelo, con, ip), fim)

    def _item_diag(self, a):
        return {"chave": a["chave"], "titulo": a["titulo"],
                "sub": {"erro": "Erro", "aviso": "Aviso", "ok": "OK"}.get(a["gravidade"], "")
                       + (f"  •  {a['detalhe']}" if a.get("detalhe") else ""),
                "linhas": [("Causa", a.get("causa", "")),
                           ("O que fazer", a.get("solucao", "")),
                           ("★ Registrado pela assistência" if a.get("da_assistencia") else "", "")],
                "fotos": a.get("fotos", [])}

    def _sel_diag(self, _e):
        sel = self.tv_diag.selection()
        if sel and self.ultimo_diag:
            self.det_diag.mostrar(self._item_diag(self.ultimo_diag["achados"][int(sel[0])]))

    def ver_historico(self):
        serie = (self.ultimo_diag or {}).get("serie")
        texto = dg.historico(serie) if serie else ""
        if not texto:
            messagebox.showinfo("Histórico", "Sem histórico. Faça um diagnóstico primeiro.")
            return
        win = tk.Toplevel(self)
        win.title(f"Histórico - série {serie}")
        t = tk.Text(win, width=70, height=24, font=("Consolas", 10), padx=8, pady=6)
        t.insert("1.0", texto)
        t.configure(state="disabled")
        t.pack(fill="both", expand=True)

    # ------------------------------------------------------------ tabela
    def _preenche_tabela(self):
        self.tv_tab.delete(*self.tv_tab.get_children())
        self._tab_itens = {}
        grupos = {}
        for i, e in enumerate(erros_epson.buscar(self.busca.get())):
            g = e["grupo"]
            if g not in grupos:
                grupos[g] = self.tv_tab.insert("", "end", text=g, open=True, tags=("grupo",))
            tag = ("naooficial",) if e["origem"] == erros_epson.NAO_OFICIAL else ()
            iid = self.tv_tab.insert(grupos[g], "end", text=f"{e['codigo']}  —  {e['titulo']}", tags=tag)
            self._tab_itens[iid] = e

    def _item_tab(self, e):
        chave = erros_epson.chave(e)
        nota = dg.carregar_banco().get(chave, {})
        return {"chave": chave, "titulo": f"{e['codigo']} — {e['titulo']}",
                "sub": f"{e['grupo']}  •  Fonte: {e['origem']}",
                "linhas": [("★ Causa encontrada (assistência)", nota.get("causa", ""), "nota"),
                           ("★ O que resolveu (assistência)", nota.get("solucao", ""), "nota"),
                           ("O que é", e["o_que_e"]),
                           ("O que fazer", e["o_que_fazer"])],
                "fotos": [dg.caminho_foto(n) for n in nota.get("fotos", [])]}

    def _sel_tab(self, _e):
        sel = self.tv_tab.selection()
        if sel and sel[0] in self._tab_itens:
            self.det_tab.mostrar(self._item_tab(self._tab_itens[sel[0]]))

    def recarregar_item(self, item):
        """Depois de editar/adicionar foto: redesenha o painel certo."""
        chave = item["chave"]
        if chave.startswith("tabela:"):
            self._sel_tab(None)
        elif self.ultimo_diag:
            dg._aplica_banco(self.ultimo_diag["achados"])
            self._sel_diag(None)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
