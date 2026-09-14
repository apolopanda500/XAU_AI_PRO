import React from 'react';

/** Widget compacto sem dados inventados; fontes reais entram pelo Core. */
export const MiniInfoWidget: React.FC = () => (
  <div className="mini-info-widget">
    <div className="mini-item">
      <span className="mini-label">DADOS EXTERNOS</span>
      <span className="muted">Aguardando fontes reais conectadas.</span>
    </div>
  </div>
);

export default MiniInfoWidget;
