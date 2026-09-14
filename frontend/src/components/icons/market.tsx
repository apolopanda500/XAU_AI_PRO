import React from 'react';
export const market = (c: string, a: string) => (<>
  <polyline points="3,20 8,13 13,16 21,5" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  <circle cx="21" cy="5" r="2" fill={a} />
  <line x1="3" y1="21" x2="21" y2="21" stroke={c} strokeWidth="0.5" opacity="0.5" />
</>);
