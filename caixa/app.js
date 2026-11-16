// Caixa 3D no celular: painel da loja, vender, consultar preço e fiado.
// Lê os dados que o Caixa 3D do computador envia para o Supabase (mesmo do OS 3D).
import { pixCopiaECola } from '../os/pix.js';

const cfg = window.OS3D_CONFIG || {};
const raiz = document.getElementById('raiz');
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const r2 = v => Math.round((Number(v) || 0) * 100) / 100;
const brl = v => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const n2 = v => (Number(v) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const qtdf = v => (Number(v) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 3 });
const num = s => { s = String(s ?? '').trim().replace(/[R$\s]/g, ''); if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.'); return parseFloat(s) || 0; };
const dataBR = s => { if (!s) return ''; const d = new Date(String(s).replace(' ', 'T')); return isNaN(d) ? s : d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); };
const FORMAS = { DINHEIRO: 'Dinheiro', PIX: 'Pix', DEBITO: 'Débito', CREDITO: 'Crédito', FIADO: 'Fiado', OUTRO: 'Outro' };

function toast(msg, tipo = '') {
  const t = document.createElement('div');
  t.className = 'toast ' + tipo; t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), tipo === 'err' ? 5000 : 2800);
}
function sheet(titulo, html) {
  const ov = document.createElement('div');
  ov.className = 'ov';
  ov.innerHTML = `<div class="sheet"><h2>${esc(titulo)}<button class="x" aria-label="Fechar">×</button></h2><div class="corpo">${html}</div></div>`;
  document.body.appendChild(ov);
  const fechar = () => ov.remove();
  $('.x', ov).onclick = fechar;
  ov.addEventListener('click', e => { if (e.target === ov) fechar(); });
  return { el: $('.corpo', ov), fechar };
}

const ICON = {
  painel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 13h8V3H3zM13 21h8V11h-8zM13 3v6h8V3zM3 21h8v-6H3z"/></svg>',
  vender: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.6 12.4a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L22 7H6"/></svg>',
  precos: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r="1.5"/></svg>',
  fiado: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/></svg>',
  scan: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 7V4h3M21 7V4h-3M3 17v3h3M21 17v3h-3M7 8v8M10 8v8M13 8v8M17 8v8"/></svg>'
};

// ---------- estado ----------
let sb = null, usuario = null, aba = 'painel';
const S = { painel: null, painelEm: null, carrinho: { itens: [], cliente: null, desconto: 0 }, timer: null };

async function iniciar() {
  if (!cfg.supabaseUrl) { raiz.innerHTML = '<p class="vazio">Configure o Supabase em os/config.js.</p>'; return; }
  const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
  sb = createClient(cfg.supabaseUrl, cfg.supabaseKey);
  const { data } = await sb.auth.getSession();
  if (data.session) { usuario = data.session.user; abrir(); } else login();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}

function login() {
  raiz.innerHTML = `<div class="login"><img src="icone-192.png" alt=""><h1>Caixa 3D</h1><p>Entre com seu usuário (ou o e-mail do OS 3D) e senha</p>
    <form id="fl"><label class="f">E-mail ou usuário<input class="inp" name="email" type="text" autocapitalize="none" autocorrect="off" autocomplete="username" required></label>
    <label class="f">Senha<input class="inp" name="senha" type="password" autocomplete="current-password" required></label>
    <button class="btn pri full" type="submit">Entrar</button></form></div>`;
  $('#fl').onsubmit = async e => {
    e.preventDefault();
    const f = new FormData(e.target);
    let email = f.get('email').trim().toLowerCase();
    if (!email.includes('@')) email += '@info3dcartuchos.com.br'; // usuário curto da equipe (ex.: daltro)
    const { data, error } = await sb.auth.signInWithPassword({ email, password: f.get('senha') });
    if (error) return toast(/invalid/i.test(error.message) ? 'E-mail ou senha incorretos' : error.message, 'err');
    usuario = data.user; abrir();
  };
}

