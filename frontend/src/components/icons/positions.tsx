import React from 'react';
export const positions = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="9" fill="none" stroke={c} strokeWidth="1.5" />
  <circle cx="12" cy="12" r="6" fill="none" stroke={c} strokeWidth="1" opacity="0.6" />
  <circle cx="12" cy="12" r="2" fill={a} />
  <line x1="12" y1="3" x2="12" y2="6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
</>);
