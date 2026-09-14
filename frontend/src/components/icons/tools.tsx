import React from 'react';
export const tools = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="4" fill="none" stroke={c} strokeWidth="1.5" />
  <line x1="12" y1="2" x2="12" y2="5" stroke={c} strokeWidth="2" strokeLinecap="round" />
  <line x1="12" y1="19" x2="12" y2="22" stroke={c} strokeWidth="2" strokeLinecap="round" />
  <line x1="2" y1="12" x2="5" y2="12" stroke={c} strokeWidth="2" strokeLinecap="round" />
  <line x1="19" y1="12" x2="22" y2="12" stroke={c} strokeWidth="2" strokeLinecap="round" />
</>);
