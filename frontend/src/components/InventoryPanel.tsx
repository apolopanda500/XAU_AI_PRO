import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import StrategyGovernancePanel from './StrategyGovernancePanel';

const MT5=`${apiBase()}`;
type Position={ticket:number;symbol:string;profit?:number;sl?:number;tp?:number};
type Inventory={account?:{login?:number;mode?:string};positions?:Position[];pending_orders?:unknown[];exposure?:{volume?:number;floating_profit?:number;protected?:boolean};ea_heartbeat?:{live?:boolean;age_sec?:number}};
export default function InventoryPanel(){
 const [data,setData]=useState<Inventory|null>(null);const [error,setError]=useState('');
 useEffect(()=>{let active=true;const load=async()=>{try{const r=await fetch(MT5+'/api/inventory',{signal:AbortSignal.timeout(5000)});if(!r.ok)throw new Error('Inventário indisponível');const d=await r.json() as Inventory;if(active){setData(d);setError('')}}catch(e){if(active)setError(e instanceof Error?e.message:'Gateway indisponível')}};void load();const t=window.setInterval(load,5000);return()=>{active=false;window.clearInterval(t)}},[]);
 const positions=data?.positions??[];return <div className="inventory-operational-zone"><div className="card inventory-panel" style={{marginTop:14}}><div className="btn-row" style={{justifyContent:'space-between',marginTop:0}}><h2 style={{margin:0}}>Inventário operacional</h2><span className={`chip ${data?.ea_heartbeat?.live?'ok':'warn'}`}>{data?.ea_heartbeat?.live?'EA vivo':'Sem heartbeat'}</span></div>{error?<div className="placeholder neg">{error}</div>:<div className="grid cols-4" style={{marginTop:8}}><div><span className="kpi-label">Conta</span><strong>{data?.account?.login??'--'}</strong><span className="kpi-sub">{data?.account?.mode??'--'}</span></div><div><span className="kpi-label">Posições</span><strong>{positions.length}</strong><span className="kpi-sub">pendentes: {data?.pending_orders?.length??0}</span></div><div><span className="kpi-label">Exposição</span><strong>{data?.exposure?.volume??0}</strong><span className="kpi-sub">P/L {data?.exposure?.floating_profit??0}</span></div><div><span className="kpi-label">Proteção</span><strong>{positions.length===0?'Sem posição':data?.exposure?.protected?'SL/TP OK':'Revisar SL/TP'}</strong><span className="kpi-sub">heartbeat {data?.ea_heartbeat?.age_sec??'--'}s</span></div></div>}</div><StrategyGovernancePanel symbol={positions[0]?.symbol??'XAUUSD'}/></div>;
}
