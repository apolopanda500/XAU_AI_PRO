import json
import logging

from openai import OpenAI

# Configuração do cliente para usar o LiteLLM Proxy local
# O LiteLLM Proxy deve estar rodando na porta 4000
client = OpenAI(api_key="anything", base_url="http://localhost:4000")


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
        return result
    except Exception as e:
        logging.error(f"Erro na validação IA: {e}")
        return {
            "valid": True,
            "reason": "Validação automática ignorada devido a erro técnico",
            "ai_confidence": 0.5,
        }


if __name__ == "__main__":
    # Teste de funcionalidade
    print("Testando validação de sinal...")
    print(validate_signal("GOLD#", "BUY", 0.72, 2385.50))
