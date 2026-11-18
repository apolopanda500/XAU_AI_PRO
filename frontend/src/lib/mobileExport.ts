// Exportação de relatórios/auditoria no cliente móvel.
// Tenta compartilhamento/FS nativo quando disponível; fallback para download no navegador.

function baixarBlob(nome: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export async function exportarTexto(nome: string, conteudo: string, mime = 'text/plain;charset=utf-8'): Promise<void> {
  const blob = new Blob([conteudo], { type: mime });
  const nav = navigator as Navigator & {
    share?: (data: ShareData & { files?: File[] }) => Promise<void>;
    canShare?: (data: ShareData & { files?: File[] }) => boolean;
  };
  try {
    const arquivo = new File([blob], nome, { type: mime });
    if (nav.canShare?.({ files: [arquivo] }) && nav.share) {
      await nav.share({ files: [arquivo], title: nome, text: 'Exportação XAU AI PRO' });
      return;
    }
  } catch {
    // fallback abaixo
  }
  baixarBlob(nome, blob);
}

function csvEsc(valor: unknown): string {
  const s = valor == null ? '' : String(valor);
  if (/[",\n;]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export async function exportarCsv(nome: string, linhas: Array<Record<string, unknown>>): Promise<void> {
  const colunas = Array.from(
    linhas.reduce<Set<string>>((acc, row) => {
      Object.keys(row || {}).forEach((k) => acc.add(k));
      return acc;
    }, new Set<string>()),
  );
  const cabecalho = colunas.join(',');
  const corpo = linhas
    .map((row) => colunas.map((c) => csvEsc((row as any)[c])).join(','))
    .join('\n');
  const csv = colunas.length ? `${cabecalho}\n${corpo}` : '';
  await exportarTexto(nome.endsWith('.csv') ? nome : `${nome}.csv`, csv, 'text/csv;charset=utf-8');
}

export async function exportarJson(nome: string, dados: unknown): Promise<void> {
  const texto = JSON.stringify(dados, null, 2);
  await exportarTexto(nome.endsWith('.json') ? nome : `${nome}.json`, texto, 'application/json;charset=utf-8');
}
