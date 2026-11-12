import { criarBanco, STATUS, soDigitos, comprimirFoto } from "./dados.js";

const raiz = document.getElementById("raiz");
let banco, loja;
const filtro = { status: "ativas", busca: "" };

// ------------------------------------------------------------ utilidades
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const reais = (n) => (Number(n) || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const numero = (s) => Number(String(s ?? "").replace(/[^\d,.-]/g, "").replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", ".")) || 0;
const data = (iso) => (iso ? new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "");
const dataHora = (iso) => (iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "");
const tag = (st) => `<span class="tag ${STATUS[st]?.cor || "cinza"}">${esc(STATUS[st]?.nome || st)}</span>`;
const total = (os) => (os.itens || []).reduce((s, i) => s + numero(i.valor), 0);
const linkCliente = (os) => new URL(`cliente.html?t=${os.token}`, location.href).href;
const ACESSORIOS = ["Cabo de força", "Cabo USB", "Fonte", "Tanques com tinta", "Cartuchos", "Caixa"];

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.setAttribute("role", "status");
  t.textContent = msg;
  document.body.append(t);
  setTimeout(() => t.remove(), 2600);
}

function telefoneWhats(w) {
  let d = soDigitos(w);
  if (!d) return "";
  if (d.length <= 11) d = "55" + d;
  return d;
}

function abrirWhats(whatsapp, texto) {
  const n = telefoneWhats(whatsapp);
  const url = `https://wa.me/${n}?text=${encodeURIComponent(texto)}`;
  window.open(url, "_blank", "noopener");
}

function mensagem(os) {
  const nome = (os.cliente_nome || "").split(" ")[0];
  const ap = os.modelo || os.tipo || "aparelho";
  const oi = `Olá${nome ? " " + nome : ""}! Aqui é da ${loja.nome}.`;
  const link = linkCliente(os);
  switch (os.status) {
    case "aprovacao": {
      const itens = (os.itens || []).map((i) => `• ${i.desc}: ${reais(numero(i.valor))}`).join("\n");
      return `${oi}\nO orçamento da sua ${ap} (OS #${os.numero}) está pronto.\n` +
        (os.laudo ? `${os.laudo}\n` : "") + `${itens}\nTotal: ${reais(total(os))}` +
        (os.garantia_dias ? ` · garantia de ${os.garantia_dias} dias` : "") +
        `\n\nAprove ou recuse por aqui: ${link}`;
    }
    case "pronta":
      return `${oi}\nSua ${ap} (OS #${os.numero}) está pronta para retirar!` +
        (total(os) ? ` Valor: ${reais(total(os))}.` : "") +
        (loja.endereco ? `\nEndereço: ${loja.endereco}` : "") + `\nDetalhes: ${link}`;
    case "conserto":
      return `${oi}\nSua ${ap} (OS #${os.numero}) já está em conserto. Acompanhe: ${link}`;
    default:
      return `${oi}\nRecebemos sua ${ap} (OS #${os.numero}). Acompanhe o andamento por aqui: ${link}`;
  }
}

// ------------------------------------------------------------ estrutura
function casca(ativo, html) {
  const it = (h, t) => `<a href="${h}" class="${ativo === h ? "ativo" : ""}">${t}</a>`;
  raiz.innerHTML = `
  <div class="app">
    <nav class="menu" aria-label="Menu principal">
      <div class="marca"><div class="logo" aria-hidden="true">OS</div>
        <div><b>OS 3D</b><small>${esc(loja.nome)}</small></div></div>
      ${it("#/", "Painel")}
      ${it("#/nova", "Nova OS")}
      ${it("#/config", "Minha loja")}
      <div class="rodape">${banco.modo === "demo"
        ? "Modo demonstração: dados só neste navegador."
        : `<button type="button" id="sair">Sair</button>`}</div>
    </nav>
    <main><div class="conteudo">${html}</div></main>
  </div>`;
  $("#sair")?.addEventListener("click", async () => { await banco.sair(); rota(); });
}

// ------------------------------------------------------------ painel
async function painel() {
  const ordens = await banco.listarOS();
  const conta = (st) => ordens.filter((o) => o.status === st).length;
  const kpis = [["orcamento", "Aguardando orçamento"], ["aprovacao", "Aguardando aprovação"],
    ["conserto", "Em conserto"], ["pronta", "Prontas p/ retirar"]];
  const chips = [["ativas", "Em aberto"], ...Object.entries(STATUS).map(([k, v]) => [k, v.nome]), ["todas", "Todas"]];

  casca("#/", `
    <div class="topo">
      <div><h1>Painel</h1><div class="sub">${new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div></div>
      <div class="acoes">
        <label class="sr" for="busca">Buscar</label>
        <input type="search" id="busca" placeholder="Buscar nº, cliente, modelo, série…" value="${esc(filtro.busca)}" style="width:280px">
        <a class="bt prim" href="#/nova">+ Nova OS</a>
      </div>
    </div>
    <div class="kpis">${kpis.map(([k, t]) =>
      `<button type="button" class="kpi" data-st="${k}"><span>${t}</span><b>${conta(k)}</b></button>`).join("")}</div>
    <section class="card" style="padding:0">
      <div class="topo" style="padding:14px 16px">
        <h2 style="margin:0">Ordens de serviço</h2>
        <div class="chips">${chips.map(([k, t]) =>
          `<button type="button" class="chip ${filtro.status === k ? "on" : ""}" data-st="${k}">${esc(t)}</button>`).join("")}</div>
      </div>
      <div class="tabela" id="lista"></div>
    </section>`);

  const desenha = () => {
    const b = filtro.busca.toLowerCase().trim();
    const lista = ordens.filter((o) =>
      (filtro.status === "todas" || (filtro.status === "ativas"
        ? !["entregue", "recusada"].includes(o.status) : o.status === filtro.status)) &&
      (!b || [o.numero, o.cliente_nome, o.cliente_whatsapp, o.modelo, o.serie, o.defeito]
        .some((x) => String(x ?? "").toLowerCase().includes(b))));
    $("#lista").innerHTML = lista.length
      ? `<div class="linha cab"><span>OS</span><span>Cliente</span><span>Aparelho</span><span>Defeito</span><span>Status</span><span>Entrada</span></div>` +
        lista.map((o) => `<a class="linha" href="#/os/${o.id}"><b>#${o.numero}</b><span>${esc(o.cliente_nome)}</span>
          <span>${esc(o.modelo || o.tipo)}</span><span class="sub">${esc(o.defeito)}</span>${tag(o.status)}
          <span class="sub">${data(o.criado_em)}</span></a>`).join("")
      : `<div class="vazio">${ordens.length ? "Nada com esse filtro." : "Nenhuma OS ainda. Clique em <b>+ Nova OS</b>."}</div>`;
  };
  desenha();
  $("#busca").addEventListener("input", (e) => { filtro.busca = e.target.value; desenha(); });
  $$("[data-st]").forEach((b) => b.addEventListener("click", () => { filtro.status = b.dataset.st; painel(); }));
}

// ------------------------------------------------------------ nova OS
async function nova() {
  const tecnicos = (loja.tecnicos || "").split(",").map((s) => s.trim()).filter(Boolean);
  casca("#/nova", `
    <div class="topo"><div><a href="#/" style="text-decoration:none">← Painel</a><h1>Nova OS</h1></div></div>
    <form id="f" class="colunas" autocomplete="off">
      <div class="principal">
        <section class="card">
          <h2>Cliente</h2>
          <div class="grade">
            <label class="campo">WhatsApp<input type="tel" name="whatsapp" placeholder="(21) 9 0000-0000" inputmode="tel"></label>
            <label class="campo">Nome *<input type="text" name="nome" required></label>
          </div>
          <div class="sub" id="cli-info" style="margin-top:8px">Digite o WhatsApp: se já for cliente, o nome aparece sozinho.</div>
        </section>
        <section class="card">
          <h2>Aparelho</h2>
          <div class="grade">
            <label class="campo">Tipo<select name="tipo"><option>Impressora</option><option>Notebook</option><option>Computador</option><option>Celular</option><option>Outro</option></select></label>
            <label class="campo">Marca / modelo *<input type="text" name="modelo" required placeholder="Epson L3250"></label>
            <label class="campo">Nº de série<input type="text" name="serie"></label>
          </div>
          <label class="campo" style="margin-top:14px">Defeito relatado pelo cliente *<textarea name="defeito" rows="3" required></textarea></label>
          <div style="margin-top:12px"><div style="font-size:13px;font-weight:600">Veio junto</div>
            <div class="checks">${ACESSORIOS.map((a) =>
              `<label class="check"><input type="checkbox" name="acessorios" value="${a}"> ${a}</label>`).join("")}</div></div>
        </section>
        <section class="card">
          <h2>Fotos de entrada</h2>
          <div class="sub" style="margin-bottom:10px">Registre riscos, peças quebradas e a etiqueta. Protege a loja.</div>
          <div class="fotos" id="fotos"></div>
        </section>
      </div>
      <div class="lado">
        <section class="card" style="display:flex;flex-direction:column;gap:14px">
          <h2 style="margin:0">Atendimento</h2>
          <label class="campo">Técnico${tecnicos.length
            ? `<select name="tecnico">${tecnicos.map((t) => `<option>${esc(t)}</option>`).join("")}</select>`
            : `<input type="text" name="tecnico">`}</label>
          <label class="campo">Previsão do orçamento<input type="date" name="previsao"></label>
          <label class="campo">Taxa de diagnóstico<input type="text" name="taxa" placeholder="R$ 0,00" inputmode="decimal"></label>
          <button class="bt prim" type="submit" id="salvar">Abrir OS</button>
        </section>
      </div>
    </form>`);

  const fotos = [];
  const f = $("#f");
  const desenhaFotos = () => {
    $("#fotos").innerHTML = fotos.map((b) => `<img src="${URL.createObjectURL(b)}" alt="Foto de entrada">`).join("") +
      `<label class="add"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>
        Tirar / escolher foto<input type="file" accept="image/*" capture="environment" multiple class="sr" id="arq"></label>`;
    $("#arq").addEventListener("change", async (e) => {
      for (const a of e.target.files) fotos.push(await comprimirFoto(a));
      desenhaFotos();
    });
  };
  desenhaFotos();

  f.whatsapp.addEventListener("blur", async () => {
    const c = await banco.buscarCliente(f.whatsapp.value).catch(() => null);
    if (c) {
      f.nome.value = c.nome;
      const anteriores = (await banco.listarOS()).filter((o) => o.cliente_id === c.id);
      $("#cli-info").textContent = `Cliente já cadastrado · ${anteriores.length} OS anterior(es).`;
    }
  });

  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const bt = $("#salvar");
    bt.disabled = true;
    bt.textContent = "Salvando…";
    try {
      const cliente_id = await banco.salvarCliente({ nome: f.nome.value.trim(), whatsapp: f.whatsapp.value });
      let os = await banco.criarOS({
        cliente_id,
        cliente_nome: f.nome.value.trim(),
        cliente_whatsapp: soDigitos(f.whatsapp.value),
        tipo: f.tipo.value,
        modelo: f.modelo.value.trim(),
        serie: f.serie.value.trim(),
        defeito: f.defeito.value.trim(),
        acessorios: $$("input[name=acessorios]:checked", f).map((c) => c.value),
        tecnico: f.tecnico.value.trim(),
        previsao: f.previsao.value || null,
        taxa: f.taxa.value.trim(),
      });
      if (fotos.length) {
        const urls = [];
        for (const b of fotos) urls.push(await banco.enviarFoto(os.id, b));
        os = await banco.atualizarOS(os.id, { fotos: urls });
      }
      toast(`OS #${os.numero} aberta`);
      location.hash = `#/os/${os.id}`;
    } catch (err) {
      alert("Não consegui salvar: " + err.message);
      bt.disabled = false;
      bt.textContent = "Abrir OS";
    }
  });
}

