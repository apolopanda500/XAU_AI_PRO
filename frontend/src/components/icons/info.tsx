import React from 'react';
export const info = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="9" fill="none" stroke={c} strokeWidth="1.5" />
  <line x1="12" y1="11" x2="12" y2="17" stroke={a} strokeWidth="2" strokeLinecap="round" />
  <circle cx="12" cy="8" r="1.2" fill={a} />
</>);
