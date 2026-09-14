import React from 'react';
export const charts = (c: string, a: string) => (<>
  <line x1="4" y1="20" x2="20" y2="20" stroke={c} strokeWidth="0.5" />
  <rect x="6" y="10" width="3" height="10" fill={c} rx="0.5" />
  <rect x="11" y="6" width="3" height="14" fill={a} rx="0.5" />
  <rect x="16" y="13" width="3" height="7" fill={c} rx="0.5" opacity="0.7" />
</>);
