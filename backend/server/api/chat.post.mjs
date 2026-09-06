const gatewayUrl = "https://ai-gateway.vercel.sh/v1/chat/completions";
const defaultModel = "openai/gpt-5.6-sol";

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const message = String(body?.message || "").trim();
  const model = String(body?.model || defaultModel).trim();
  const apiKey = process.env.AI_GATEWAY_API_KEY || process.env.VERCEL_OIDC_TOKEN;

  if (!message) {
    throw createError({ statusCode: 400, statusMessage: "message e obrigatoria" });
  }
  if (!apiKey) {
    throw createError({ statusCode: 503, statusMessage: "AI Gateway nao configurado" });
  }

  const response = await fetch(gatewayUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [{ role: "system", content: "Voce e o assistente XAU AI PRO. Nao execute ordens; responda com analise e riscos." },
                 { role: "user", content: message }],
      stream: false,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw createError({ statusCode: response.status, statusMessage: payload?.error?.message || "Falha no AI Gateway" });
  }
  return { model, reply: payload?.choices?.[0]?.message?.content || "", usage: payload?.usage || null };
});
