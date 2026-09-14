import React from 'react';
export const calendar = (c: string, a: string) => (<>
  <rect x="3" y="5" width="18" height="16" rx="2" fill="none" stroke={c} strokeWidth="1.5" />
  <line x1="3" y1="10" x2="21" y2="10" stroke={c} strokeWidth="1" />
  <line x1="8" y1="3" x2="8" y2="7" stroke={a} strokeWidth="1.5" strokeLinecap="round" />
  <line x1="16" y1="3" x2="16" y2="7" stroke={a} strokeWidth="1.5" strokeLinecap="round" />
  <circle cx="12" cy="15" r="2" fill={c} />
</>);
