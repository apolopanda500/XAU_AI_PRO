import dotenv from 'dotenv';
import { Sandbox } from '@vercel/sandbox';

// Carrega o .env.local
dotenv.config({ path: './.env.local', override: true });

// Força a leitura do token
if (!process.env.VERCEL_OIDC_TOKEN) {
  console.error('ERRO: VERCEL_OIDC_TOKEN nao encontrado no ambiente.');
  process.exit(1);
} else {
  console.log('Token OIDC carregado com sucesso.');
}

const sandbox = await Sandbox.getOrCreate({
  name: "my-sandbox-435823",
  persistent: true,
  networkPolicy: 'deny-all',
});

await sandbox.update({ networkPolicy: 'deny-all' });

try {
  await sandbox.writeFiles([
    {
      path: '/vercel/generated.mjs',
      content: "console.log('Hello from generated code')",
    },
  ]);

  const result = await sandbox.runCommand('node', [
    '/vercel/generated.mjs',
  ]);
  console.log(await result.stdout());

  if (result.exitCode !== 0) {
    console.error(await result.stderr());
  }
} finally {
  await sandbox.stop();
}