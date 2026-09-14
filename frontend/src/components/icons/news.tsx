import React from 'react';
export const news = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="9" fill="none" stroke={c} strokeWidth="1.5" />
  <ellipse cx="12" cy="12" rx="4" ry="9" fill="none" stroke={c} strokeWidth="1" opacity="0.6" />
  <line x1="3" y1="8" x2="21" y2="8" stroke={a} strokeWidth="1" opacity="0.7" />
  <line x1="3" y1="12" x2="21" y2="12" stroke={a} strokeWidth="1" opacity="0.7" />
  <line x1="3" y1="16" x2="21" y2="16" stroke={a} strokeWidth="1" opacity="0.7" />
</>);