function abrir() {
  raiz.innerHTML = `<header class="top"><h1 id="tt">Caixa 3D</h1><span class="sp"></span><span class="mini" id="sub"></span>
      <button class="btn sm" id="sair" style="background:transparent;color:#fff;border-color:#3b4d7a">Sair</button></header>
    <main id="pg"></main>
    <nav class="tabs">${[['painel', 'Painel'], ['vender', 'Vender'], ['precos', 'Preços'], ['fiado', 'Fiado']].map(([k, t]) => `<button data-a="${k}">${ICON[k]}${t}</button>`).join('')}</nav>`;
  $('#sair').onclick = async () => { if (confirm('Sair do Caixa 3D neste celular?')) { await sb.auth.signOut(); location.reload(); } };
  $$('nav.tabs button').forEach(b => b.onclick = () => ir(b.dataset.a));
  ir(aba);
  clearInterval(S.timer);
  S.timer = setInterval(() => { if (aba === 'painel' && document.visibilityState === 'visible') telas.painel(); }, 30000);
}

function ir(a) {
  aba = a;
  $$('nav.tabs button').forEach(b => b.classList.toggle('on', b.dataset.a === a));
  $('#tt').textContent = { painel: 'Painel da loja', vender: 'Vender', precos: 'Consultar preço', fiado: 'Fiado' }[a];
  $('#pg').innerHTML = '<p class="vazio">Carregando…</p>';
  telas[a]().catch(e => { $('#pg').innerHTML = `<div class="card" style="color:var(--bad)">${esc(e.message)}</div>`; });
}

async function carregarPainel() {
  const { data, error } = await sb.from('cx_painel').select('dados, atualizado_em').maybeSingle();
  if (error) throw new Error(/cx_painel|schema cache|does not exist/.test(error.message) ? 'As tabelas do celular ainda não foram criadas no Supabase (rode o supabase-caixa.sql).' : error.message);
  S.painel = data ? data.dados : null; S.painelEm = data ? data.atualizado_em : null;
  return S.painel;
}
function avisoSync() {
  if (!S.painelEm) return '<div class="aviso">O computador da loja ainda não enviou os dados. Abra o Caixa 3D no PC e conecte ao OS 3D (Configurações → OS 3D).</div>';
  const min = (Date.now() - new Date(S.painelEm)) / 60000;
  return min > 10 ? `<div class="aviso">Dados de ${dataBR(S.painelEm)}. O Caixa 3D do computador pode estar fechado ou sem internet.</div>` : '';
}

// ---------- leitor de código de barras pela câmera ----------
async function lerCodigo() {
  const s = sheet('Ler código de barras', '<video class="cam" playsinline muted></video><p class="muted" style="text-align:center">Aponte a câmera para o código de barras</p>');
  const video = $('video', s.el);
  let parar = () => {};
  const fechar = s.fechar;
  return new Promise(async resolve => {
    s.fechar = () => { parar(); fechar(); resolve(null); };
    $('.x', s.el.parentElement).onclick = s.fechar;
    const pronto = cod => { parar(); fechar(); resolve(cod); };
    try {
      if ('BarcodeDetector' in window) {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = stream; await video.play();
        const det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'qr_code'] });
        let ativo = true;
        parar = () => { ativo = false; stream.getTracks().forEach(t => t.stop()); };
        const loop = async () => { if (!ativo) return; try { const r = await det.detect(video); if (r[0]) return pronto(r[0].rawValue); } catch (_) {} requestAnimationFrame(loop); };
        loop();
      } else {
        const { BrowserMultiFormatReader } = await import('https://esm.sh/@zxing/browser@0.1.5');
        const leitor = new BrowserMultiFormatReader();
        const ctl = await leitor.decodeFromVideoDevice(undefined, video, (res) => { if (res) pronto(res.getText()); });
        parar = () => { try { ctl.stop(); } catch (_) {} };
      }
    } catch (e) { toast('Não consegui abrir a câmera: ' + e.message, 'err'); s.fechar(); }
  });
}

async function buscarProdutos(q) {
  q = q.trim();
  if (!q) return [];
  const exato = await sb.from('cx_produtos').select('*').eq('ativo', true).or(`codigo_barras.eq.${q},codigo.eq.${q}`).limit(5);
  if (exato.data && exato.data.length) return exato.data;
  const termo = '%' + q.replace(/[%_,()]/g, ' ').trim().replace(/\s+/g, '%') + '%';
  const { data, error } = await sb.from('cx_produtos').select('*').eq('ativo', true).ilike('descricao', termo).order('descricao').limit(40);
  if (error) throw error;
  return data;
}