// ------------------------------------------------------------ detalhe
async function detalhe(id) {
  let os = await banco.obterOS(id);
  if (!os) { casca("", `<div class="vazio">OS não encontrada. <a href="#/">Voltar</a></div>`); return; }
  const itens = (os.itens || []).map((i) => ({ ...i }));

  casca("", `
    <div class="topo nao-imprimir">
      <div>
        <a href="#/" style="text-decoration:none">← Painel</a>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><h1>OS #${os.numero} · ${esc(os.modelo || os.tipo)}</h1>${tag(os.status)}</div>
        <div class="sub">${esc(os.cliente_nome)}${os.cliente_whatsapp ? " · " + esc(os.cliente_whatsapp) : ""} · entrada ${dataHora(os.criado_em)}${os.tecnico ? " · técnico " + esc(os.tecnico) : ""}</div>
      </div>
      <div class="acoes">
        <a class="bt" href="#/imprimir/${os.id}">Imprimir via</a>
        ${os.status === "pronta" ? `<button class="bt prim" type="button" data-ir="entregue">Entregar ao cliente</button>` : ""}
        ${os.status === "conserto" ? `<button class="bt prim" type="button" data-ir="pronta">Marcar como pronta</button>` : ""}
      </div>
    </div>
    <div class="colunas">
      <div class="principal">
        <section class="card">
          <h2>Entrada</h2>
          <div class="grade" style="font-size:14px">
            <div><div class="sub">Defeito relatado</div>${esc(os.defeito)}</div>
            <div><div class="sub">Nº de série</div>${esc(os.serie) || "—"}</div>
            <div><div class="sub">Veio junto</div>${esc((os.acessorios || []).join(", ")) || "—"}</div>
            <div><div class="sub">Taxa de diagnóstico</div>${esc(os.taxa) || "—"}</div>
          </div>
          <div class="fotos" style="margin-top:14px" id="fotos"></div>
        </section>
        <section class="card">
          <h2>Diagnóstico e orçamento</h2>
          <label class="campo">Laudo do técnico<textarea id="laudo" rows="3" placeholder="Ex.: Almofada de tinta saturada. Trocar almofada e zerar o contador.">${esc(os.laudo)}</textarea></label>
          <div style="margin-top:14px" id="itens"></div>
          <div class="acoes" style="margin-top:4px"><button class="bt peq" type="button" id="add-item">+ Serviço / peça</button></div>
          <div class="total"><span>Total</span><span id="tot"></span></div>
          <div class="grade" style="margin-top:14px">
            <label class="campo">Garantia (dias)<input type="text" id="garantia" inputmode="numeric" value="${esc(os.garantia_dias ?? 90)}"></label>
            <label class="campo">Status<select id="status">${Object.entries(STATUS).map(([k, v]) =>
              `<option value="${k}" ${k === os.status ? "selected" : ""}>${v.nome}</option>`).join("")}</select></label>
          </div>
          <div class="acoes" style="margin-top:16px">
            <button class="bt" type="button" id="salvar">Salvar</button>
            ${["orcamento", "aprovacao"].includes(os.status)
              ? `<button class="bt prim" type="button" id="enviar-orc">Salvar e enviar orçamento no WhatsApp</button>` : ""}
          </div>
        </section>
      </div>
      <div class="lado">
        <section class="card">
          <h2>Mensagem para o cliente</h2>
          <div class="msg" id="msg"></div>
          <div class="acoes" style="margin-top:12px">
            <button class="bt zap" type="button" id="zap" ${os.cliente_whatsapp ? "" : "disabled"}>Enviar no WhatsApp</button>
            <button class="bt peq" type="button" id="copiar">Copiar link do cliente</button>
          </div>
          ${os.cliente_whatsapp ? "" : `<div class="sub" style="margin-top:8px">Cliente sem WhatsApp cadastrado.</div>`}
        </section>
        <section class="card">
          <h2>Andamento</h2>
          <div class="tempo">${(os.eventos || []).slice().reverse().map((ev) =>
            `<div><i aria-hidden="true"></i><span>${esc(ev.texto)}<small>${dataHora(ev.em)}</small></span></div>`).join("")}</div>
        </section>
      </div>
    </div>`);

  const desenhaFotos = () => {
    $("#fotos").innerHTML = (os.fotos || []).map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener"><img src="${esc(u)}" alt="Foto da OS"></a>`).join("") +
      `<label class="add">+ Foto<input type="file" accept="image/*" capture="environment" multiple class="sr" id="arq"></label>`;
    $("#arq").addEventListener("change", async (e) => {
      const urls = [...(os.fotos || [])];
      for (const a of e.target.files) urls.push(await banco.enviarFoto(os.id, await comprimirFoto(a)));
      os = await banco.atualizarOS(os.id, { fotos: urls });
      desenhaFotos();
    });
  };
  desenhaFotos();

  const msg = () => { $("#msg").textContent = mensagem({ ...os, itens, laudo: $("#laudo").value }); };
  const desenhaItens = () => {
    $("#itens").innerHTML = itens.map((i, n) => `
      <div class="item">
        <input type="text" aria-label="Descrição" placeholder="Serviço ou peça" data-n="${n}" data-c="desc" value="${esc(i.desc)}">
        <input type="text" aria-label="Valor" placeholder="R$ 0,00" inputmode="decimal" data-n="${n}" data-c="valor" value="${esc(i.valor)}">
        <button class="bt peq" type="button" aria-label="Remover" data-del="${n}">✕</button>
      </div>`).join("");
    $("#tot").textContent = reais(total({ itens }));
    $$("#itens input").forEach((inp) => inp.addEventListener("input", () => {
      itens[inp.dataset.n][inp.dataset.c] = inp.value;
      $("#tot").textContent = reais(total({ itens }));
      msg();
    }));
    $$("#itens [data-del]").forEach((b) => b.addEventListener("click", () => { itens.splice(b.dataset.del, 1); desenhaItens(); msg(); }));
  };
  if (!itens.length) itens.push({ desc: "", valor: "" });
  desenhaItens();
  msg();
  $("#laudo").addEventListener("input", msg);
  $("#add-item").addEventListener("click", () => { itens.push({ desc: "", valor: "" }); desenhaItens(); });

  const salvar = async (novoStatus) => {
    const st = novoStatus || $("#status").value;
    const ev = [...(os.eventos || [])];
    if (st !== os.status) ev.push({ em: new Date().toISOString(), texto: STATUS[st].nome });
    os = await banco.atualizarOS(os.id, {
      laudo: $("#laudo").value.trim(),
      itens: itens.filter((i) => i.desc.trim() || numero(i.valor)),
      garantia_dias: parseInt($("#garantia").value, 10) || 0,
      status: st,
      eventos: ev,
    });
    return os;
  };

  $("#salvar").addEventListener("click", async () => { await salvar(); toast("Salvo"); detalhe(os.id); });
  $("#enviar-orc")?.addEventListener("click", async () => {
    if (!itens.some((i) => i.desc.trim())) { alert("Coloque pelo menos um serviço ou peça no orçamento."); return; }
    await salvar("aprovacao");
    if (os.cliente_whatsapp) abrirWhats(os.cliente_whatsapp, mensagem(os));
    else toast("Salvo. Cliente sem WhatsApp: copie o link.");
    detalhe(os.id);
  });
  $$("[data-ir]").forEach((b) => b.addEventListener("click", async () => {
    await salvar(b.dataset.ir);
    if (b.dataset.ir === "pronta" && os.cliente_whatsapp && confirm("Avisar o cliente no WhatsApp que está pronta?"))
      abrirWhats(os.cliente_whatsapp, mensagem(os));
    detalhe(os.id);
  }));
  $("#zap").addEventListener("click", () => abrirWhats(os.cliente_whatsapp, $("#msg").textContent));
  $("#copiar").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(linkCliente(os)); toast("Link copiado"); }
    catch { prompt("Copie o link:", linkCliente(os)); }
  });
}

