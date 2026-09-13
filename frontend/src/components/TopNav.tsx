import React from 'react'; import {useAppStore,TabType} from '../hooks/useAppStore';
const tabs:[TabType,string][]=[['dashboard','Painel'],['market','Mercado'],['positions','Carteira'],['charts','GrÃƒÂ¡ficos'],['robot','RobÃƒÂ´'],['strategy-tester','EstratÃƒÂ©gias']];
export default function TopNav({wsConnected}:{activeTab:TabType;onTabChange:(t:TabType)=>void;wsConnected:boolean}){const {activeTab,setActiveTab,robotStatus,aiStatus}=useAppStore(); const [time,setTime]=React.useState(new Date()); React.useEffect(()=>{const id=setInterval(()=>setTime(new Date()),1000);return()=>clearInterval(id)},[]); return <header className="topbar"><div style={{display:'flex',gap:5}}>{tabs.map(([k,l])=><button key={k} className={`btn ${activeTab===k?'primary':''}`} style={{padding:'7px 12px',fontSize:12}} onClick={()=>setActiveTab(k)}>{l}</button>)}</div><div style={{display:'flex',gap:18,alignItems:'center'}}><span className="status"><i className={`dot ${wsConnected?'on':''}`}/> WS {wsConnected?'Online':'Offline'}</span><span className="status">Ã°Å¸Â¤â€“ AI: {aiStatus}</span><span className="status">EA: {robotStatus}</span><span className="muted">{time.toLocaleTimeString('pt-BR')}</span></div></header>}






