# OS 3D – Ordens de serviço da assistência

Endereço: https://luanullmann.github.io/info3dcartuchos/os/

## Modo demonstração (já funciona)
Abra o endereço e use. Os dados ficam **só no navegador** em que você abriu.
Serve para testar. Se limpar o histórico do navegador, as OS somem.

## Ligar na nuvem (PC do balcão + celular juntos)
Grátis no plano Free do Supabase.

1. Crie uma conta em https://supabase.com e clique em **New project**
   (nome: os3d, região: São Paulo; anote a senha do banco).
2. No projeto: **SQL Editor > New query**, cole todo o arquivo `supabase.sql` e clique em **Run**.
3. **Authentication > Sign In / Providers > Email**: desligue *Confirm email*
   (assim a conta já entra sem precisar confirmar no e-mail).
4. **Project Settings > API**: copie a *Project URL* e a chave *anon public*.
5. No GitHub, edite `os/config.js` e cole os dois valores. Salve (commit).
6. Abra o endereço, clique em **Criar conta**, depois em **Entrar**.
   Para outro funcionário usar a mesma loja, por enquanto entrem todos com o mesmo login.

A chave *anon* pode ficar pública: a segurança é feita pelo próprio banco
(cada loja só enxerga as próprias OS). Nunca cole a chave *service_role*.

## O que tem nesta versão
- Painel com contadores e busca por nº, cliente, modelo ou série
- Nova OS: cliente pelo WhatsApp (puxa o cadastro), aparelho, defeito, acessórios e fotos
- Orçamento com itens e total, laudo, garantia e status
- Botão de WhatsApp com a mensagem pronta e o link para o cliente aprovar ou recusar pelo celular
- Via impressa (cliente e loja) com termos e assinatura
- Configurações da loja

## Pix
Em **Minha loja**, preencha o tipo e a chave Pix e a cidade. Quando o cliente aprova o
orçamento, o link mostra o QR Code e o "copia e cola" com o valor exato da OS.
O dinheiro cai direto na sua conta, sem taxa. O sistema **não confirma sozinho**:
o cliente aperta "Já paguei", você confere no app do banco e clica em **Marcar como pago**.
(Bibliotecas: qrcode-generator, MIT, em `vendor/`.)

## Próximos passos
- Usuários separados por funcionário
- Estoque de peças e caixa
- Botão "Ler impressora" ligado ao Printer's 3D Utility
