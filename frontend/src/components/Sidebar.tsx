import React from 'react'; import { useAppStore, TabType } from '../hooks/useAppStore';
const items:[TabType,string,string][]=[['dashboard','Painel','Ã¢â€”Ë†'],['market','Mercado','Ã¢â€”Å’'],['positions','Carteira','Ã¢â€“Â£'],['charts','GrÃƒÂ¡ficos','Ã¢Å’Â'],['robot','RobÃƒÂ´ MT5','Ã¢Å¡â„¢'],['strategy-tester','Teste EstratÃƒÂ©gia','Ã¢â€”Â«'],['robot-vision','RobÃƒÂ´ Vision','Ã¢Å“Â¦'],['tools','Ferramentas','Ã¢Å¡â€™'],['integrations','IntegraÃƒÂ§ÃƒÂµes','Ã¢â€¡â€ž'],['settings','ConfiguraÃƒÂ§ÃƒÂµes','Ã¢Å¡â„¢']];
export default function Sidebar(){const {activeTab,setActiveTab}=useAppStore();return <aside className="sidebar"><div className="brand">Ã¢â€”Ë† XAU AI PRO</div><nav className="nav-list">{items.map(([key,label,icon])=><button key={key} className={`nav-item ${activeTab===key?'active':''}`} onClick={()=>setActiveTab(key)}><span>{icon}</span><span>{label}</span></button>)}</nav><div className="muted" style={{padding:'15px',borderTop:'1px solid var(--border)'}}>v0.1.0 Ã¢â‚¬Â¢ Rust Core</div></aside>}






