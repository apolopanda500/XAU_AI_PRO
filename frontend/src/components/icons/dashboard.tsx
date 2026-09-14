import React from 'react';
export const dashboard = (c: string, a: string) => (<>
  <rect x="3" y="3" width="6" height="6" rx="1" fill={c} />
  <rect x="15" y="3" width="6" height="6" rx="1" fill={c} opacity="0.7" />
  <rect x="3" y="15" width="6" height="6" rx="1" fill={c} opacity="0.7" />
  <rect x="15" y="15" width="6" height="6" rx="1" fill={c} />
  <circle cx="6" cy="6" r="1" fill="#fff" />
  <circle cx="18" cy="18" r="1" fill="#fff" />
</>);
