import React from 'react';
export const robot = (c: string, a: string) => (<>
  <rect x="6" y="8" width="12" height="10" rx="2" fill="none" stroke={c} strokeWidth="1.5" />
  <circle cx="10" cy="12" r="1.5" fill={a} />
  <circle cx="14" cy="12" r="1.5" fill={a} />
  <line x1="12" y1="4" x2="12" y2="8" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
  <circle cx="12" cy="3" r="1.5" fill={c} />
</>);
