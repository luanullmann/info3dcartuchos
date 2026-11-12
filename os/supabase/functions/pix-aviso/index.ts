// Recebe o aviso (webhook) do PagBank quando o Pix muda de situação.
// Não confia no conteúdo do aviso: consulta o pedido direto no PagBank com o token da loja.
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


Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  try {
    const corpo = await req.json().catch(() => ({}));
    const pedidoId: string = corpo?.id || "";
    if (!/^ORDE_[A-Za-z0-9-]+$/.test(pedidoId)) return json({ ok: true, ignorado: "sem pedido" });

    const { data: os } = await db.from("ordens").select("*").eq("pix_pedido_id", pedidoId).maybeSingle();
    if (!os) return json({ ok: true, ignorado: "pedido desconhecido" });
    if (os.pago) return json({ ok: true, ja_pago: true });

    const pedido = await pagbank(`/orders/${pedidoId}`);
    if (pedido.reference_id !== os.id || !pedidoPago(pedido)) return json({ ok: true, pago: false });

    const valor = (os.itens || []).reduce((s: number, i: { valor?: string }) => s + numero(i.valor), 0);
    const agora = new Date().toISOString();
    const eventos = [...(os.eventos || []), {
      em: agora,
      texto: `Pix confirmado pelo PagBank (${valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })})`,
    }];
    await db.from("ordens").update({
      pago: true, pago_em: agora, pagamento_informado: true, atualizado_em: agora, eventos,
    }).eq("id", os.id).eq("pago", false);
    return json({ ok: true, pago: true });
  } catch (e) {
    console.error(e);
    // 500 faz o PagBank tentar avisar de novo mais tarde
    return json({ erro: String((e as Error).message || e) }, 500);
  }
});
