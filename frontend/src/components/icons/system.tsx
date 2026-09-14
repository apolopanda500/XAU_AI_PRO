import React from 'react';
export const system = (c: string, a: string) => (<>
  <rect x="3" y="4" width="18" height="12" rx="2" fill="none" stroke={c} strokeWidth="1.5" />
  <line x1="8" y1="20" x2="16" y2="20" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
  <line x1="12" y1="16" x2="12" y2="20" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
  <circle cx="12" cy="10" r="2" fill={a} />
</>);
