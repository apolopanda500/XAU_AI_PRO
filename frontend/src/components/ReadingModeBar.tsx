// ===========================================================================
//  MODOS DE LEITURA, CANAL E TAXA DE QUADROS (18/11/2026)
// ===========================================================================
//  Tres densidades para a mesma tela:
//    compacto  — celular/retrato: menos espaco entre campos, fonte menor;
//    mesa      — uso normal em PC;
//    auditoria — tudo aberto e fonte maior, para conferir numero por numero.
//
//  O modo e aplicado em `<html data-leitura="...">` porque quem consome e o
//  CSS (`theme/reading_modes.css`). Um botao que so muda o proprio rotulo
//  seria enfeite; este muda a densidade real das tabelas e dos campos.
//
//  O CANAL e derivado da URL configurada, nao digitado: loopback e local, o
//  resto e remoto. E a taxa de quadros vem do medidor, nunca de uma constante.
import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { faixaDeQuadros, medidorDeQuadros } from '../utils/frameRateEngine';

export type ModoDeLeitura = 'compacto' | 'mesa' | 'auditoria';

const CHAVE = 'xau-modo-leitura';
const MODOS: Array<{ id: ModoDeLeitura; rotulo: string; dica: string }> = [
  { id: 'compacto', rotulo: 'Compacto', dica: 'Menos espaco, mais linhas visiveis' },
  { id: 'mesa', rotulo: 'Mesa', dica: 'Densidade padrao de operacao' },
  { id: 'auditoria', rotulo: 'Auditoria', dica: 'Fonte maior, tudo aberto' },
];

function lerModo(): ModoDeLeitura {
  try {
    const salvo = window.localStorage.getItem(CHAVE);
    if (salvo === 'compacto' || salvo === 'mesa' || salvo === 'auditoria') return salvo;
  } catch {
    // sem storage: cai no padrao
  }
  return 'mesa';
}

function descreverCanal(): { tipo: 'USB/ADB' | 'LOCAL' | 'REMOTO'; host: string } {
  try {
    const url = new URL(apiBase());
    const host = url.host;
    const loopback =
      url.hostname === '127.0.0.1' || url.hostname === 'localhost' || url.hostname === '[::1]';
    if (!loopback) return { tipo: 'REMOTO', host };
    // Em Android, o loopback so existe porque o `adb reverse` publicou o tunel.
    const android =
      typeof navigator !== 'undefined' && /android/i.test(navigator.userAgent);
    return { tipo: android ? 'USB/ADB' : 'LOCAL', host };
  } catch {
    return { tipo: 'REMOTO', host: 'invalido' };
  }
}

export interface ReadingModeBarProps {
  websocket: boolean;
  atualizadoEm: string;
  onRessincronizar: () => void;
}

export default function ReadingModeBar({
  websocket,
  atualizadoEm,
  onRessincronizar,
}: ReadingModeBarProps) {
  const [modo, setModo] = useState<ModoDeLeitura>(lerModo);
  const [fps, setFps] = useState(0);
  const canal = descreverCanal();

  useEffect(() => {
    document.documentElement.setAttribute('data-leitura', modo);
    try {
      window.localStorage.setItem(CHAVE, modo);
    } catch {
      // preferencia nao persiste; o modo atual continua valendo
    }
  }, [modo]);

  useEffect(() => {
    const cancelar = medidorDeQuadros.assinar(setFps);
    return cancelar;
  }, []);

  return (
    <div className="modo-leitura-barra">
      <div className="modo-leitura-grupo" role="group" aria-label="Modo de leitura">
        <span className="modo-leitura-rotulo">MODO</span>
        {MODOS.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`modo-leitura-botao ${modo === m.id ? 'ativo' : ''}`}
            aria-pressed={modo === m.id}
            title={m.dica}
            onClick={() => setModo(m.id)}
          >
            {m.rotulo}
          </button>
        ))}
      </div>

      <div className="modo-leitura-estado">
        <span className={`modo-leitura-canal canal-${canal.tipo.toLowerCase().replace('/', '-')}`}>
          ● {canal.tipo} · {canal.host}
        </span>
        <span className={websocket ? 'modo-leitura-ws ativo' : 'modo-leitura-ws'}>
          {websocket ? 'WS ONLINE' : 'WS OFFLINE'}
        </span>
        <span className="modo-leitura-fps">
          {fps > 0 ? `${fps} FPS · ${faixaDeQuadros(fps)}` : 'medindo FPS'}
        </span>
        <span className="modo-leitura-hora">sync {atualizadoEm}</span>
        <button type="button" className="modo-leitura-sync" onClick={onRessincronizar}>
          Ressincronizar
        </button>
      </div>
    </div>
  );
}