// ------------------------------------------------------------ via impressa
async function imprimir(id) {
  const os = await banco.obterOS(id);
  if (!os) { location.hash = "#/"; return; }
  const via = (quem) => `
    <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
      <div><h1>${esc(loja.nome)}</h1><div>${esc(loja.endereco)}</div><div>${loja.whatsapp ? "WhatsApp " + esc(loja.whatsapp) : ""}</div></div>
      <div style="text-align:right"><b style="font-size:18px">OS #${os.numero}</b><div>${dataHora(os.criado_em)}</div><div>${quem}</div></div>
    </div>
    <table>
      <tr><th style="width:25%">Cliente</th><td>${esc(os.cliente_nome)} ${os.cliente_whatsapp ? "· " + esc(os.cliente_whatsapp) : ""}</td></tr>
      <tr><th>Aparelho</th><td>${esc(os.tipo)} · ${esc(os.modelo)} ${os.serie ? "· série " + esc(os.serie) : ""}</td></tr>
      <tr><th>Defeito relatado</th><td>${esc(os.defeito)}</td></tr>
      <tr><th>Veio junto</th><td>${esc((os.acessorios || []).join(", ")) || "Nada"}</td></tr>
      ${os.taxa ? `<tr><th>Taxa de diagnóstico</th><td>${esc(os.taxa)}</td></tr>` : ""}
      ${os.laudo ? `<tr><th>Laudo</th><td>${esc(os.laudo)}</td></tr>` : ""}
      ${(os.itens || []).length ? `<tr><th>Orçamento</th><td>${os.itens.map((i) => `${esc(i.desc)}: ${reais(numero(i.valor))}`).join("<br>")}<br><b>Total: ${reais(total(os))}</b></td></tr>` : ""}
      ${os.garantia_dias ? `<tr><th>Garantia</th><td>${os.garantia_dias} dias após a entrega</td></tr>` : ""}
    </table>
    <div style="font-size:11px">${esc(loja.termos)}</div>
    <div style="font-size:11px;margin-top:4px">Acompanhe pelo celular: ${esc(linkCliente(os))}</div>
    <div class="ass"><div>Cliente</div><div>${esc(loja.nome)}</div></div>`;
  casca("", `
    <div class="acoes nao-imprimir"><a class="bt" href="#/os/${os.id}">← Voltar</a><button class="bt prim" type="button" id="imp">Imprimir</button></div>
    <div class="via">${via("Via do cliente")}<hr>${via("Via da loja")}</div>`);
  $("#imp").addEventListener("click", () => window.print());
}

