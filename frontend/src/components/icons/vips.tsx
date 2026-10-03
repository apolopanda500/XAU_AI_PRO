import React from 'react';

// Icone de level: coroa de tres pontas. Escolhido em vez de estrela ou
// escudo porque "VIP" aqui e NIVEL de acesso, e coroa comunica nivel sem
// prometer preco. O `a` (acento) marca a ponta central.
export const vips = (c: string, a: string) => (<>
  <path d="M3 18 L3 8 L7.5 12 L12 6 L16.5 12 L21 8 L21 18 Z" fill="none" stroke={c} strokeWidth="1.5" strokeLinejoin="round" />
  <circle cx="12" cy="6" r="1.4" fill={a} />
  <line x1="3" y1="20" x2="21" y2="20" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
</>);