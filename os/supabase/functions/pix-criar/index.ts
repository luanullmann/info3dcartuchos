// Gera (ou reaproveita) o Pix do PagBank de uma OS. Chamada pela página do cliente.
// Entrada: { t: token_da_os, nome, cpf }
// (arquivo completo: já inclui o código comum, pode colar direto no painel do Supabase)
// Código comum das funções de Pix do PagBank (Supabase Edge Functions / Deno).
import { createClient } from "jsr:@supabase/supabase-js@2";

export const PAGBANK =
  (Deno.env.get("PAGBANK_AMBIENTE") || "sandbox") === "producao"
    ? "https://api.pagseguro.com"
    : "https://sandbox.api.pagseguro.com";

export const TOKEN = Deno.env.get("PAGBANK_TOKEN") || "";
// domínio usado no e-mail técnico do pedido (o PagBank exige um e-mail do comprador)
export const DOMINIO = Deno.env.get("PAGBANK_EMAIL_DOMINIO") || "info3dcartuchos.com.br";

// data no formato que o PagBank usa, no horário de Brasília (-03:00)
export function dataBrasilia(ms: number) {
  return new Date(ms - 3 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "-03:00");
}

// service role: só existe aqui no servidor, nunca vai para o navegador
export const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

export function json(corpo: unknown, status = 200) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

export async function pagbank(caminho: string, opcoes: RequestInit = {}) {
  const r = await fetch(PAGBANK + caminho, {
    ...opcoes,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(opcoes.headers || {}),
    },
  });
  const texto = await r.text();
  let corpo: any;
  try { corpo = JSON.parse(texto); } catch { corpo = { bruto: texto }; }
  if (!r.ok) {
    const msg = corpo?.error_messages?.map((e: any) => `${e.parameter_name || ""} ${e.description || e.code}`).join("; ")
      || texto.slice(0, 300);
    throw new Error(`PagBank ${r.status}: ${msg}`);
  }
  return corpo;
}

export function numero(s: unknown) {
  return Number(String(s ?? "").replace(/[^\d,.-]/g, "").replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", ".")) || 0;
}

export function totalCentavos(itens: { valor?: string }[]) {
  return Math.round((itens || []).reduce((s, i) => s + numero(i.valor), 0) * 100);
}

// O pedido foi pago? Confere de várias formas porque o PagBank tem dois formatos de pedido Pix.
export function pedidoPago(pedido: any) {
  return (pedido?.charges || []).some((c: any) => c.status === "PAID");
}

export function textoPix(pedido: any) {
  return pedido?.qr_codes?.[0]?.text || pedido?.charges?.[0]?.qr_code?.text || "";
}

export function imagemPix(pedido: any) {
  const links = pedido?.qr_codes?.[0]?.links || pedido?.charges?.[0]?.links || [];
  return links.find((l: any) => l.rel === "QRCODE.PNG")?.href || "";
}


function cpfValido(c: string) {
  if (!/^\d{11}$/.test(c) || /^(\d)\1{10}$/.test(c)) return false;
  const dv = (n: number) => {
    let s = 0;
    for (let i = 0; i < n; i++) s += Number(c[i]) * (n + 1 - i);
    const r = (s * 10) % 11;
    return r === 10 ? 0 : r;
  };
  return dv(9) === Number(c[9]) && dv(10) === Number(c[10]);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  try {
    if (!TOKEN) return json({ erro: "PagBank não configurado" }, 500);
    const { t, nome, cpf } = await req.json();
    const doc = String(cpf || "").replace(/\D/g, "");
    if (!t) return json({ erro: "Link inválido" }, 400);
    if (!cpfValido(doc)) return json({ erro: "CPF inválido" }, 400);

    const { data: os } = await db.from("ordens").select("*").eq("token", t).maybeSingle();
    if (!os) return json({ erro: "OS não encontrada" }, 404);
    if (os.pago) return json({ pago: true });
    if (!["conserto", "pronta", "entregue"].includes(os.status)) {
      return json({ erro: "O orçamento ainda não foi aprovado" }, 400);
    }
    const centavos = totalCentavos(os.itens);
    if (centavos < 100) return json({ erro: "Valor inválido" }, 400);

    // Já existe Pix válido com o mesmo valor? Reaproveita.
    const agora = Date.now();
    if (os.pix_pedido_id && os.pix_texto && os.pix_valor === centavos &&
        os.pix_expira && new Date(os.pix_expira).getTime() - agora > 5 * 60 * 1000) {
      return json({ texto: os.pix_texto, imagem: os.pix_imagem, expira: os.pix_expira, valor: centavos });
    }

    const expira = dataBrasilia(agora + 24 * 60 * 60 * 1000);
    const pedido = await pagbank("/orders", {
      method: "POST",
      body: JSON.stringify({
        reference_id: os.id,
        customer: {
          name: String(nome || os.cliente_nome || "Cliente").slice(0, 60),
          email: `os${os.numero}.${os.token.slice(0, 6)}@${DOMINIO}`,
          tax_id: doc,
        },
        items: [{ reference_id: `OS${os.numero}`, name: `OS ${os.numero} - ${os.modelo || os.tipo || "servico"}`.slice(0, 64), quantity: 1, unit_amount: centavos }],
        qr_codes: [{ amount: { value: centavos }, expiration_date: expira }],
        notification_urls: [`${Deno.env.get("SUPABASE_URL")}/functions/v1/pix-aviso`],
      }),
    });

    if (pedidoPago(pedido)) return json({ pago: true });
    const texto = textoPix(pedido);
    if (!texto) throw new Error("O PagBank não devolveu o código Pix");
    const imagem = imagemPix(pedido);
    await db.from("ordens").update({
      pix_pedido_id: pedido.id, pix_texto: texto, pix_imagem: imagem,
      pix_expira: new Date(agora + 24 * 60 * 60 * 1000).toISOString(), pix_valor: centavos,
    }).eq("id", os.id);
    return json({ texto, imagem, valor: centavos });
  } catch (e) {
    console.error(e);
    return json({ erro: String((e as Error).message || e) }, 500);
  }
});