// ---------- telas ----------
const telas = {
  async painel() {
    const p = await carregarPainel();
    const pg = $('#pg');
    if (!p) { pg.innerHTML = avisoSync(); return; }
    $('#sub').textContent = p.loja || '';
    const dias = []; const hoje = new Date();
    for (let i = 6; i >= 0; i--) { const d = new Date(hoje); d.setDate(d.getDate() - i); const iso = d.toLocaleDateString('sv-SE'); dias.push({ d, t: ((p.ult7 || []).find(x => x.d === iso) || {}).t || 0 }); }
    const max = Math.max(1, ...dias.map(x => x.t));
    const cx = p.caixa;
    pg.innerHTML = `${avisoSync()}
      <div class="g2"><div class="card kpi"><div class="l">Vendas hoje</div><div class="v">${brl(p.hoje.t)}</div><div class="s">${p.hoje.n} venda(s)</div></div>
      <div class="card kpi"><div class="l">No mês</div><div class="v">${brl(p.mes.t)}</div><div class="s">${p.mes.n} venda(s)</div></div></div>
      <div class="card"><div class="row"><h3 style="margin:0">Caixa</h3><span class="sp"></span>${cx ? `<span class="tag ok">Aberto nº ${cx.id}</span>` : '<span class="tag warn">Fechado</span>'}</div>
        ${cx ? `<div class="lin"><div class="t"><b>Dinheiro esperado na gaveta</b><span>aberto em ${dataBR(cx.abertura)} · fundo ${brl(cx.valor_abertura)}</span></div><b class="num">${brl(cx.esperado)}</b></div>
        ${Object.entries(cx.porForma || {}).map(([f, v]) => `<div class="lin"><div class="t">${FORMAS[f] || f}</div><span class="num">${brl(v)}</span></div>`).join('')}
        ${cx.sangrias || cx.suprimentos ? `<div class="lin"><div class="t">Sangrias / suprimentos</div><span class="num">-${n2(cx.sangrias)} / +${n2(cx.suprimentos)}</span></div>` : ''}` : '<p class="muted" style="margin:8px 0 0">Vendas feitas no celular entram quando o caixa do computador estiver aberto.</p>'}</div>
      ${(p.contasPagar || []).length ? `<div class="card" style="border-color:#f5d79b"><h3>🔔 Contas a pagar</h3>${p.contasPagar.map(c => `<div class="lin"><div class="t"><b>${esc(c.descricao)}</b><span>${new Date(c.vencimento + 'T12:00').toLocaleDateString('pt-BR')}${c.fornecedor ? ' · ' + esc(c.fornecedor) : ''}</span></div>
        <span class="tag ${c.dias < 0 ? 'bad' : c.dias === 0 ? 'warn' : 'info'}">${c.dias < 0 ? 'atrasada' : c.dias === 0 ? 'hoje' : 'em ' + c.dias + 'd'}</span><b class="num">${brl(c.valor)}</b></div>`).join('')}</div>` : ''}
      <div class="card"><h3>Últimos 7 dias</h3><div class="bars">${dias.map(x => `<div class="b"><span>${x.t ? Math.round(x.t) : ''}</span><i style="height:${Math.round(x.t / max * 100)}%"></i>${['D', 'S', 'T', 'Q', 'Q', 'S', 'S'][x.d.getDay()]}</div>`).join('')}</div></div>
      <div class="g2"><div class="card kpi"><div class="l">Fiado em aberto</div><div class="v" style="color:var(--bad)">${brl(p.fiado.total)}</div><div class="s">${p.fiado.clientes} cliente(s)</div></div>
      <div class="card kpi"><div class="l">A pagar (7 dias)</div><div class="v">${brl(p.pagar.t)}</div><div class="s">${p.pagar.n} conta(s)</div></div></div>
      <div class="card"><h3>Últimas vendas</h3>${(p.ultimas || []).map(v => `<div class="lin"><div class="t"><b>nº ${v.id} — ${esc(v.cliente || 'Consumidor')}</b><span>${dataBR(v.data)} · ${esc((v.formas || '').split(', ').map(f => FORMAS[f] || f).join(', '))}</span></div>
        ${v.status === 'CANCELADA' ? '<span class="tag bad">cancelada</span>' : `<b class="num">${brl(v.total)}</b>`}</div>`).join('') || '<p class="muted">Nenhuma venda ainda</p>'}</div>
      <div class="card"><h3>Estoque baixo</h3>${(p.baixo || []).map(x => `<div class="lin"><div class="t">${esc(x.descricao)}</div><span class="tag ${x.estoque <= 0 ? 'bad' : 'warn'}">${qtdf(x.estoque)} / mín ${qtdf(x.estoque_min)}</span></div>`).join('') || '<p class="muted">Tudo certo com o estoque</p>'}</div>
      <p class="muted" style="text-align:center;font-size:12px">Atualizado ${dataBR(S.painelEm)} · atualiza sozinho a cada 30 s</p>`;
  },

  async precos() {
    const pg = $('#pg');
    pg.innerHTML = `<div class="busca"><input class="inp" id="q" placeholder="Nome ou código do produto" enterkeyhint="search"><button class="btn scan" id="sc" aria-label="Ler código de barras">${ICON.scan}</button></div><div id="res"><p class="vazio">Digite o nome ou leia o código de barras</p></div>`;
    const mostrar = async q => {
      const lista = await buscarProdutos(q);
      $('#res').innerHTML = lista.length ? `<div class="card">${lista.map(p => `<div class="lin"><div class="t"><b>${esc(p.descricao)}</b><span>${esc(p.codigo_barras || p.codigo || '')} · ${p.tipo === 'S' ? 'serviço' : 'estoque ' + qtdf(p.estoque) + ' ' + esc(p.unidade || '')}</span></div><b class="num" style="font-size:17px">${brl(p.preco_venda)}</b></div>`).join('')}</div>`
        : '<p class="vazio">Nada encontrado</p>';
    };
    let t; $('#q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(() => mostrar(e.target.value).catch(er => toast(er.message, 'err')), 250); });
    $('#sc').onclick = async () => { const c = await lerCodigo(); if (c) { $('#q').value = c; mostrar(c); } };
  },

  async vender() {
    if (!S.painel) await carregarPainel().catch(() => {});
    const pg = $('#pg');
    pg.innerHTML = `${S.painel && !S.painel.caixa ? '<div class="aviso">O caixa do computador está fechado: a venda fica guardada e entra quando ele for aberto.</div>' : ''}
      <div class="busca"><input class="inp" id="q" placeholder="Adicionar produto: nome ou código" enterkeyhint="search"><button class="btn scan" id="sc" aria-label="Ler código de barras">${ICON.scan}</button></div>
      <div id="sug"></div><div id="cli" class="card"></div><div id="car"></div><div style="height:70px"></div>
      <div class="total-bar"><div><div style="font-size:12px;color:#a9b6d6" id="ni"></div><div class="v" id="tot"></div></div><span class="sp"></span><button class="btn ok" id="fin">Finalizar</button></div>`;
    const C = S.carrinho;
    const total = () => r2(C.itens.reduce((a, i) => a + i.qtd * i.preco_unit, 0) - C.desconto);
    const add = p => {
      const ex = C.itens.find(i => i.produto_id === p.id);
      if (ex) ex.qtd++; else C.itens.push({ produto_id: p.id, descricao: p.descricao, qtd: 1, preco_unit: Number(p.preco_venda), estoque: p.estoque, tipo: p.tipo });
      $('#q').value = ''; $('#sug').innerHTML = ''; desenhar(); toast(p.descricao + ' adicionado');
    };
    const desenhar = () => {
      $('#cli').innerHTML = `<div class="row"><div style="flex:1"><div class="muted" style="font-size:12px">Cliente</div><b>${C.cliente ? esc(C.cliente.nome) : 'Consumidor (sem cliente)'}</b>${C.cliente && C.cliente.fiado > 0 ? `<div class="muted" style="font-size:12px">fiado em aberto: ${brl(C.cliente.fiado)}</div>` : ''}</div>
        ${C.cliente ? '<button class="btn sm" id="tc">Tirar</button>' : ''}<button class="btn sm" id="ec">${C.cliente ? 'Trocar' : 'Escolher'}</button></div>`;
      $('#ec').onclick = escolherCliente;
      if ($('#tc')) $('#tc').onclick = () => { C.cliente = null; desenhar(); };
      $('#car').innerHTML = C.itens.length ? `<div class="card">${C.itens.map((i, n) => `<div class="lin"><div class="t"><b>${esc(i.descricao)}</b><span>${brl(i.preco_unit)} cada${i.tipo === 'P' && i.estoque - i.qtd < 0 ? ' · <span style="color:var(--bad)">estoque insuficiente</span>' : ''}</span></div>
        <div class="qtd"><button data-m="${n}" aria-label="Diminuir">−</button><b class="num">${qtdf(i.qtd)}</b><button data-p="${n}" aria-label="Aumentar">+</button></div></div>`).join('')}
        <div class="row" style="margin-top:8px"><span class="muted">Desconto</span><span class="sp"></span><button class="btn sm" id="ds">${C.desconto ? '- ' + brl(C.desconto) : 'Dar desconto'}</button></div></div>`
        : '<p class="vazio">Carrinho vazio. Busque ou leia o código do produto.</p>';
      $$('[data-p]').forEach(b => b.onclick = () => { C.itens[b.dataset.p].qtd++; desenhar(); });
      $$('[data-m]').forEach(b => b.onclick = () => { const i = C.itens[b.dataset.m]; i.qtd--; if (i.qtd <= 0) C.itens.splice(b.dataset.m, 1); desenhar(); });
      if ($('#ds')) $('#ds').onclick = () => { const v = prompt('Desconto em R$ (ex: 5,00) ou em % (ex: 10%)', C.desconto ? n2(C.desconto) : ''); if (v === null) return; const sub = C.itens.reduce((a, i) => a + i.qtd * i.preco_unit, 0); C.desconto = /%/.test(v) ? r2(sub * num(v) / 100) : num(v); if (C.desconto > sub) C.desconto = 0; desenhar(); };
      $('#ni').textContent = C.itens.length ? C.itens.reduce((a, i) => a + i.qtd, 0) + ' item(ns)' : 'Total';
      $('#tot').textContent = brl(total());
      $('#fin').disabled = !C.itens.length;
    };
    const escolherCliente = () => {
      const s = sheet('Escolher cliente', '<input class="inp" id="qc" placeholder="Nome, telefone ou CPF" style="margin-bottom:10px"><div id="lc"></div>');
      let t;
      $('#qc', s.el).addEventListener('input', e => { clearTimeout(t); t = setTimeout(async () => {
        const q = e.target.value.trim(); if (q.length < 2) return;
        const d = q.replace(/\D/g, '');
        let qr = sb.from('cx_clientes').select('*').eq('ativo', true).limit(30);
        qr = d.length >= 4 ? qr.or(`telefone.ilike.%${d.slice(-8)}%,cpf_cnpj.ilike.%${d}%,nome.ilike.%${q}%`) : qr.ilike('nome', '%' + q.replace(/\s+/g, '%') + '%');
        const { data } = await qr.order('nome');
        $('#lc', s.el).innerHTML = (data || []).map((c, i) => `<div class="lin" data-i="${i}" style="cursor:pointer"><div class="t"><b>${esc(c.nome)}</b><span>${esc(c.telefone || '')} ${esc(c.cpf_cnpj || '')}</span></div>${c.fiado > 0 ? `<span class="tag bad">${brl(c.fiado)}</span>` : ''}</div>`).join('') || '<p class="vazio">Nenhum cliente</p>';
        $$('[data-i]', s.el).forEach(x => x.onclick = () => { C.cliente = data[x.dataset.i]; s.fechar(); desenhar(); });
      }, 250); });
      setTimeout(() => $('#qc', s.el).focus(), 50);
    };
    let t;
    $('#q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(async () => {
      const q = e.target.value.trim(); if (q.length < 2) { $('#sug').innerHTML = ''; return; }
      const lista = await buscarProdutos(q);
      $('#sug').innerHTML = lista.length ? `<div class="card">${lista.slice(0, 12).map((p, i) => `<div class="lin" data-i="${i}" style="cursor:pointer"><div class="t"><b>${esc(p.descricao)}</b><span>${p.tipo === 'S' ? 'serviço' : 'estoque ' + qtdf(p.estoque)}</span></div><b class="num">${brl(p.preco_venda)}</b></div>`).join('')}</div>` : '<p class="vazio">Nada encontrado</p>';
      $$('#sug [data-i]').forEach(x => x.onclick = () => add(lista[x.dataset.i]));
    }, 250); });
    $('#q').addEventListener('keydown', async e => { if (e.key === 'Enter') { const l = await buscarProdutos(e.target.value); if (l.length === 1) add(l[0]); } });
    $('#sc').onclick = async () => { const c = await lerCodigo(); if (!c) return; const l = await buscarProdutos(c); if (l.length) add(l[0]); else toast('Produto não encontrado: ' + c, 'err'); };
    $('#fin').onclick = () => finalizar(total(), desenhar);
    desenhar();
  },

  async fiado() {
    const p = await carregarPainel();
    const pg = $('#pg');
    pg.innerHTML = `${avisoSync()}<div class="card kpi"><div class="l">Total em aberto</div><div class="v" style="color:var(--bad)">${brl(p ? p.fiado.total : 0)}</div><div class="s">${p ? p.fiado.clientes : 0} cliente(s)</div></div>
      <input class="inp" id="q" placeholder="Buscar cliente" style="margin-bottom:12px"><div id="lst"></div>`;
    const desenhar = lista => {
      $('#lst').innerHTML = lista.length ? `<div class="card">${lista.map((c, i) => `<div class="lin"><div class="t"><b>${esc(c.nome)}</b><span>${esc(c.telefone || 'sem telefone')}${c.vencimento ? ' · desde ' + new Date(c.vencimento + 'T12:00').toLocaleDateString('pt-BR') : ''}</span></div>
        <b class="num" style="color:var(--bad)">${brl(c.total ?? c.fiado)}</b>${c.telefone ? `<button class="btn sm" data-z="${i}">Cobrar</button>` : ''}</div>`).join('')}</div>` : '<p class="vazio">Ninguém devendo</p>';
      $$('[data-z]').forEach(b => b.onclick = () => {
        const c = lista[b.dataset.z];
        let f = String(c.telefone || '').split('/')[0].replace(/\D/g, ''); if (f.length <= 9) f = '21' + f;
        const txt = `Olá ${c.nome.split(' ')[0]}! Tudo bem? Aqui é da ${S.painel ? S.painel.loja : 'loja'}. Passando para lembrar do valor em aberto de ${brl(c.total ?? c.fiado)}. Qualquer dúvida, estamos à disposição!`;
        window.open('https://wa.me/55' + f + '?text=' + encodeURIComponent(txt));
      });
    };
    desenhar(p ? p.devedores || [] : []);
    let t;
    $('#q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(async () => {
      const q = e.target.value.trim(); if (!q) return desenhar(p ? p.devedores || [] : []);
      const { data } = await sb.from('cx_clientes').select('*').gt('fiado', 0).ilike('nome', '%' + q.replace(/\s+/g, '%') + '%').order('fiado', { ascending: false }).limit(40);
      desenhar(data || []);
    }, 250); });
  }
};

