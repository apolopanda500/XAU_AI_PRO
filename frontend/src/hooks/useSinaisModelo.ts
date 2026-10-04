import { useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';

export type SinalModelo = {
  time: number;
  price: number | null;
  signal: string;
  confidence: number | null;
  model: string;
  motivo: string;
};

type Resposta = {
  signal?: string;
  confidence?: number;
  price?: number;
  model?: string;
  reason?: string;
  motivo?: string;
  disponivel?: boolean;
  available?: boolean;
};

/**
 * Fita de sinais do modelo em tempo real.
 *
 * Pesquisa `/api/ai/predict` a cada minuto e acumula os sinais com preco e
 * hora — e o que permite "ver o modelo operar" sem abrir ordem nenhuma.
 * NEUTRAL e recusa entram na fita como texto (sem marcar grafico), para o
 * operador distinguir "modelo calado" de "modelo sem sinal".
 *
 * Nada e inventado: sem resposta, a fita mostra o ultimo estado com a idade
 * em segundos e o aviso de desatualizado.
 */
export function useSinaisModelo(symbol: string, timeframe: string, ativo: boolean) {
  const [sinais, setSinais] = useState<SinalModelo[]>([]);
  const [idadeSeg, setIdadeSeg] = useState<number | null>(null);
  const ultimoRef = useRef<number>(0);

  useEffect(() => {
    if (!ativo || !symbol || !timeframe) return undefined;
    let vivo = true;
    const consultar = async () => {
      try {
        const r = await fetch(
          `${apiBase()}/api/ai/predict?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`,
          { signal: AbortSignal.timeout(15000) },
        );
        const d = (await r.json()) as Resposta;
        if (!vivo) return;
        const agora = Math.floor(Date.now() / 1000);
        ultimoRef.current = agora;
        const ok = d.disponivel ?? d.available ?? false;
        setSinais((atual) =>
          [
            {
              time: agora,
              price: typeof d.price === 'number' ? d.price : null,
              signal: ok ? String(d.signal ?? 'NEUTRAL') : 'INDISPONIVEL',
              confidence: typeof d.confidence === 'number' ? d.confidence : null,
              model: String(d.model ?? ''),
              motivo: String(d.reason ?? d.motivo ?? ''),
            },
            ...atual,
          ].slice(0, 30),
        );
      } catch {
        if (vivo) setIdadeSeg((v) => v);
      }
    };
    void consultar();
    const t = window.setInterval(consultar, 60_000);
    const relogio = window.setInterval(() => {
      if (ultimoRef.current) setIdadeSeg(Math.floor(Date.now() / 1000) - ultimoRef.current);
    }, 5_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
      window.clearInterval(relogio);
    };
  }, [ativo, symbol, timeframe]);

  return { sinais, idadeSeg };
}
