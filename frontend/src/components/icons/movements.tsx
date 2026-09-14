import React from 'react';
export const movements = (c: string, a: string) => (<>
  <line x1="4" y1="8" x2="20" y2="8" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
  <polyline points="7,4 4,8 7,12" fill="none" stroke={a} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  <polyline points="17,12 20,8 17,4" fill="none" stroke={a} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
</>);
