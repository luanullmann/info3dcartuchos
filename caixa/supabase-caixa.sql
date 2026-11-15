-- Caixa 3D no celular – tabelas na nuvem (mesmo projeto do OS 3D)
-- Cole tudo no Supabase: SQL Editor > New query > Run. Pode rodar de novo sem problema.
-- O Caixa 3D do computador envia produtos, clientes e o resumo da loja;
-- o celular lê esses dados e manda as vendas, que o computador registra no caixa.

create table if not exists cx_produtos (
  loja_id uuid not null default minha_loja() references lojas on delete cascade,
  id bigint not null,
  codigo text,
  codigo_barras text,
  descricao text not null,
  tipo text default 'P',
  unidade text default 'UN',
  categoria text,
  preco_venda numeric not null default 0,
  estoque numeric not null default 0,
  estoque_min numeric not null default 0,
  ativo boolean not null default true,
  atualizado_em timestamptz not null default now(),
  primary key (loja_id, id)
);
create index if not exists cx_produtos_barras on cx_produtos (loja_id, codigo_barras);

create table if not exists cx_clientes (
  loja_id uuid not null default minha_loja() references lojas on delete cascade,
  id bigint not null,
  nome text not null,
  telefone text,
  cpf_cnpj text,
  fiado numeric not null default 0,
  ativo boolean not null default true,
  atualizado_em timestamptz not null default now(),
  primary key (loja_id, id)
);

create table if not exists cx_painel (
  loja_id uuid primary key default minha_loja() references lojas on delete cascade,
  dados jsonb not null default '{}',
  atualizado_em timestamptz not null default now()
);

create table if not exists cx_vendas_moveis (
  id uuid primary key default gen_random_uuid(),
  loja_id uuid not null default minha_loja() references lojas on delete cascade,
  criado_em timestamptz not null default now(),
  usuario text,
  cliente_id bigint,
  cliente_nome text,
  itens jsonb not null default '[]',
  pagamentos jsonb not null default '[]',
  desconto numeric not null default 0,
  total numeric not null default 0,
  status text not null default 'PENDENTE',  -- PENDENTE, PROCESSADA, ERRO
  venda_id bigint,
  erro text,
  processada_em timestamptz
);
create index if not exists cx_vendas_moveis_status on cx_vendas_moveis (loja_id, status, criado_em);

alter table cx_produtos enable row level security;
alter table cx_clientes enable row level security;
alter table cx_painel enable row level security;
alter table cx_vendas_moveis enable row level security;

drop policy if exists cx_produtos_loja on cx_produtos;
create policy cx_produtos_loja on cx_produtos for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());
drop policy if exists cx_clientes_loja on cx_clientes;
create policy cx_clientes_loja on cx_clientes for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());
drop policy if exists cx_painel_loja on cx_painel;
create policy cx_painel_loja on cx_painel for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());
drop policy if exists cx_vendas_moveis_loja on cx_vendas_moveis;
create policy cx_vendas_moveis_loja on cx_vendas_moveis for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());

grant select, insert, update, delete on cx_produtos, cx_clientes, cx_painel, cx_vendas_moveis to authenticated;
