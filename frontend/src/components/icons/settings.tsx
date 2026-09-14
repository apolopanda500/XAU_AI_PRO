import React from 'react';
export const settings = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="3" fill="none" stroke={c} strokeWidth="1.5" />
  <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
</>);
