import { useCallback, useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import '../theme/plans-table.css';

type Plan = {
  id: string;
  name: string;
  description: string;
  reference_price_monthly: number;
  currency: string;
  features: string[];
  entitlements: Record<string, boolean>;
  limits: Record<string, number>;
};

type Subscription = {
  plan_id: string;
  plan: Plan;
  execution_mode: string;
  live_execution: boolean;
};

type Strategy = {
  id: string;
  name: string;
  description: string;
  risk_profile: string;
  timeframes: string[];
  symbols: string[];
  available: boolean;
  following: boolean;
};

const api = apiBase();

export default function SubscriptionPanel() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [status, setStatus] = useState('Carregando planos locais...');
  const loadGeneration = useRef(0);

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    try {
      const [plansResponse, subscriptionResponse, strategiesResponse] = await Promise.all([
        fetch(`${api}/api/subscriptions/plans`, { signal: AbortSignal.timeout(6000) }),
        fetch(`${api}/api/subscriptions/me`, { signal: AbortSignal.timeout(6000) }),
        fetch(`${api}/api/social/strategies`, { signal: AbortSignal.timeout(6000) }),
      ]);
      if (!plansResponse.ok || !subscriptionResponse.ok) throw new Error('gateway indisponível');
      const planData = await plansResponse.json() as { plans?: Plan[] };
      const subscriptionData = await subscriptionResponse.json() as { subscription?: Subscription };
      const strategyData = strategiesResponse.ok ? await strategiesResponse.json() as { strategies?: Strategy[] } : { strategies: [] };
      if (generation !== loadGeneration.current) return;
      setPlans(Array.isArray(planData.plans) ? planData.plans : []);
      setSubscription(subscriptionData.subscription ?? null);
      setStrategies(Array.isArray(strategyData.strategies) ? strategyData.strategies : []);
      setStatus('Planos locais; nenhuma cobrança ou execução real foi ativada.');
    } catch {
      if (generation === loadGeneration.current) setStatus('Gateway indisponível. A assinatura local será exibida quando o gateway iniciar.');
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const activate = async (planId: string) => {
    loadGeneration.current += 1;
    setStatus('Ativando plano local...');
    try {
      const response = await fetch(`${api}/api/subscriptions/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: planId }),
        signal: AbortSignal.timeout(6000),
      });
      const data = await response.json() as { subscription?: Subscription; error?: string };
      if (!response.ok || !data.subscription) throw new Error(data.error || 'plano indisponível');
      setSubscription(data.subscription);
      setStatus(`Plano ${data.subscription.plan.name} ativado localmente.`);
      await load();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'não foi possível ativar o plano');
    }
  };

  const follow = async (strategyId: string) => {
    loadGeneration.current += 1;
    setStatus('Atualizando estratégia paper...');
    try {
      const response = await fetch(`${api}/api/social/follow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy_id: strategyId }),
        signal: AbortSignal.timeout(6000),
      });
      const data = await response.json() as { error?: string };
      if (!response.ok) throw new Error(data.error || 'estratégia indisponível');
      await load();
      setStatus('Estratégia adicionada ao modo social paper.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'não foi possível seguir a estratégia');
    }
  };

  return (
    <div className="subscription-panel">
      <p className="hint settings-hint">
        Preferência local de recursos. Não é licença comercial nem cobrança. Copy trading real permanece bloqueado.
      </p>

      <div className="table-scroll">
        <table className="tbl compact-table plans-grid">
          <caption className="sr-only">Planos locais disponíveis</caption>
          <thead>
            <tr>
              <th>Plano</th>
              <th className="num">Referência</th>
              <th>Inclui</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => {
              const ativo = subscription?.plan_id === plan.id;
              return (
                <tr key={plan.id} className={ativo ? 'selected' : ''}>
                  <td><strong>{plan.name}</strong><br /><span className="muted">{plan.description}</span></td>
                  <td className="num">{plan.reference_price_monthly === 0 ? 'Grátis' : `${plan.currency} ${plan.reference_price_monthly}`}</td>
                  <td className="plans-features">{plan.features.join(' · ')}</td>
                  <td><span className={`chip ${ativo ? 'ok' : 'warn'}`}>{ativo ? 'ativo' : 'local'}</span></td>
                  <td>
                    <button type="button" className="btn xs primary" onClick={() => void activate(plan.id)} disabled={ativo}>
                      {ativo ? 'Ativo' : 'Ativar'}
                    </button>
                  </td>
                </tr>
              );
            })}
            {!plans.length && <tr><td colSpan={5}>Nenhum plano lido do gateway.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="table-scroll">
        <table className="tbl compact-table plans-grid">
          <caption className="sr-only">Estratégias compartilhadas</caption>
          <thead>
            <tr>
              <th>Estratégia</th>
              <th>Risco</th>
              <th>Ativos</th>
              <th>Tempo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {strategies.map((strategy) => (
              <tr key={strategy.id}>
                <td><strong>{strategy.name}</strong><br /><span className="muted">{strategy.description}</span></td>
                <td><span className="chip">{strategy.risk_profile}</span></td>
                <td>{strategy.symbols.join(' · ')}</td>
                <td>{strategy.timeframes.join(' / ')}</td>
                <td>
                  <button type="button" className="btn xs ghost" disabled={!strategy.available || strategy.following} onClick={() => void follow(strategy.id)}>
                    {strategy.following ? 'Seguindo' : strategy.available ? 'Seguir' : 'Requer Pro'}
                  </button>
                </td>
              </tr>
            ))}
            {!strategies.length && <tr><td colSpan={5}>Nenhuma estratégia publicada.</td></tr>}
          </tbody>
        </table>
      </div>

      {status && <div className="hint" role="status">{status}</div>}
    </div>
  );
}
