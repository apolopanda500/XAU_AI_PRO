import 'dotenv/config';
import { streamText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';

// Vercel AI Gateway — modelo 'openai/gpt-5.6-sol' via API key do gateway.
const gateway = createOpenAI({
  apiKey: process.env.AI_GATEWAY_API_KEY || '',
  baseURL: 'https://ai-gateway.vercel.sh/v1',
});

const result = streamText({
  model: gateway('openai/gpt-5.6-sol'),
  prompt: 'Responda em uma frase: quem é você?',
});

let full = '';
try {
  for await (const chunk of result.textStream) {
    full += chunk;
    process.stdout.write(chunk);
  }
  console.log('\n\n[usage]', JSON.stringify(await result.usage));
} catch (err) {
  console.error('\n[erro]', err.constructor?.name || err.name, err.message || err);
  const st = await result.textStream;
  console.error('status:', st);
  process.exitCode = 1;
}