-- OS 3D – banco de dados no Supabase
-- Cole tudo no Supabase: SQL Editor > New query > Run. Pode rodar de novo sem problema.

create table if not exists lojas (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  whatsapp text,
  endereco text,
  tecnicos text,
  termos text,
  prox_numero int not null default 1,
  criado_em timestamptz not null default now()
);

alter table lojas add column if not exists cnpj text;
alter table lojas add column if not exists logo text;

create table if not exists membros (
  user_id uuid primary key references auth.users on delete cascade,
  loja_id uuid not null references lojas on delete cascade,
  criado_em timestamptz not null default now()
);

create or replace function minha_loja() returns uuid
language sql stable security definer set search_path = public as $$
  select loja_id from membros where user_id = auth.uid()
$$;

create table if not exists clientes (
  id uuid primary key default gen_random_uuid(),
  loja_id uuid not null default minha_loja() references lojas on delete cascade,
  nome text not null,
  whatsapp text,
  criado_em timestamptz not null default now(),
  unique (loja_id, whatsapp)
);

create table if not exists ordens (
  id uuid primary key default gen_random_uuid(),
  loja_id uuid not null default minha_loja() references lojas on delete cascade,
  numero int,
  cliente_id uuid references clientes on delete set null,
  cliente_nome text,
  cliente_whatsapp text,
  tipo text,
  modelo text,
  serie text,
  defeito text,
  acessorios jsonb not null default '[]',
  tecnico text,
  previsao date,
  taxa text,
  laudo text default '',
  itens jsonb not null default '[]',
  garantia_dias int not null default 90,
  status text not null default 'orcamento',
  token text not null unique default replace(gen_random_uuid()::text, '-', ''),
  fotos jsonb not null default '[]',
  eventos jsonb not null default '[]',
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists ordens_loja_numero on ordens (loja_id, numero desc);

-- número sequencial por loja
create or replace function numerar_os() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update lojas set prox_numero = prox_numero + 1
   where id = new.loja_id
   returning prox_numero - 1 into new.numero;
  return new;
end $$;
drop trigger if exists numerar_os on ordens;
create trigger numerar_os before insert on ordens for each row execute function numerar_os();

-- primeiro acesso: cria a loja e liga o usuário a ela
create or replace function criar_loja(nome_loja text) returns uuid
language plpgsql security definer set search_path = public as $$
declare l uuid;
begin
  if auth.uid() is null then raise exception 'faça login'; end if;
  select loja_id into l from membros where user_id = auth.uid();
  if l is not null then return l; end if;
  insert into lojas (nome) values (nome_loja) returning id into l;
  insert into membros (user_id, loja_id) values (auth.uid(), l);
  return l;
end $$;

-- segurança: cada loja só enxerga os próprios dados
alter table lojas enable row level security;
alter table membros enable row level security;
alter table clientes enable row level security;
alter table ordens enable row level security;

drop policy if exists loja_propria on lojas;
create policy loja_propria on lojas for all to authenticated
  using (id = minha_loja()) with check (id = minha_loja());
drop policy if exists membro_proprio on membros;
create policy membro_proprio on membros for select to authenticated
  using (loja_id = minha_loja());
drop policy if exists clientes_loja on clientes;
create policy clientes_loja on clientes for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());
drop policy if exists ordens_loja on ordens;
create policy ordens_loja on ordens for all to authenticated
  using (loja_id = minha_loja()) with check (loja_id = minha_loja());

-- página do cliente (link do WhatsApp): só lê pelo token, sem login
create or replace function os_publica(t text) returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'numero', o.numero, 'tipo', o.tipo, 'modelo', o.modelo, 'status', o.status,
    'laudo', o.laudo, 'itens', o.itens, 'garantia_dias', o.garantia_dias,
    'cliente', split_part(coalesce(o.cliente_nome, ''), ' ', 1),
    'criado_em', o.criado_em, 'eventos', o.eventos,
    'loja_nome', l.nome, 'loja_whatsapp', l.whatsapp)
  from ordens o join lojas l on l.id = o.loja_id
  where o.token = t
$$;

create or replace function os_responder(t text, aprovar boolean) returns boolean
language plpgsql security definer set search_path = public as $$
begin
  update ordens set
    status = case when aprovar then 'conserto' else 'recusada' end,
    atualizado_em = now(),
    eventos = eventos || jsonb_build_array(jsonb_build_object(
      'em', now(),
      'texto', case when aprovar then 'Cliente aprovou o orçamento pelo link'
                    else 'Cliente recusou o orçamento pelo link' end))
  where token = t and status = 'aprovacao';
  return found;
end $$;

grant execute on function os_publica(text) to anon, authenticated;
grant execute on function os_responder(text, boolean) to anon, authenticated;
grant execute on function criar_loja(text) to authenticated;

-- fotos: pasta pública com nomes aleatórios; só a loja grava na própria pasta
insert into storage.buckets (id, name, public) values ('fotos', 'fotos', true)
  on conflict (id) do nothing;
drop policy if exists fotos_grava on storage.objects;
create policy fotos_grava on storage.objects for insert to authenticated
  with check (bucket_id = 'fotos' and (storage.foldername(name))[1] = minha_loja()::text);
