import 'dotenv/config'
import { streamText } from 'ai'

async function main() {
  if (!process.env.AI_GATEWAY_API_KEY) {
    throw new Error(
      'AI_GATEWAY_API_KEY não está configurada. Adicione-a em .env.local ou nas Vars do projeto.',
    )
  }

  const result = streamText({
    model: 'openai/gpt-5.6-sol',
    prompt: 'Explique em uma frase por que o gerenciamento de risco é importante no trading.',
  })

  for await (const textPart of result.textStream) {
    process.stdout.write(textPart)
  }

  const usage = await result.usage
  process.stdout.write('\n\nUso de tokens:\n')
  console.log({
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    totalTokens: usage.totalTokens,
  })
}

main().catch((error: unknown) => {
  console.error('Falha na geração:', error)
  process.exitCode = 1
})
