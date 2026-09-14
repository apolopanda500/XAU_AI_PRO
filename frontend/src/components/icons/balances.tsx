import React from 'react';
export const balances = (c: string, a: string) => (<>
  <line x1="12" y1="4" x2="12" y2="20" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
  <line x1="12" y1="4" x2="7" y2="9" stroke={a} strokeWidth="1.5" strokeLinecap="round" />
  <line x1="12" y1="4" x2="17" y2="9" stroke={a} strokeWidth="1.5" strokeLinecap="round" />
  <rect x="5" y="10" width="14" height="2" rx="1" fill={c} opacity="0.7" />
  <rect x="4" y="18" width="16" height="2" rx="1" fill={c} />
</>);
