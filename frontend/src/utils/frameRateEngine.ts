// ===========================================================================
//  MEDIDOR DE QUADROS (18/11/2026)
// ===========================================================================
//  O painel mostra "144 Hz" ou "60 Hz" — e mostra o que foi MEDIDO, nunca o
//  que o monitor promete. Um numero escrito a mao envelhece: o app roda em
//  WebView2 no PC, em WebView no Android e pode estar limitado por bateria,
//  por aba em segundo plano ou por composicao de software.
//
//  POR QUE UM LOOP PROPRIO E NAO O `QuantumBackground`
//  ==================================================
//  O fundo animado tem teto de 30 fps de proposito (ver `QuantumBackground`).
//  Reaproveitar o contador dele mediria 30 e chamaria de "taxa do aparelho".
//  Aqui o `requestAnimationFrame` e vazio: ele mede a taxa que o WebView
//  realmente entrega, sem desenhar nada.
//
//  PAUSA FORA DE VISTA
//  ===================
//  `document.visibilityState` e checado a cada quadro. Minimizado, o loop
//  continua agendado (custo de um callback vazio) mas nao conta nem mede.
//  Isso evita o defeito classico de "FPS caiu para 0" quando o usuario apenas
//  trocou de janela.
export type FaixaQuadros = 'ECO' | 'PADRAO' | 'ALTA';

/** Rotulo de faixa derivado da taxa medida — nao e configuracao do usuario. */
export function faixaDeQuadros(fps: number): FaixaQuadros {
  if (fps >= 110) return 'ALTA';
  if (fps >= 50) return 'PADRAO';
  return 'ECO';
}

class MedidorDeQuadros {
  private rafId: number | null = null;
  private quadros = 0;
  private inicioJanela = 0;
  private ultimoFps = 0;
  private ouvintes = new Set<(fps: number) => void>();

  /** Liga o medidor. Chamar duas vezes e no-op, nao duplica o loop. */
  medir(): void {
    if (this.rafId !== null) return;
    this.inicioJanela = performance.now();
    this.quadros = 0;
    const passo = (agora: number) => {
      this.rafId = requestAnimationFrame(passo);
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        // Janela minimizada: reinicia a janela para nao creditar tempo parado.
        this.quadros = 0;
        this.inicioJanela = agora;
        return;
      }
      this.quadros += 1;
      const decorrido = agora - this.inicioJanela;
      if (decorrido < 1000) return;
      this.ultimoFps = Math.round((this.quadros * 1000) / decorrido);
      this.quadros = 0;
      this.inicioJanela = agora;
      this.ouvintes.forEach((fn) => fn(this.ultimoFps));
    };
    this.rafId = requestAnimationFrame(passo);
  }

  parar(): void {
    if (this.rafId === null) return;
    cancelAnimationFrame(this.rafId);
    this.rafId = null;
    this.quadros = 0;
  }

  fps(): number {
    return this.ultimoFps;
  }

  /**
   * Devolve a funcao de cancelamento da assinatura.
   *
   * O loop so existe enquanto ha ouvinte: sem isto, cada montagem da barra
   * deixaria um `requestAnimationFrame` eterno — inclusive nos testes, onde
   * centenas de montagens somariam centenas de loops.
   */
  assinar(fn: (fps: number) => void): () => void {
    this.ouvintes.add(fn);
    this.medir();
    if (this.ultimoFps > 0) fn(this.ultimoFps);
    return () => {
      this.ouvintes.delete(fn);
      if (this.ouvintes.size === 0) this.parar();
    };
  }
}

export const medidorDeQuadros = new MedidorDeQuadros();
