import json
import logging

from openai import OpenAI

# Sentry: ID de conversa por sinal (agrupa spans em Conversas) + logging estruturado.
try:
    from sentry_config import set_ai_conversation_id, get_logger
except Exception:
    def set_ai_conversation_id(_conv_id):  # noqa: E305
        pass
    get_logger = None

log = get_logger(__name__) if get_logger else None

# Configuração do cliente para usar o LiteLLM Proxy local
# O LiteLLM Proxy deve estar rodando na porta 4000
# A chave "anything" é apenas um placeholder exigido pelo SDK local;
# nenhuma credencial real é enviada para localhost.
client = OpenAI(api_key="anything", base_url="http://localhost:4000")  # noqa: S106 - placeholder local


def validate_signal(symbol: str, signal: str, confidence: float, price: float) -> dict:
    """
    Valida um sinal de trading usando LLM via LiteLLM Proxy (Ollama).
    Retorna um dicionário com a decisão da IA.
    """
    try:
        prompt = f"""
        Você é um analista expert em trading quantitativo.
        O modelo de Machine Learning gerou o seguinte sinal para execução:
        Símbolo: {symbol}
        Sinal Sugerido: {signal}
        Confiança do Modelo: {confidence:.2f}
        Preço de Entrada: {price}

        Avalie se este sinal deve ser executado considerando que sinais com confiança abaixo de 0.65
        são considerados de alto risco a menos que a tendência seja muito clara.

        Responda estritamente em formato JSON:
        {{
            "valid": true/false,
            "reason": "breve explicação em português",
            "ai_confidence": 0.0 a 1.0
        }}
        """

        # Sentry: agrupa spans desta validacao em Conversas (gen_ai.conversation.id).
        set_ai_conversation_id(f"signal:{symbol}:{signal}:{confidence:.2f}")

        response = client.chat.completions.create(
            model="ollama/deepseek-v4-flash:cloud",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente de trading que valida sinais. Responda apenas em JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        if content is None:
            return {
                "valid": True,
                "reason": "Resposta vazia da IA",
                "ai_confidence": 0.5,
            }
        # Limpeza básica caso o modelo retorne markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        if log:
            log.info("sinal validado pela IA",
                     extra={"symbol": symbol, "signal": signal,
                            "confidence": round(confidence, 4),
                            "ai_valid": result.get("valid"),
                            "ai_confidence": result.get("ai_confidence")})
        return result
    except Exception as e:
        if log:
            log.error("erro na validacao IA", extra={"symbol": symbol,
                                                      "error": str(e)}, exc_info=True)
        return {
            "valid": True,
            "reason": "Validação automática ignorada devido a erro técnico",
            "ai_confidence": 0.5,
        }


if __name__ == "__main__":
    # Teste de funcionalidade
    print("Testando validação de sinal...")
    print(validate_signal("GOLD#", "BUY", 0.72, 2385.50))
