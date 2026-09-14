import React from 'react';
export const quantum = (c: string, a: string) => (<>
  <circle cx="12" cy="12" r="3" fill={c} />
  <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke={c} strokeWidth="1" opacity="0.7" />
  <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke={a} strokeWidth="1" opacity="0.7" transform="rotate(60 12 12)" />
  <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke={c} strokeWidth="1" opacity="0.5" transform="rotate(-60 12 12)" />
</>);