// ------------------------------------------------------------ configurações
async function config() {
  casca("#/config", `
    <div class="topo"><h1>Minha loja</h1></div>
    ${banco.modo === "demo" ? `<div class="aviso">Você está no <b>modo demonstração</b>: as OS ficam só neste navegador e o link do cliente só abre aqui. Para usar de verdade (PC e celular juntos), siga o LEIA-ME para ligar o banco na nuvem.</div>` : ""}
    <form class="card" id="f" style="display:flex;flex-direction:column;gap:14px;max-width:720px">
      <div class="grade">
        <label class="campo">Nome da loja<input type="text" name="nome" value="${esc(loja.nome)}"></label>
        <label class="campo">WhatsApp da loja<input type="tel" name="whatsapp" value="${esc(loja.whatsapp)}"></label>
      </div>
      <label class="campo">Endereço<input type="text" name="endereco" value="${esc(loja.endereco)}"></label>
      <label class="campo">Técnicos (separados por vírgula)<input type="text" name="tecnicos" value="${esc(loja.tecnicos)}" placeholder="Luan, João"></label>
      <label class="campo">Termos que saem na via impressa<textarea name="termos" rows="4">${esc(loja.termos)}</textarea></label>
      <div><button class="bt prim" type="submit">Salvar</button></div>
    </form>`);
  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    await banco.salvarLoja({ nome: f.nome.value.trim(), whatsapp: f.whatsapp.value.trim(),
      endereco: f.endereco.value.trim(), tecnicos: f.tecnicos.value.trim(), termos: f.termos.value.trim() });
    loja = await banco.loja();
    toast("Dados da loja salvos");
    config();
  });
}

