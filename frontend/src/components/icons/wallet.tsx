import React from 'react';
export const wallet = (c: string, a: string) => (<>
  <rect x="3" y="6" width="18" height="13" rx="2" fill="none" stroke={c} strokeWidth="1.5" />
  <rect x="15" y="10" width="4" height="3" rx="1" fill={a} opacity="0.7" />
  <line x1="3" y1="10" x2="21" y2="10" stroke={c} strokeWidth="1" />
</>);
