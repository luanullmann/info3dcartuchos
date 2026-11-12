// Gera o "Pix copia e cola" (BR Code estático, padrão do Banco Central).
// Não passa por nenhuma empresa: o dinheiro cai direto na chave da loja.

function campo(id, valor) {
  return id + String(valor.length).padStart(2, "0") + valor;
}

// CRC16-CCITT (polinômio 0x1021, início 0xFFFF), exigido no fim do código
export function crc16(txt) {
  let crc = 0xffff;
  for (const b of new TextEncoder().encode(txt)) {
    crc ^= b << 8;
    for (let i = 0; i < 8; i++) crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
  }
  return crc.toString(16).toUpperCase().padStart(4, "0");
}

function semAcento(s, max) {
  return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Za-z0-9 ]/g, " ").replace(/\s+/g, " ").trim().toUpperCase().slice(0, max);
}

export function normalizarChave(chave, tipo) {
  const c = (chave || "").trim();
  const dig = c.replace(/\D/g, "");
  switch (tipo) {
    case "cpf":
    case "cnpj":
      return dig;
    case "telefone":
      return "+" + (dig.length <= 11 ? "55" + dig : dig);
    case "email":
      return c.toLowerCase();
    default:
      return c; // chave aleatória
  }
}

export function pixCopiaECola({ chave, tipo, nome, cidade, valor, txid }) {
  const k = normalizarChave(chave, tipo);
  if (!k) throw new Error("Chave Pix não cadastrada");
  const conta = campo("00", "br.gov.bcb.pix") + campo("01", k);
  const id = (txid || "").replace(/[^A-Za-z0-9]/g, "").slice(0, 25) || "***";
  let p =
    campo("00", "01") +
    campo("26", conta) +
    campo("52", "0000") +
    campo("53", "986") +
    (valor > 0 ? campo("54", valor.toFixed(2)) : "") +
    campo("58", "BR") +
    campo("59", semAcento(nome, 25) || "RECEBEDOR") +
    campo("60", semAcento(cidade, 15) || "BRASIL") +
    campo("62", campo("05", id)) +
    "6304";
  return p + crc16(p);
}
