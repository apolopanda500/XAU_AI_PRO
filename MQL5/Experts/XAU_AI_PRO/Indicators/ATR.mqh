// XAU_AI_PRO v1.2.9
#ifndef ATR_MQH
#define ATR_MQH

// P2.11 (03/11/2026): este header era um stub vazio - apenas apontava para
// Indicators/VolatilityFilter.mqh. O efeito colateral medido: Core/Config.mqh
// usa GetATR(symbol) em NoiseDistancePointsForRisk() (linha 1181) e no
// envelope de risco stopless (linha 1336), mas nao declarava a funcao.
// Compilar Config.mqh ISOLADO (Ctrl+F7 sobre o ficheiro) dava:
//    undeclared identifier 'GetATR'       Config.mqh 1181 26
//    'sym' - some operator expected       Config.mqh 1181 33
//    undeclared identifier 'GetATR'       Config.mqh 1336 18
//    'symbol' - some operator expected    Config.mqh 1336 25
// Dentro do EA o defeito ficava escondido: o pre-scan do TU encontrava a
// definicao em VolatilityFilter.mqh, que o .mq5 inclui.
//
// Passa a ser a INTERFACE do ATR: as assinaturas ficam aqui e a
// implementacao continua em Indicators/VolatilityFilter.mqh. Assim qualquer
// modulo declara a dependencia sem arrastar o handle e os buffers globais do
// filtro. Nao ha ciclo: VolatilityFilter.mqh nao inclui nada.

double GetATR();
double GetATR(string symbol);
double GetATRPoints();

#endif
