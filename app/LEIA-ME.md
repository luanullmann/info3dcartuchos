# Printer's 3D Utility

Programa gratuito para Windows, para impressoras Epson, pelo **Wi-Fi/rede** ou **cabo USB**:

- **Reset de almofadas**: lê os contadores e faz reset permanente (com backup) ou temporário.
- **Diagnóstico**: lê o status e o histórico de erros da impressora e mostra em português o que fazer.
- **Tabela de erros Epson**: códigos da tela (E-01, E-11, W-01...) e padrões de luzes dos modelos sem tela, resumidos dos manuais da Epson.
- **Fotos e soluções da assistência**: em qualquer erro, use *Adicionar foto* e *Editar solução*. Tudo fica salvo em `diagnosticos.json` e na pasta `fotos`.
- **Teste de impressão**: página de qualidade completa (cores, degradês, cinza, linhas finas, texto pequeno) e página de barras CMYK, com o guia do que cada defeito indica. Imprime por qualquer impressora instalada no Windows.
- **Histórico por número de série**: cada diagnóstico fica gravado na pasta `historico`.

A comunicação com a impressora usa a biblioteca aberta
[epson_print_conf](https://github.com/Ircama/epson_print_conf) (Ircama, licença EUPL-1.2).

## Como gerar o .exe (uma vez só)

**Opção A, no PC com Windows:**
1. Instale o Python 3.11 ou mais novo pelo site python.org e marque **"Add python.exe to PATH"**.
2. Descompacte esta pasta e dê dois cliques em **COMPILAR.bat**.
3. O programa fica em `dist\Printers3DUtility.exe`. Leve junto o `modelos_extra.json` e o `diagnosticos.json`.

**Opção B, sem instalar nada (pelo GitHub):**
1. Crie um repositório no GitHub e envie esta pasta para ele.
2. Abra a aba **Actions**. A compilação roda sozinha.
3. Baixe o artefato **Printers3DUtility-windows** (o arquivo .exe já vem pronto).

Para testar sem compilar, use `RODAR_SEM_COMPILAR.bat` (também precisa do Python).

## Como usar

1. **Conexão**
   - **Wi-Fi/rede:** clique em *Procurar na rede* ou digite o IP. Se não tiver roteador,
     conecte o PC no **Wi-Fi Direct** da impressora (o IP costuma ser 192.168.223.1).
   - **USB:** usa o driver da Epson que já está instalado. Nenhum driver é trocado.
2. **Modelo**: clique em *Detectar modelo* ou escolha na lista.
3. **Ler contadores** mostra a porcentagem de cada almofada.
4. **Reset PERMANENTE**: o programa salva antes um **backup** da EEPROM na pasta `backups`,
   depois grava e confere cada byte. No fim, desligue e ligue a impressora.
5. **Reset temporário**: libera a impressão até desligar. Funciona até em modelos
   que não estão no banco e nos que têm bloqueio pela rede.
6. **Restaurar backup**: grava de volta os valores salvos, caso algo dê errado.

## Situação dos modelos mais comuns

| Modelo | Wi-Fi permanente | Wi-Fi temporário | USB permanente |
|---|---|---|---|
| L3150 / L3151 / L3160 | ✔ (*) | ✔ | ✔ |
| L4150 / L4160 | ✔ (*) | ✔ | ✔ |
| L3250 / L3251 | ✖ bloqueado pelo firmware | ✔ | precisa cadastrar |
| L4260, L1250 | provável bloqueio | ✔ | precisa cadastrar |
| L3210, L3110 | não têm Wi-Fi | — | precisa cadastrar |

(*) Desde que o firmware não tenha sido atualizado para uma versão que bloqueia o acesso.

São 117 modelos no banco no total: L355, L365, L395, L405, L3060, toda a linha
ET-2xxx/4xxx e muitas XP. Veja a lista completa no programa.

## Cadastrar modelos novos (`modelos_extra.json`)

Para modelos que não estão no banco (L4260, L1250, L3210...), é preciso saber
a chave de leitura, a chave de gravação e os endereços dos contadores.
1. Escolha um modelo **parecido** que já esteja no banco e use **Descobrir chave (avançado)**.
   Esse botão só lê, não grava nada.
2. Preencha uma entrada no `modelos_extra.json` (tem um exemplo dentro do arquivo).
3. **Antes de fazer o reset permanente, confira os contadores com "Ler contadores"**.
   Os valores devem bater com o que a impressora mostra, com a almofada cheia perto de 100%.

## Avisos importantes

- Zerar o contador **não limpa a almofada**. Troque ou lave a almofada, ou instale
  um coletor externo, senão a tinta vaza sobre a placa.
- Gravar na EEPROM com dados errados pode deixar a impressora com defeito.
  Por isso o programa sempre faz backup antes de gravar e só permite o reset
  permanente nos modelos que estão no banco.
- Canon não é suportada nesta versão.
- A Epson não publica os códigos internos de erro fatal (como 000031 e 031006). Os poucos que estão na tabela vêm de fontes de assistência e aparecem em laranja, marcados como "não oficial".

## Licença

EUPL-1.2, a mesma da biblioteca usada. O programa é livre para usar e
distribuir. Se você distribuir uma versão modificada, precisa disponibilizar
o código-fonte junto.
