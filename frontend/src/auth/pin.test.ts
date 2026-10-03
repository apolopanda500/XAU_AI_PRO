// Testes do PIN local (PBKDF2 no webview, gravacao pelo shell Tauri).
//
// O bug corrigido aqui: desativar o PIN usava validarPin(), que so checa o
// formato. Qualquer sequencia de 4 a 8 digitos desligava a protecao. A
// desativacao e a troca agora exigem verificarPin(), que compara o hash.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({ invoke: (...args: unknown[]) => invoke(...args) }));

const { validarPin, definirPin, verificarPin, removerPin, ITERACOES } = await import('./auth');

beforeEach(() => {
  invoke.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('validarPin', () => {
  it('aceita de 4 a 8 digitos', () => {
    expect(validarPin('1234')).toBeNull();
    expect(validarPin('12345678')).toBeNull();
  });

  it('recusa formato invalido', () => {
    expect(validarPin('123')).toBeTruthy();
    expect(validarPin('123456789')).toBeTruthy();
    expect(validarPin('12a4')).toBeTruthy();
    expect(validarPin('')).toBeTruthy();
  });
});

describe('definirPin', () => {
  it('grava salt, hash e 150k iteracoes, sem o PIN em claro', async () => {
    invoke.mockResolvedValue(null);
    await definirPin('4321');
    const [cmd, args] = invoke.mock.calls[0] as unknown as [string, { payload: Record<string, unknown> }];
    expect(cmd).toBe('save_auth');
    expect(args.payload.iterations).toBe(ITERACOES);
    expect(args.payload.salt_b64).toEqual(expect.any(String));
    expect(args.payload.hash_b64).toEqual(expect.any(String));
    expect(JSON.stringify(args.payload)).not.toContain('4321');
  });

  it('gera salt diferente a cada gravacao', async () => {
    invoke.mockResolvedValue(null);
    await definirPin('4321');
    await definirPin('4321');
    const primeiro = (invoke.mock.calls[0][1] as { payload: { salt_b64: string } }).payload.salt_b64;
    const segundo = (invoke.mock.calls[1][1] as { payload: { salt_b64: string } }).payload.salt_b64;
    expect(primeiro).not.toBe(segundo);
  });
});

describe('verificarPin', () => {
  it('aceita o PIN correto', async () => {
    invoke.mockResolvedValue(null);
    await definirPin('4321');
    const { payload } = invoke.mock.calls[0][1] as { payload: Record<string, unknown> };
    invoke.mockResolvedValue(payload);
    await expect(verificarPin('4321')).resolves.toBe(true);
  });

  it('recusa PIN errado mesmo com formato valido', async () => {
    invoke.mockResolvedValue(null);
    await definirPin('4321');
    const { payload } = invoke.mock.calls[0][1] as { payload: Record<string, unknown> };
    invoke.mockResolvedValue(payload);
    // 9999 tem o mesmo formato de 4321: e o caso que a desativacao precisa barrar.
    await expect(verificarPin('9999')).resolves.toBe(false);
  });

  it('recusa quando nao ha PIN cadastrado', async () => {
    invoke.mockResolvedValue(null);
    await expect(verificarPin('1234')).resolves.toBe(false);
  });

  it('nao remove a credencial (quem remove e a UI, apos verificar)', async () => {
    invoke.mockResolvedValue(null);
    await expect(verificarPin('1234')).resolves.toBe(false);
    const comandos = invoke.mock.calls.map((c) => c[0]);
    expect(comandos).not.toContain('remove_auth');
  });
});

describe('removerPin', () => {
  it('delega a remocao ao shell Tauri', async () => {
    invoke.mockResolvedValue(null);
    await removerPin();
    expect(invoke.mock.calls[0][0]).toBe('remove_auth');
  });
});
