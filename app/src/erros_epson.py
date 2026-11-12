"""
Tabela de erros Epson, resumida em português.

Fontes oficiais (manuais Epson das linhas EcoTank L3150/ET-2710, L4260/ET-2850,
L3260, L3560, XP e WF): códigos da tela (E-/W-/I-) e padrões de luzes dos
modelos sem tela. O texto foi resumido e reescrito para a bancada.

Os códigos internos (000031, 031006...) NÃO são publicados pela Epson; os poucos
incluídos vêm de fontes de assistência técnica e estão marcados como
"não oficial".
"""

# Cada item: código/padrão -> dict(titulo, o_que_e, o_que_fazer, origem, grupo)
OFICIAL = "Epson (manual do usuário)"
NAO_OFICIAL = "Não oficial (fontes de assistência)"

ERROS = [
    # ---------------- Códigos na tela (modelos com visor: L4260, L3250 com tela, etc.)
    dict(codigo="E-01", grupo="Código na tela", titulo="Erro da impressora",
         o_que_e="Erro geral de hardware (geralmente carro travado, papel ou trava de transporte dentro).",
         o_que_fazer="Abrir o scanner, tirar papel/material de proteção, desligar e ligar. "
                     "Se continuar: ler o código interno com o programa e verificar carro, "
                     "encoder, correia e motor.",
         origem=OFICIAL),
    dict(codigo="E-02", grupo="Código na tela", titulo="Erro do scanner",
         o_que_e="Falha na unidade de digitalização.",
         o_que_fazer="Desligar e ligar. Se persistir: verificar cabo flat do scanner, "
                     "trava do scanner e motor do scanner.",
         origem=OFICIAL),
    dict(codigo="E-11", grupo="Código na tela", titulo="Almofada cheia (trocar)",
         o_que_e="Almofada principal chegou ao fim da vida útil. Impressão bloqueada; scanner funciona.",
         o_que_fazer="Trocar/lavar a almofada (ou coletor externo) e fazer o Reset PERMANENTE.",
         origem=OFICIAL),
    dict(codigo="E-12", grupo="Código na tela", titulo="Almofada sem margem cheia",
         o_que_e="Almofada da impressão sem margem chegou ao limite. Imprime só com margem.",
         o_que_fazer="Trocar/lavar a almofada sem margem e fazer o Reset PERMANENTE.",
         origem=OFICIAL),
    dict(codigo="W-01", grupo="Código na tela", titulo="Papel atolado",
         o_que_e="Atolamento de papel.",
         o_que_fazer="Tirar o papel, apertar o botão indicado na tela; se precisar, desligar e ligar. "
                     "Atolamento sem papel: sensor PE, roletes ou pedaço de papel escondido.",
         origem=OFICIAL),
    dict(codigo="W-11", grupo="Código na tela", titulo="Almofada quase cheia",
         o_que_e="Almofada principal perto do fim. Ainda dá para imprimir apertando OK.",
         o_que_fazer="Programar troca/limpeza da almofada e Reset PERMANENTE.",
         origem=OFICIAL),
    dict(codigo="W-12", grupo="Código na tela", titulo="Cartucho mal encaixado",
         o_que_e="Cartucho instalado errado (modelos com cartucho).",
         o_que_fazer="Pressionar cada cartucho até travar. Verificar contatos do chip.",
         origem=OFICIAL),
    dict(codigo="W-13", grupo="Código na tela", titulo="Cartucho não reconhecido",
         o_que_e="A impressora não reconhece o cartucho indicado.",
         o_que_fazer="Trocar o cartucho/chip. Limpar contatos.",
         origem=OFICIAL),
    dict(codigo="W-14", grupo="Código na tela", titulo="Almofada sem margem quase cheia",
         o_que_e="Almofada da impressão sem margem perto do fim.",
         o_que_fazer="Programar troca/limpeza e Reset PERMANENTE.",
         origem=OFICIAL),
    dict(codigo="I-22", grupo="Código na tela", titulo="Configurar Wi-Fi por WPS (botão)",
         o_que_e="Aguardando o botão WPS do roteador.", o_que_fazer="Apertar o WPS no roteador.",
         origem=OFICIAL),
    dict(codigo="I-23", grupo="Código na tela", titulo="Configurar Wi-Fi por WPS (PIN)",
         o_que_e="Aguardando o PIN no roteador.",
         o_que_fazer="Digitar no roteador o PIN da tela em até 2 minutos.", origem=OFICIAL),
    dict(codigo="I-31", grupo="Código na tela", titulo="Wi-Fi automático pelo computador",
         o_que_e="Aguardando configuração pelo instalador.",
         o_que_fazer="Rodar o instalador no PC e seguir as instruções.", origem=OFICIAL),
    dict(codigo="I-41", grupo="Código na tela", titulo="Exibição de papel desativada",
         o_que_e="Algumas funções (ex.: AirPrint) ficam indisponíveis.",
         o_que_fazer="Ativar a exibição automática de configuração de papel no menu.",
         origem=OFICIAL),
    dict(codigo="I-60", grupo="Código na tela", titulo="PC sem suporte a WSD",
         o_que_e="Digitalizar para o PC (WSD) não funciona nesse computador.",
         o_que_fazer="Usar o Epson Scan pelo USB/rede.", origem=OFICIAL),
    dict(codigo="Modo de recuperação", grupo="Código na tela",
         titulo="Falha na atualização de firmware",
         o_que_e="A impressora entrou em modo de recuperação.",
         o_que_fazer="Ligar pelo cabo USB (pela rede não funciona) e regravar o firmware.",
         origem=OFICIAL),

    # ---------------- Luzes (modelos sem tela: L3150, L3250, L3210, L1250...)
    dict(codigo="Luz Papel acesa", grupo="Luzes (sem tela)", titulo="Sem papel / puxou duas folhas",
         o_que_e="Falta papel ou entraram várias folhas.",
         o_que_fazer="Colocar papel e apertar o botão de cópia. Se tiver papel e não puxa: "
                     "rolete de alimentação e separador.", origem=OFICIAL),
    dict(codigo="Luz Papel piscando", grupo="Luzes (sem tela)", titulo="Papel atolado",
         o_que_e="Atolamento de papel.",
         o_que_fazer="Tirar o papel e apertar o botão de cópia. Sem papel visível: sensor PE.",
         origem=OFICIAL),
    dict(codigo="Luz Tinta acesa", grupo="Luzes (sem tela)", titulo="Carga inicial incompleta",
         o_que_e="A carga inicial de tinta pode não ter terminado.",
         o_que_fazer="Completar os tanques e refazer a carga inicial.", origem=OFICIAL),
    dict(codigo="Power + Papel piscando juntos", grupo="Luzes (sem tela)",
         titulo="Almofada principal cheia/quase cheia",
         o_que_e="Almofada principal no fim da vida útil.",
         o_que_fazer="Trocar/lavar a almofada e fazer o Reset PERMANENTE (ou temporário para liberar).",
         origem=OFICIAL),
    dict(codigo="Power + Papel piscando alternado", grupo="Luzes (sem tela)",
         titulo="Almofada sem margem cheia/quase cheia",
         o_que_e="Almofada da impressão sem margem no fim. Sem margem fica bloqueado.",
         o_que_fazer="Trocar/lavar a almofada sem margem e fazer o Reset PERMANENTE.",
         origem=OFICIAL),
    dict(codigo="Tinta + Papel piscando juntos", grupo="Luzes (sem tela)",
         titulo="Almofada principal cheia (alguns modelos)",
         o_que_e="Em parte dos modelos sem tela, este é o aviso de almofada principal.",
         o_que_fazer="Ler os contadores no programa para confirmar e fazer o reset.",
         origem=OFICIAL),
    dict(codigo="Tinta + Papel piscando alternado", grupo="Luzes (sem tela)",
         titulo="Almofada sem margem (alguns modelos)",
         o_que_e="Em parte dos modelos sem tela, aviso da almofada sem margem.",
         o_que_fazer="Ler os contadores no programa para confirmar e fazer o reset.",
         origem=OFICIAL),
    dict(codigo="Todas as luzes piscando", grupo="Luzes (sem tela)", titulo="Erro geral da impressora",
         o_que_e="Erro de hardware ou papel/material de proteção preso.",
         o_que_fazer="Tirar papel e travas de transporte, desligar e ligar. Se continuar: "
                     "use 'Diagnosticar' para ler o código interno (carro, encoder, cabeça, placa).",
         origem=OFICIAL),
    dict(codigo="Wi-Fi + Wi-Fi Direct piscando", grupo="Luzes (sem tela)", titulo="Erro de Wi-Fi",
         o_que_e="Falha na conexão sem fio.",
         o_que_fazer="Apertar o botão Wi-Fi para limpar o erro e tentar de novo.", origem=OFICIAL),
    dict(codigo="Tinta + Papel + Wi-Fi + Wi-Fi Direct acesas", grupo="Luzes (sem tela)",
         titulo="Erro na atualização de firmware",
         o_que_e="Firmware não foi gravado (modo de recuperação).",
         o_que_fazer="Ligar pelo cabo USB e regravar o firmware.", origem=OFICIAL),
    dict(codigo="Tinta + Papel acesas", grupo="Luzes (sem tela)", titulo="Desligada de forma errada",
         o_que_e="A impressora foi desligada da tomada sem usar o botão.",
         o_que_fazer="Apertar o botão de cópia, fazer teste de bicos e cancelar trabalhos pendentes.",
         origem=OFICIAL),

    # ---------------- Códigos internos (NÃO oficiais)
    dict(codigo="000031", grupo="Código interno (não oficial)", titulo="Erro de movimento do carro",
         o_que_e="O carro não se move ou a impressora não lê a posição dele (falso atolamento).",
         o_que_fazer="Verificar obstrução no caminho do carro, trava de transporte, encoder "
                     "(fita e sensor), correia e motor CR.",
         origem=NAO_OFICIAL),
    dict(codigo="031006", grupo="Código interno (não oficial)", titulo="Falha elétrica cabeça/placa",
         o_que_e="Comunicação/alimentação da cabeça com a placa (comum após tinta na placa ou cabo flat).",
         o_que_fazer="Verificar cabos flat da cabeça, fusível da placa e sinais de tinta/curto. "
                     "Pode ser cabeça ou placa principal.",
         origem=NAO_OFICIAL),
]


def buscar(texto: str) -> list[dict]:
    t = (texto or "").strip().lower()
    if not t:
        return list(ERROS)
    return [e for e in ERROS if t in " ".join(
        [e["codigo"], e["titulo"], e["o_que_e"], e["grupo"]]).lower()]


def chave(e: dict) -> str:
    return "tabela:" + e["codigo"]
