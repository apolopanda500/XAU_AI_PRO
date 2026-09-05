import dotenv from 'dotenv';
import { Sandbox } from '@vercel/sandbox';

dotenv.config({ path: './.env.local', override: true });

if (!process.env.VERCEL_OIDC_TOKEN) {
  console.error('ERRO: VERCEL_OIDC_TOKEN nao encontrado.');
  process.exit(1);
}
console.log('Token OIDC carregado.');

// Cria/retoma sandbox com allow-all (necessario p/ auth do Claude)
const sandbox = await Sandbox.getOrCreate({
  name: "my-sandbox-448760",
  persistent: true,
  networkPolicy: 'allow-all',
});

await sandbox.update({ networkPolicy: 'allow-all' });

console.log('Sandbox inicializado.');

try {
  // Verificar se Claude Code ja esta instalado
  console.log('Verificando Claude Code...');
  const check = await sandbox.runCommand('bash', ['-lc', 'which claude && claude --version']);
  const checkOut = await check.stdout();
  const checkErr = await check.stderr();
  console.log('--- Check stdout ---');
  console.log(checkOut);
  if (checkErr) console.error('--- Check stderr ---\n' + checkErr);
  console.log('Exit code:', check.exitCode);

  if (check.exitCode !== 0) {
    console.log('\nInstalando Claude Code...');
    const install = await sandbox.runCommand('bash', ['-lc', 'npm install -g @anthropic-ai/claude-code']);
    const installOut = await install.stdout();
    const installErr = await install.stderr();
    console.log('--- Install stdout ---');
    console.log(installOut);
    if (installErr) console.error('--- Install stderr ---\n' + installErr);
    console.log('Exit code:', install.exitCode);

    if (install.exitCode !== 0) {
      throw new Error('Falha ao instalar Claude Code');
    }
  }

  // Verificar versao instalada
  console.log('\nVerificando versao do Claude...');
  const version = await sandbox.runCommand('bash', ['-lc', 'claude --version']);
  console.log(await version.stdout());

  console.log('');

} finally {
}