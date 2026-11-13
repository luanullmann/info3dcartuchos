// Camada de dados do OS 3D: modo demonstração (localStorage) ou nuvem (Supabase).

export const STATUS = {
  orcamento: { nome: "Aguardando orçamento", cor: "cinza" },
  aprovacao: { nome: "Aguardando aprovação", cor: "laranja" },
  conserto: { nome: "Em conserto", cor: "azul" },
  recusada: { nome: "Recusada", cor: "vermelho" },
  pronta: { nome: "Pronta p/ retirar", cor: "verde" },
  entregue: { nome: "Entregue", cor: "cinza" },
};

const LOJA_PADRAO = {
  nome: "Minha assistência",
  whatsapp: "",
  endereco: "",
  tecnicos: "",
  cnpj: "",
  logo: "",
  pix_tipo: "cnpj",
  pix_chave: "",
  pix_cidade: "",
  termos:
    "Aparelhos não retirados em 90 dias após o aviso de pronto poderão ser descartados. " +
    "A garantia cobre somente o serviço e as peças trocadas descritos nesta OS.",
};

function novoToken() {
  const a = new Uint8Array(12);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function soDigitos(s) {
  return (s || "").replace(/\D/g, "");
}

// ------------------------------------------------------------ fotos
export function formatarCNPJ(s) {
  const d = soDigitos(s).slice(0, 14);
  if (d.length !== 14) return (s || "").trim();
  return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

export async function comprimirFoto(arquivo, max = 1280, tipo = "image/jpeg") {
  const img = await new Promise((ok, erro) => {
    const i = new Image();
    i.onload = () => ok(i);
    i.onerror = erro;
    i.src = URL.createObjectURL(arquivo);
  });
  const k = Math.min(1, max / Math.max(img.width, img.height));
  const c = document.createElement("canvas");
  c.width = Math.round(img.width * k);
  c.height = Math.round(img.height * k);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  URL.revokeObjectURL(img.src);
  return await new Promise((ok) => c.toBlob(ok, tipo, 0.8));
}

function blobParaDataURL(blob) {
  return new Promise((ok) => {
    const r = new FileReader();
    r.onload = () => ok(r.result);
    r.readAsDataURL(blob);
  });
}

// ------------------------------------------------------------ demonstração
class BancoDemo {
  modo = "demo";
  #chave = "os3d_demo";

  #ler() {
    try {
      return JSON.parse(localStorage.getItem(this.#chave)) || this.#vazio();
    } catch {
      return this.#vazio();
    }
  }
  #vazio() {
    return { loja: { ...LOJA_PADRAO }, prox: 1, ordens: [], clientes: [] };
  }
  #gravar(d) {
    try {
      localStorage.setItem(this.#chave, JSON.stringify(d));
    } catch (e) {
      throw new Error("O navegador ficou sem espaço (muitas fotos no modo demonstração).");
    }
  }

  async sessao() { return { email: "demonstração" }; }
  async entrar() {}
  async cadastrar() {}
  async sair() {}
  async garantirLoja() {}

  async loja() { return this.#ler().loja; }
  async salvarLoja(dados) {
    const d = this.#ler();
    d.loja = { ...d.loja, ...dados };
    this.#gravar(d);
  }

  async listarOS() {
    return this.#ler().ordens.slice().sort((a, b) => b.numero - a.numero);
  }
  async obterOS(id) {
    return this.#ler().ordens.find((o) => o.id === id) || null;
  }
  async criarOS(dados) {
    const d = this.#ler();
    const agora = new Date().toISOString();
    const os = {
      acessorios: [], itens: [], fotos: [], laudo: "", garantia_dias: 90,
      ...dados,
      id: crypto.randomUUID(),
      numero: d.prox++,
      status: "orcamento",
      token: novoToken(),
      criado_em: agora,
      atualizado_em: agora,
      eventos: [{ em: agora, texto: "Entrada do aparelho" }],
    };
    d.ordens.push(os);
    this.#gravar(d);
    return os;
  }
  async atualizarOS(id, campos) {
    const d = this.#ler();
    const os = d.ordens.find((o) => o.id === id);
    if (!os) throw new Error("OS não encontrada");
    Object.assign(os, campos, { atualizado_em: new Date().toISOString() });
    this.#gravar(d);
    return os;
  }
  async buscarCliente(whatsapp) {
    const w = soDigitos(whatsapp);
    return this.#ler().clientes.find((c) => c.whatsapp === w) || null;
  }
  async salvarCliente({ nome, whatsapp, cpf }) {
    const d = this.#ler();
    const w = soDigitos(whatsapp);
    let c = d.clientes.find((x) => x.whatsapp === w && w);
    if (c) { c.nome = nome; if (cpf) c.cpf = cpf; }
    else d.clientes.push((c = { id: crypto.randomUUID(), nome, whatsapp: w, cpf: cpf || null }));
    this.#gravar(d);
    return c.id;
  }
  async enviarFoto(_osId, blob) {
    return await blobParaDataURL(blob);
  }
  async enviarLogo(blob) {
    return await blobParaDataURL(blob);
  }
  async informarPagamento(token) {
    const d = this.#ler();
    const os = d.ordens.find((o) => o.token === token);
    if (!os || os.pago || os.pagamento_informado) return false;
    os.pagamento_informado = true;
    os.atualizado_em = new Date().toISOString();
    os.eventos.push({ em: os.atualizado_em, texto: "Cliente avisou que pagou por Pix (confira no banco)" });
    this.#gravar(d);
    return true;
  }
  async osPublica(token) {
    const d = this.#ler();
    const os = d.ordens.find((o) => o.token === token);
    return os ? publico(os, d.loja) : null;
  }
  async responder(token, aprovar) {
    const d = this.#ler();
    const os = d.ordens.find((o) => o.token === token);
    if (!os || os.status !== "aprovacao") return false;
    os.status = aprovar ? "conserto" : "recusada";
    os.atualizado_em = new Date().toISOString();
    os.eventos.push({
      em: new Date().toISOString(),
      texto: aprovar ? "Cliente aprovou o orçamento pelo link" : "Cliente recusou o orçamento pelo link",
    });
    this.#gravar(d);
    return true;
  }
}

function publico(os, loja) {
  // mesmos campos que a função os_publica do Supabase
  return {
    numero: os.numero,
    tipo: os.tipo,
    modelo: os.modelo,
    status: os.status,
    laudo: os.laudo,
    itens: os.itens,
    garantia_dias: os.garantia_dias,
    cliente: (os.cliente_nome || "").split(" ")[0],
    criado_em: os.criado_em,
    eventos: os.eventos,
    loja_nome: loja.nome,
    loja_logo: loja.logo,
    loja_cnpj: loja.cnpj,
    loja_endereco: loja.endereco,
    cliente_nome: os.cliente_nome,
    cliente_whats_final: (os.cliente_whatsapp || "").slice(-4),
    serie: os.serie,
    defeito: os.defeito,
    acessorios: os.acessorios,
    loja_whatsapp: loja.whatsapp,
    pix_tipo: loja.pix_tipo,
    pix_chave: loja.pix_chave,
    pix_cidade: loja.pix_cidade,
    pago: !!os.pago,
    pagamento_informado: !!os.pagamento_informado,
    garantia: !!os.garantia,
  };
}

// ------------------------------------------------------------ nuvem
class BancoNuvem {
  modo = "nuvem";
  constructor(sb) { this.sb = sb; }

  #ok({ data, error }) {
    if (error) throw new Error(error.message);
    return data;
  }

  async sessao() {
    const { data } = await this.sb.auth.getSession();
    return data.session ? data.session.user : null;
  }
  async entrar(email, senha) {
    this.#ok(await this.sb.auth.signInWithPassword({ email, password: senha }));
  }
  async cadastrar(email, senha) {
    this.#ok(await this.sb.auth.signUp({ email, password: senha }));
  }
  async sair() { await this.sb.auth.signOut(); }
  async garantirLoja(nome) {
    this.#ok(await this.sb.rpc("criar_loja", { nome_loja: nome || LOJA_PADRAO.nome }));
  }

  async loja() {
    const r = this.#ok(await this.sb.from("lojas").select("*").maybeSingle());
    if (!r) return null;
    // campo vazio no banco não apaga o padrão (ex.: termos da via impressa)
    const limpo = Object.fromEntries(Object.entries(r).filter(([, v]) => v !== null && v !== ""));
    return { ...LOJA_PADRAO, ...limpo };
  }
  async salvarLoja(dados) {
    const l = await this.loja();
    const { nome, whatsapp, endereco, tecnicos, termos, cnpj, logo, pix_tipo, pix_chave, pix_cidade } = dados;
    this.#ok(await this.sb.from("lojas")
      .update({ nome, whatsapp, endereco, tecnicos, termos, cnpj, logo, pix_tipo, pix_chave, pix_cidade })
      .eq("id", l.id));
  }
  async listarOS() {
    return this.#ok(await this.sb.from("ordens").select("*")
      .order("numero", { ascending: false }).limit(500));
  }
  async obterOS(id) {
    return this.#ok(await this.sb.from("ordens").select("*").eq("id", id).maybeSingle());
  }
  async criarOS(dados) {
    const agora = new Date().toISOString();
    return this.#ok(await this.sb.from("ordens").insert({
      ...dados,
      eventos: [{ em: agora, texto: "Entrada do aparelho" }],
    }).select().single());
  }
  async atualizarOS(id, campos) {
    return this.#ok(await this.sb.from("ordens")
      .update({ ...campos, atualizado_em: new Date().toISOString() })
      .eq("id", id).select().single());
  }
  async buscarCliente(whatsapp) {
    const w = soDigitos(whatsapp);
    if (!w) return null;
    return this.#ok(await this.sb.from("clientes").select("*").eq("whatsapp", w).maybeSingle());
  }
  async salvarCliente({ nome, whatsapp, cpf }) {
    const w = soDigitos(whatsapp);
    if (w) {
      const r = this.#ok(await this.sb.from("clientes")
        .upsert({ nome, whatsapp: w, cpf: cpf || null }, { onConflict: "loja_id,whatsapp" }).select().single());
      return r.id;
    }
    const r = this.#ok(await this.sb.from("clientes").insert({ nome, whatsapp: null, cpf: cpf || null }).select().single());
    return r.id;
  }
  async enviarFoto(osId, blob) {
    const l = await this.loja();
    const caminho = `${l.id}/${osId}/${crypto.randomUUID()}.jpg`;
    this.#ok(await this.sb.storage.from("fotos").upload(caminho, blob, { contentType: "image/jpeg" }));
    return this.sb.storage.from("fotos").getPublicUrl(caminho).data.publicUrl;
  }
  async enviarLogo(blob) {
    const l = await this.loja();
    const caminho = `${l.id}/logo-${crypto.randomUUID()}.png`;
    this.#ok(await this.sb.storage.from("fotos").upload(caminho, blob, { contentType: "image/png" }));
    return this.sb.storage.from("fotos").getPublicUrl(caminho).data.publicUrl;
  }
  async osPublica(token) {
    return this.#ok(await this.sb.rpc("os_publica", { t: token }));
  }
  async responder(token, aprovar) {
    return this.#ok(await this.sb.rpc("os_responder", { t: token, aprovar }));
  }
  async informarPagamento(token) {
    return this.#ok(await this.sb.rpc("os_informar_pagamento", { t: token }));
  }
  get pixAutomatico() { return !!(window.OS3D_CONFIG || {}).pagbank; }
  async gerarPix(token, nome, cpf) {
    const { data, error } = await this.sb.functions.invoke("pix-criar", { body: { t: token, nome, cpf } });
    if (error) {
      let msg = error.message;
      try { msg = (await error.context.json()).erro || msg; } catch { /* sem corpo */ }
      throw new Error(msg);
    }
    if (data?.erro) throw new Error(data.erro);
    return data;
  }
}

export async function criarBanco() {
  const cfg = window.OS3D_CONFIG || {};
  if (cfg.supabaseUrl && cfg.supabaseKey) {
    const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2");
    return new BancoNuvem(createClient(cfg.supabaseUrl, cfg.supabaseKey));
  }
  return new BancoDemo();
}
