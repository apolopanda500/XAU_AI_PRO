import { streamText } from 'ai';
import dotenv from 'dotenv';

dotenv.config({ path: './.env.local', override: true });

async function main() {
  const result = streamText({
    model: 'openai/gpt-5.6-sol',
    prompt: 'Invent a new holiday and describe its traditions.',
  });

  for await (const textPart of result.textStream) {
    process.stdout.write(textPart);
  }

  console.log();
  console.log('Token usage:', await result.usage);
}

main().catch(console.error);