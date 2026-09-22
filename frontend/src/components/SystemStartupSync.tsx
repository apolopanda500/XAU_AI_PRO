import { useEffect } from 'react';
import { apiBase } from '../lib/api';
const API=`${apiBase()}`;
export default function SystemStartupSync(){useEffect(()=>{let active=true;const check=async()=>{try{await fetch(`${API}/api/health`,{signal:AbortSignal.timeout(3000)});if(active)window.dispatchEvent(new CustomEvent('xau-system-sync',{detail:{at:Date.now()}}));}catch{/* estado fica explícito na aba Sistema */}};void check();const timer=window.setInterval(()=>void check(),30000);return()=>{active=false;window.clearInterval(timer)}},[]);return null}
