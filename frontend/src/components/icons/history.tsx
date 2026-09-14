import React from 'react';
export const history = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="9" fill="none" stroke={c} strokeWidth="1.5" />
  <polyline points="12,6 12,12 16,14" fill="none" stroke={a} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
</>);
