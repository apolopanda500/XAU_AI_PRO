import { useState } from 'react';
import {
  ativarPlanoLocal,
  useAssinatura,
  usePlanosCatalogo,
  type PlanoCatalogo,
} from '../hooks/queries';

/*
  O LUGAR DO DESBLOQUEIO (11/10/2026)
  ====================================
  MEDIDO: ligar o motor numa conta Free respondia 403 `PLAN_REQUIRED` com o
  `required_plans` no corpo — e a tela só mostrava "Configurado, mas não ligou:
  recurso nao liberado no plano atual: auto_engine". O gateway já expunha as
  três rotas de assinatura; o frontend não tinha UM consumidor. Bloqueio com o
  caminho do desbloqueio fora da tela é o mesmo beco sem saída das mensagens
  que mandavam para uma aba já removida.

  O que esta secao FAZ: lê o catálogo (`/api/subscriptions/plans`), mostra o
  plano que o gateway diz estar ativo (`/api/subscriptions/me`) e ativa um
  plano LOCALMENTE (`/api/subscriptions/activate`).

  O que ela NÃO faz, e a tela avisa:
    - não cobra nada (`billing_status: not_configured`, ativação local);
    - não destrava saque nem transferência — `withdrawals_enabled` é `false`
      em TODA resposta, e nenhuma regra de plano muda isso (AGENTS.md 2);
    - não liga execução real (`live_execution` é `false`; a execução real é
      o caminho gated de §4, com validação e autorização explícita).

  A ativação é um registro local com integridade SHA-256
  (`backend/planos/subscriptions.py`); adulterar o arquivo não abre porta:
  `pode_usar_multi_modelo` e o resto do `has_entitlement` são a trava.
*/
export default function PlanoConfig() {
  const assinatura = useAssinatura();
  const catalogo = usePlanosCatalogo();
  const [status, setStatus] = useState('');
  const [ocupado, setOcupado] = useState('');

  const atual = assinatura.data?.subscription;
  const ativoId = String(atual?.effective_plan_id || atual?.plan_id || 'free').trim();
  const planos: PlanoCatalogo[] = Array.isArray(catalogo.data?.plans) ? catalogo.data!.plans! : [];

  const ativar = async (plano: PlanoCatalogo) => {
    const id = String(plano.id ?? '').trim();
    if (!id || ocupado) return;
    setOcupado(id);
    try {
      const resultado = await ativarPlanoLocal(id);
      if (resultado.ok === false) {
        setStatus(`Plano ${plano.name ?? id} não ativado: ${resultado.error ?? 'recusado'}`);
        return;
      }
      setStatus(`Plano ${plano.name ?? id} ativado neste dispositivo.`);
      // A tela volta a perguntar o gateway: o que aparece aqui é o que ele
      // respondeu, não o que o botão acreditou ter feito.
      await assinatura.refetch();
    } finally {
      setOcupado('');
    }
  };

  return (
    <div>
      <h3>Plano</h3>
      <p className="hint">
        Ativação local neste dispositivo: sem cobrança, sem saque e sem transferência. O plano
        decide o que o app destrava; a trava de dinheiro real não muda em nenhum deles.
      </p>

      <div className="settings-rows">
        <div className={`chip ${atual?.active ? 'ok' : 'warn'}`} data-testid="plano-atual">
          {atual?.plan?.name ?? ativoId ?? 'Free'}
          {atual?.active === false ? ' (expirado/inválido → Free)' : ''}
        </div>
        {assinatura.data?.subscription?.plan?.description && (
          <p className="hint">{assinatura.data.subscription.plan.description}</p>
        )}
      </div>

      {assinatura.isError && (
        <p className="hint" role="status" data-testid="plano-erro-assinatura">
          Assinatura indisponível: {(assinatura.error as Error)?.message ?? 'gateway indisponível'}
        </p>
      )}
      {catalogo.isError && (
        <p className="hint" role="status" data-testid="plano-erro-catalogo">
          Catálogo de planos indisponível:{' '}
          {(catalogo.error as Error)?.message ?? 'gateway indisponível'}
        </p>
      )}

      <div className="plano-lista">
        {planos.map((plano) => {
          const id = String(plano.id ?? '').trim();
          const ehAtivo = id === ativoId;
          return (
            <div
              key={id || plano.name || 'plano'}
              className={`plano-item ${ehAtivo ? 'ativo' : ''}`}
              data-plano-id={id}
            >
              <div>
                <h4>
                  {plano.name ?? id}{' '}
                  {Number.isFinite(Number(plano.reference_price_monthly)) &&
                  Number(plano.reference_price_monthly) > 0 ? (
                    <span className="muted">
                      · referência R$ {Number(plano.reference_price_monthly)}/mês
                    </span>
                  ) : null}
                  {ehAtivo ? <span className="chip ok">ativo</span> : null}
                </h4>
                {plano.description && <p>{plano.description}</p>}
                {Array.isArray(plano.features) && plano.features.length > 0 && (
                  <ul className="plano-features">
                    {plano.features.map((f) => (
                      <li key={String(f)}>{f}</li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                type="button"
                className="btn sm"
                disabled={ehAtivo || ocupado === id || ocupado !== ''}
                onClick={() => void ativar(plano)}
                title={
                  ehAtivo
                    ? 'Este plano já está ativo neste dispositivo'
                    : `Ativar ${plano.name ?? id} localmente, sem cobrança`
                }
              >
                {ehAtivo ? 'Ativado' : ocupado === id ? 'Ativando…' : 'Ativar'}
              </button>
            </div>
          );
        })}
        {!planos.length && !catalogo.isError && (
          <p className="hint" data-testid="plano-catalogo-vazio">
            Lendo o catálogo de planos no gateway…
          </p>
        )}
      </div>

      {status && (
        <div className="hint" role="status" data-testid="plano-status">
          {status}
        </div>
      )}
    </div>
  );
}
