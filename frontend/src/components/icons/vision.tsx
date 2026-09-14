import React from 'react';
export const vision = (c: string, a: string) => (<>
  <path d="M2 12s4-8 10-8 10 8 10 8-4 8-10 8-10-8-10-8z" fill="none" stroke={c} strokeWidth="1.5" />
  <circle cx="12" cy="12" r="4" fill="none" stroke={a} strokeWidth="1.5" />
  <circle cx="12" cy="12" r="1.5" fill={c} />
</>);
