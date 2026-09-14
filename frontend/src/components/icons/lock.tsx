import React from 'react';
export const lock = (c: string, a: string) => (<>
  <rect x="5" y="11" width="14" height="9" rx="2" fill="none" stroke={c} strokeWidth="1.5" />
  <path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke={a} strokeWidth="1.5" strokeLinecap="round" />
  <circle cx="12" cy="15.5" r="1.5" fill={c} />
</>);
