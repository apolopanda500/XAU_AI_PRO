import { useCallback, useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';

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
    <div className="card settings-card subscription-panel">
      <div className="section-head">
        <div>
          <h2>Planos locais e Social Paper</h2>
          <span className="muted">Preferência local de recursos; não é licença comercial nem cobrança</span>
        </div>
        <span className="chip warn">paper/demo</span>
      </div>
      <div className="plan-grid">
        {plans.map((plan) => (
          <article className={`plan-card ${subscription?.plan_id === plan.id ? 'selected' : ''}`} key={plan.id}>
            <div className="plan-head">
              <h3>{plan.name}</h3>
              <strong>{plan.reference_price_monthly === 0 ? 'Grátis' : `Referência: ${plan.currency} ${plan.reference_price_monthly}/mês`}</strong>
            </div>
            <p>{plan.description}</p>
            <ul>
              {plan.features.map((feature) => <li key={feature}>{feature}</li>)}
            </ul>
            <button type="button" className="btn primary sm" onClick={() => void activate(plan.id)}>
              {subscription?.plan_id === plan.id ? 'Plano ativo' : 'Ativar localmente'}
            </button>
          </article>
        ))}
      </div>
      <div className="section-title">Social Paper</div>
      <p className="hint">Compartilhamento local de estratégias para estudo. Copy trading real permanece bloqueado.</p>
      <div className="strategy-grid">
        {strategies.map((strategy) => (
          <div className="strategy-card" key={strategy.id}>
            <div><strong>{strategy.name}</strong><span className="chip">{strategy.risk_profile}</span></div>
            <p>{strategy.description}</p>
            <small>{strategy.symbols.join(' · ')} · {strategy.timeframes.join(' / ')}</small>
            <button type="button" className="btn ghost sm" disabled={!strategy.available || strategy.following} onClick={() => void follow(strategy.id)}>
              {strategy.following ? 'Seguindo no paper' : strategy.available ? 'Seguir no paper' : 'Requer Pro'}
            </button>
          </div>
        ))}
      </div>
      {status && <div className="hint" role="status">{status}</div>}
    </div>
  );
}
