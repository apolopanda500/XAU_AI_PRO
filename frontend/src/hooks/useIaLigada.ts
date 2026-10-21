import { create } from 'zustand';

/**
 * A IA LIGADA OU NAO — e o estado que NAO pode morrer na troca de aba.
 *
 * O DEFEITO MEDIDO (09/10/2026)
 * =============================
 * O dono reportou: "quando desligo e volto novamente ele desliga".
 *
 * MEDIDO no fonte: `iaLigada` era `useState(false)` DENTRO de
 * `OperacaoAutomatica.tsx`. A aba ROBÔ monta esse componente inteiro; sair da
 * aba desmonta, e voltar monta de novo — com `useState(false)` do zero. O
 * interruptor voltava a "desligada" so pela navegacao, e o operador via a IA
 * apagada sem ter apagado nada.
 *
 * Nao era so a tela: `useInferenciaIA(timeframe, iaLigada)` usa o interruptor
 * para decidir se chama o gateway. Com o estado zerado, a inferencia PARAVA de
 * rodar no cliente — e voltava a correr so se o operador religasse, sem saber
 * que tinha parado.
 *
 * POR QUE UM STORE A PARTE, E NAO O `useAppStore`
 * ===============================================
 * O `useAppStore` tem `persist` (line 277): o que entra la sobrevive ao
 * REINICIO do app, porque vai para o `localStorage`.
 *
 * A IA comeca DESLIGADA de proposito (ver o comentario em `OperacaoAutomatica`
 * acima do interruptor): inferencia consome CPU e escreve estado, e ligar isso
 * sozinho na abertura e decidir pelo operador. Se `iaLigada` entrasse no store
 * persistido, elavoltaria ligada no proximo dia — exatamente o que aquele
 * comentario proibe.
 *
 * Este store NAO tem `persist`: vive enquanto o app vive. Sobrevive a troca de
 * aba e morre com o app. E o escopo certo: a escolha vale para esta sessao, e
 * cada sessao comeca desligada.
 *
 * A IA nao e o estado do MOTOR: o liga/desliga do motor vem de
 * `useAutoState()`, que consulta `/api/auto/state` a cada 5s e tem cache no
 * `QueryClient` do root — esse ja sobrevivia a troca de aba. O que nao
 * sobrevivia era so este interruptor do cliente.
 */
type IaLigada = {
  ligada: boolean;
  /** Liga ou desliga. Recebe o valor, e nao inverte: quem inverte e o botao. */
  setLigada: (valor: boolean) => void;
};

export const useIaLigada = create<IaLigada>((set) => ({
  ligada: false,
  setLigada: (valor) => set({ ligada: valor }),
}));

/**
 * Zera o interruptor — para teste.
 *
 * MEDIDO (09/10/2026): o store ȁ de MODULO, e o modulo vive enquanto o processo
 * de teste vive. O `useIaLigada.test.tsx` liga a IA e nao desliga; quando a
 * suite roda inteira, o `RobotTabs.test.tsx` herda o `ligada: true` e o teste
 * "AUTO aplica o 1:1 PADRAO e liga o motor" reprova — porque o painel encontrou
 * a inferencia ja ligada e nao passou pelo primeiro clique.

 * E a falha era INTERMITENTE (1 em 3 rodadas), que ȁ a assinatura de estado
 * compartilhado entre arquivos: depende da ordem que o runner escolhe.

 * O reset no `afterEach` de cada arquivo ȁ o que fecha isso. Quem precisa do
 * interruptor ligado dentro de um teste liga de novo.
 */
export function zerarIaLigada(): void {
  useIaLigada.setState({ ligada: false });
}