// ---------- finalizar venda ----------
function finalizar(total, redesenhar) {
  const C = S.carrinho;
  const s = sheet('Pagamento', `<div style="text-align:center;margin-bottom:12px"><div class="muted">Total</div><div style="font-size:34px;font-weight:700">${brl(total)}</div></div>
    <div class="formas">${['DINHEIRO', 'PIX', 'DEBITO', 'CREDITO', 'FIADO'].map(f => `<button class="btn" data-f="${f}">${FORMAS[f]}</button>`).join('')}</div><div id="det" style="margin-top:14px"></div>`);
  const det = $('#det', s.el);
  const enviar = async pagamentos => {
    det.innerHTML = '<p class="vazio">Enviando…</p>';
    const venda = {
      usuario: usuario.email, cliente_id: C.cliente ? C.cliente.id : null, cliente_nome: C.cliente ? C.cliente.nome : null,
      itens: C.itens.map(i => ({ produto_id: i.produto_id, descricao: i.descricao, qtd: i.qtd, preco_unit: i.preco_unit })),
      pagamentos, desconto: C.desconto, total
    };
    const { data, error } = await sb.from('cx_vendas_moveis').insert(venda).select('id').single();
    if (error) { det.innerHTML = `<p style="color:var(--bad)">${esc(error.message)}</p>`; return; }
    S.carrinho = { itens: [], cliente: null, desconto: 0 };
    redesenhar && aba === 'vender' && telas.vender();
    acompanhar(data.id, s);
  };
  $$('[data-f]', s.el).forEach(b => b.onclick = () => {
    $$('[data-f]', s.el).forEach(x => x.classList.toggle('pri', x === b));
    const f = b.dataset.f;
    if (f === 'DINHEIRO') {
      det.innerHTML = `<label class="f">Valor recebido<input class="inp" id="rec" inputmode="decimal" value="${n2(total)}"></label><div id="tr" style="font-size:20px;font-weight:700;color:var(--ok);margin-bottom:10px"></div><button class="btn ok full" id="ok">Concluir venda</button>`;
      const upd = () => { const t = r2(num($('#rec', det).value) - total); $('#tr', det).textContent = t > 0 ? 'Troco: ' + brl(t) : ''; };
      $('#rec', det).oninput = upd; upd();
      $('#ok', det).onclick = () => { const v = num($('#rec', det).value); if (v + 0.001 < total) return toast('Valor menor que o total', 'err'); enviar([{ forma: 'DINHEIRO', valor: r2(v) }]); };
    } else if (f === 'PIX') {
      const p = (S.painel && S.painel.pix) || {};
      let codigo = '';
      try { codigo = pixCopiaECola({ chave: p.chave, tipo: /@/.test(p.chave) ? 'email' : /^\d{11}$|^\d{14}$/.test(p.chave) ? 'cnpj' : 'aleatoria', nome: p.nome, cidade: p.cidade, valor: total, txid: 'CEL' + Date.now().toString(36).toUpperCase() }); } catch (e) { det.innerHTML = `<p style="color:var(--bad)">${esc(e.message)}</p>`; return; }
      let img = ''; try { const q = window.qrcode(0, 'M'); q.addData(codigo); q.make(); img = q.createDataURL(6, 2); } catch (_) {}
      det.innerHTML = `${img ? `<img class="qr" src="${img}" alt="QR Code Pix">` : ''}<p class="muted" style="text-align:center;margin:4px 0 10px">O cliente lê o QR no app do banco. Confira no PagBank se o Pix caiu.</p>
        <button class="btn full" id="cp" style="margin-bottom:10px">Copiar Pix copia e cola</button><button class="btn ok full" id="ok">Pix recebido ✓</button>`;
      $('#cp', det).onclick = async () => { try { await navigator.clipboard.writeText(codigo); toast('Código copiado', 'ok'); } catch (_) { prompt('Copie o código:', codigo); } };
      $('#ok', det).onclick = () => enviar([{ forma: 'PIX', valor: total }]);
    } else if (f === 'FIADO') {
      if (!C.cliente) { det.innerHTML = '<p style="color:var(--bad)">Escolha o cliente antes de vender no fiado.</p>'; return; }
      const v = new Date(); v.setDate(v.getDate() + 30);
      det.innerHTML = `<p>Cliente: <b>${esc(C.cliente.nome)}</b></p><label class="f">Vencimento<input class="inp" type="date" id="ven" value="${v.toLocaleDateString('sv-SE')}"></label><button class="btn ok full" id="ok">Concluir no fiado</button>`;
      $('#ok', det).onclick = () => enviar([{ forma: 'FIADO', valor: total, vencimento: $('#ven', det).value }]);
    } else {
      det.innerHTML = `${f === 'CREDITO' ? '<label class="f">Parcelas<input class="inp" id="par" inputmode="numeric" value="1"></label>' : ''}<p class="muted">Passe o cartão na maquininha e conclua quando aprovar.</p><button class="btn ok full" id="ok">Pagamento aprovado — concluir</button>`;
      $('#ok', det).onclick = () => enviar([{ forma: f, valor: total, parcelas: f === 'CREDITO' ? Math.max(1, parseInt($('#par', det).value) || 1) : 1 }]);
    }
  });
}

