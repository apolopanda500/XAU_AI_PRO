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

try {
  console.log(`Sandbox inicializado (id: ${sandbox.id}).`);

  // 1) Instalar Claude Code (versao mais recente)
  console.log('Instalando Claude Code...');
  const install = await sandbox.runCommand('bash', [
    '-lc',
    'npm install -g @anthropic-ai/claude-code',
  ]);
  const installOut = await install.stdout();
  const installErr = await install.stderr();
  console.log('--- Install stdout ---');
  console.log(installOut);
  if (installErr) console.error('--- Install stderr ---\n' + installErr);
  console.log('Exit code:', install.exitCode);

  if (install.exitCode !== 0) {
    throw new Error('Falha ao instalar Claude Code');
  }

  // 2) Verificar versao instalada
  console.log('\nVerificando versao do Claude...');
  const version = await sandbox.runCommand('bash', ['-lc', 'claude --version']);
  console.log(await version.stdout());

  // 3) Rodar Claude em modo nao-interativo para mostrar instrucoes de login
  console.log('\nClaude instalado com sucesso!');
  console.log('\n==============================================');
  console.log('  CLAUDE CODE INSTALADO NO SANDBOX');
  console.log('==============================================');
  console.log('');
  console.log('Para usar o Claude interativamente, voce precisa:');
  console.log('');
  console.log('  1. Conectar ao sandbox:');
  console.log('    npx sandbox ssh my-sandbox-448760 --scope apolopanda500 --project xau-ai-pro-api');
  console.log('');
  console.log('  2. Rodar Claude:');
  console.log('    claude');
  console.log('');
  console.log('  3. No primeiro uso, o Claude abre o navegador para');
  console.log('     autenticacao. Como estamos em um container, use:');
  console.log('     pressione [c] para copiar a URL de login');
  console.log('     cole no navegador e complete o login');
  console.log('');
  console.log('  4. Apos autenticar, o Claude abre o prompt e voce');
  console.log('     pode digitar sua primeira pergunta.');
  console.log('');
  console.log('  5. Para deslogar quando terminar:');
  console.log('     claude auth logout');
  console.log('     exit');
  console.log('');
  console.log('  6. Para parar o sandbox localmente:');
  console.log('    npx sandbox stop "my-sandbox-448760" --scope apolopanda500 --project xau-ai-pro-api');
  console.log('');

} finally {
  // NAO para o sandbox aqui - queremos que ele continue rodando
  // para voce se conectar via SSH depois.
  console.log('\nSandbox mantido ATIVO para conectividade externa.');
  console.log('Para parar: stop my-sandbox-448760 (quando terminar).');
}