// ------------------------------------------------------------ login (nuvem)
function telaLogin() {
  raiz.innerHTML = `
  <div class="login"><form class="card" id="f">
    <div><h1>OS 3D</h1><div class="sub">Ordens de serviço da assistência</div></div>
    <label class="campo">E-mail<input type="email" name="email" required autocomplete="username"></label>
    <label class="campo">Senha<input type="password" name="senha" required minlength="6" autocomplete="current-password"></label>
    <button class="bt prim" type="submit">Entrar</button>
    <button class="bt" type="button" id="criar">Criar conta</button>
    <div class="sub" id="info"></div>
  </form></div>`;
  const f = $("#f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await banco.entrar(f.email.value, f.senha.value); rota(); }
    catch (err) { $("#info").textContent = "Não entrou: " + err.message; }
  });
  $("#criar").addEventListener("click", async () => {
    if (!f.reportValidity()) return;
    try {
      await banco.cadastrar(f.email.value, f.senha.value);
      $("#info").textContent = "Conta criada. Se pedir, confirme pelo e-mail e depois clique em Entrar.";
      if (await banco.sessao()) rota();
    } catch (err) { $("#info").textContent = "Erro: " + err.message; }
  });
}

// ------------------------------------------------------------ rotas
async function rota() {
  try {
    if (!(await banco.sessao())) return telaLogin();
    loja = await banco.loja();
    if (!loja) {
      await banco.garantirLoja();
      loja = await banco.loja();
    }
    const h = location.hash || "#/";
    let m;
    if ((m = h.match(/^#\/os\/(.+)$/))) return await detalhe(m[1]);
    if ((m = h.match(/^#\/imprimir\/(.+)$/))) return await imprimir(m[1]);
    if (h === "#/nova") return await nova();
    if (h === "#/config") return await config();
    return await painel();
  } catch (err) {
    console.error(err);
    raiz.innerHTML = `<div class="vazio">Erro: ${esc(err.message)}<br><button class="bt" type="button" onclick="location.reload()">Tentar de novo</button></div>`;
  }
}

window.addEventListener("hashchange", () => { rota(); window.scrollTo(0, 0); });
banco = await criarBanco();
rota();