async function acompanhar(id, s) {
  const el = s.el;
  el.innerHTML = '<div style="text-align:center;padding:20px 0"><div style="font-size:40px">⏳</div><b>Venda enviada</b><p class="muted" id="st">Aguardando o caixa do computador registrar…</p></div><button class="btn full" id="nv">Nova venda</button>';
  $('#nv', el).onclick = () => { s.fechar(); ir('vender'); };
  for (let i = 0; i < 60 && document.body.contains(el); i++) {
    await new Promise(r => setTimeout(r, 3000));
    const { data } = await sb.from('cx_vendas_moveis').select('status, venda_id, erro').eq('id', id).single();
    if (!data) continue;
    if (data.status === 'PROCESSADA') { el.firstElementChild.innerHTML = `<div style="font-size:40px">✅</div><b>Venda nº ${data.venda_id} registrada no caixa</b><p class="muted">O estoque foi baixado no computador.</p>`; return; }
    if (data.status === 'ERRO') { el.firstElementChild.innerHTML = `<div style="font-size:40px">⚠️</div><b>O caixa recusou a venda</b><p style="color:var(--bad)">${esc(data.erro || '')}</p>`; return; }
    if (data.erro) $('#st', el).textContent = data.erro;
  }
}

iniciar().catch(e => { raiz.innerHTML = `<p class="vazio">${esc(e.message)}</p>`; });
