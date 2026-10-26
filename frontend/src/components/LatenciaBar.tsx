import React, { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { IconeRelogio, IconeSinal } from './Icones';
import '../theme/latencia-bar.css';

type Medicao = {
  broker: string;
  ms: number | null;
  ok: boolean;
  motivo: string;
  server: string;
  melhor_em_ms: number | null;
};

/**
 * POR QUE A BARRA FICAVA VAZIA — e por que era invisível
 * ========================================================
 * MEDIDO no backend (`mt5_gateway.py`, `_autorizado`): **toda** rota GET exige
 * `Authorization: Bearer`, e a MESMA função aplica **rate limit por minuto**.
 *
 * O token é injetado por `installGatewayAuth` (`lib/tauri.ts:41`), que
 * intercepta `window.fetch` — por isso o resto do app responde e esta barra
 * também é chamada com token.
 *
 * Aí está o furo: quando a resposta é **429** (cota do minuto estourada), o
 * corpo vem `{ok: false, error: "rate limit excedido"}` **sem `corretoras`**. O
 * componente fazia:
 *
 *     setMedicoes(Array.isArray(d.corretoras) ? d.corretoras : [])
 *
 * e depois `if (!medicoes.length) return null` — a barra **sumia da tela**.
 *
 * Três falhas de leitura numa linha só: 401, 429 e "nenhuma corretora
 * configurada" produziam exatamente a mesma tela — um espaço vazio no rodapé.
 * O operador concluía "a latência não existe" e não tinha como saber que era
 * cota estourada.
 *
 * O conserto é distinguir os três e DIZER qual deles é.
 */
type EstadoBarra = 'medindo' | 'ok' | 'sem-corretora' | 'token' | 'cota' | 'indisponivel';

/** Nivel de latencia. A FAIXA e um token no CSS, aqui e o dado. */
function nivel(m: Medicao): 'otima' | 'ok' | 'ruim' | 'off' {
  if (m.ms === null) return 'off';
  if (m.ms <= 150) return 'otima';
  if (m.ms <= 350) return 'ok';
  return 'ruim';
}

/**
 * Latencia ao vivo da CONTA ATIVA — canto inferior direito, sem lista.
 *
 * 25/10/2026, pedido do dono: "deletar a lista, manter o ms da conta".
 * O dropdown por corretora saiu; o que fica no rodape e o item unico:
 * ponto de cor + `broker · ms` da conta que o operador escolheu (`ativa`).
 * As outras corretoras continuam MEDIDAS no gateway (`/api/latencia`) — o
 * item e a leitura da conta ATIVA, que e o dado que decide a operacao.
 *
 * REGRA QUE IMPORTA
 * -----------------
 * Sem resposta mostra "sem resposta" e NUNCA `0 ms`. Zero parece medida
 * perfeita e esconderia corretora fora do ar. O valor vem do backend, que
 * crono-metra de verdade (ver `backend/latencia.py`).
 */
export default function LatenciaBar({ ativa }: { ativa?: string }) {
  const [medicoes, setMedicoes] = useState<Medicao[]>([]);
  const [erro, setErro] = useState(false);
  const [estado, setEstado] = useState<EstadoBarra>('medindo');

  useEffect(() => {
    let vivo = true;
    const medir = () => {
      fetch(`${apiBase()}/api/latencia`, { signal: AbortSignal.timeout(6000) })
        .then((r) => {
          /*
            O STATUS ANTES DO CORPO. `r.json()` em resposta de erro devolve o
            `{ok:false}` e esconde o que aconteceu; ler o status primeiro é o
            que separa 401 de 429 de 200 com lista vazia.
          */
          const status = r.status;
          return r.json().then(
            (d: { corretoras?: Medicao[] }) => ({ status, d }),
            () => ({ status, d: {} as { corretoras?: Medicao[] } }),
          );
        })
        .then(({ status, d }) => {
          if (!vivo) return;
          if (status === 401) {
            setEstado('token');
            setErro(false);
            return;
          }
          if (status === 429) {
            // Cota do minuto, nao corretora fora do ar. A mensagem tem que dizer
            // isso: "sem medição" levaria o operador a culpar a rede.
            setEstado('cota');
            setErro(false);
            return;
          }
          if (!Array.isArray(d.corretoras)) {
            setEstado('indisponivel');
            setErro(true);
            return;
          }
          if (!d.corretoras.length) {
            setEstado('sem-corretora');
            setErro(false);
            return;
          }
          setMedicoes(d.corretoras);
          setEstado('ok');
          setErro(false);
        })
        .catch(() => {
          if (vivo) {
            setEstado('indisponivel');
            setErro(true);
          }
        });
    };
    medir();
    // 15 s: rapido demais vira consumo, lento demais deixa de ajudar a decidir.
    const t = setInterval(medir, 15_000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, []);

  if (erro) {
    return (
      <div className="latencia-rodape">
        <span className="latencia-item latencia-off" title="Gateway sem resposta para medir latência">
          {/* `📡` e emoji: cor e dois caracteres de largura, ao lado de icones
              monocromaticos do mesmo painel. */}
          <IconeSinal />
          sem medição
        </span>
      </div>
    );
  }
  if (!medicoes.length) {
    /*
      A BARRA NUNCA DESAPARECE, E DIZ POR QUE.

      Antes: `return null` quando não havia medição. Ausência renderizada como
      NADA é indistinguível de ausência real — e foi assim que 401, 429 e
      "nenhuma corretora" viraram o mesmo espaço vazio no rodapé.

      Agora cada estado tem a sua frase. "Sem medição" sem causa é um relatório
      inútil; "cota do minuto" diz o que fazer.
    */
    const FRASES: Record<EstadoBarra, { texto: string; titulo: string }> = {
      medindo: { texto: 'medindo…', titulo: 'Primeira medição de latência em andamento' },
      'sem-corretora': {
        texto: 'sem corretora',
        titulo: 'Nenhuma corretora configurada ainda',
      },
      token: {
        texto: 'sem token',
        titulo: 'O gateway recusou a leitura (401). A sessão do app não foi reconhecida.',
      },
      cota: {
        texto: 'cota do minuto',
        titulo:
          'O gateway devolveu 429: cota de leitura do minuto estourada. Não é corretora fora do ar.',
      },
      indisponivel: {
        texto: 'gateway fora',
        titulo: 'O gateway não respondeu para medir latência',
      },
      ok: { texto: 'sem medição', titulo: 'Sem medição disponível' },
    };
    const f = FRASES[estado];
    return (
      <div className="latencia-rodape">
        <span className="latencia-item latencia-off" title={f.titulo}>
          <IconeRelogio /> {f.texto}
        </span>
      </div>
    );
  }

  // A CONTA ATIVA PRIMEIRO (25/10/2026): a lista sumiu, entao o item do rodape
  // e obrigatoriamente DA CONTA ESCOLHIDA. Se a medida da conta ativa nao
  // existe (nenhuma corretora medida com esse nome), digo sem resposta — nao
  // escondo o ms de OUTRA corretora na frente da conta que o operador usa.
  const daConta = (ativa && medicoes.find((m) => m.broker === ativa)) || null;
  const semResposta = !daConta || daConta.ms === null;

  return (
    <div className="latencia-rodape">
      <span
        className={`latencia-gatilho latencia-${semResposta ? 'off' : nivel(daConta)}`}
        title={`Latência da conta ativa (${ativa || 'sem corretora'})`}
      >
        <span className="latencia-gatilho-ponto" aria-hidden="true" />
        {/* O PAR agora vai no texto: com a lista fora, `mexc · 334 ms` responde
            DE QUEM e o ms — e o operador le sem clicar. */}
        <span className="latencia-gatilho-ms">
          {ativa ? `${ativa} · ` : ''}
          {semResposta ? 'sem resposta' : `${Math.round(daConta.ms)} ms`}
        </span>
        <span className="sr-only">
          {`Latência da conta ${ativa || 'sem corretora'}: ${
            semResposta ? 'sem resposta' : `${Math.round(daConta.ms)} ms`
          }`}
        </span>
      </span>
    </div>
  );
}
