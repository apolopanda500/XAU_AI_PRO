import React from 'react';
export const strategy = (c: string, a: string) => (<>
  <circle cx="6" cy="6" r="2" fill={c} />
  <circle cx="18" cy="6" r="2" fill={a} />
  <circle cx="12" cy="18" r="2" fill={c} />
  <line x1="6" y1="8" x2="11" y2="16" stroke={c} strokeWidth="1" opacity="0.7" />
  <line x1="18" y1="8" x2="13" y2="16" stroke={a} strokeWidth="1" opacity="0.7" />
</>);
