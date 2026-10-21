/*
  ICONES DE INTERFACE QUE SUMIRAM (09/10/2026)
  ===========================================
  MEDIDO pelo dono: "tem icones no grafico mas nao da pra ver nada". O grafico
  ja foi corrigido em `charts/IconesGrafico.tsx`. O MESMO defeito estava em tres
  paineis, com tres glifos que a fonte do Windows nao garante:

    `⌁`  ELECTRIC ARROW        ConnectedDevicesPanel  (estado vazio)
    `⏻`  POWER SYMBOL          ExitAppButton          (antes do "Sair")
    `◷`  WHITE CIRCLE UPPER...  LatenciaBar            (antes do texto)

  Glifo que a fonte nao tem vira caractere de substituted — um quadrado do
  tamanho de uma letra. Para o operador e a mesma coisa que um botao vazio: o
  icone some e o texto continua, e parece erro de layout em vez de erro de
  fonte.

  Por que outro arquivo, e nao o do grafico: sao icones de interface, nao do
  grafico. `charts/IconesGrafico.tsx` fica com o que so o grafico usa. O
  criterio do repositorio e nome que diz o que a coisa e.

  Assim como no grafico, o desenho e SVG e usa `currentColor`: renderiza em
  qualquer maquina e segue o tema.
*/

type Props = { className?: string };

/** Um dispositivo: a tela do celular com a antena. Estado "nenhum conectado". */
export function IconeDispositivo({ className }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="7" y="2.5" width="10" height="19" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10.5 5.5h3" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="12" cy="18.6" r="0.9" fill="currentColor" />
      <path
        d="M3.2 8.6a11 11 0 000 6.8M20.8 8.6a11 11 0 010 6.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.75"
      />
    </svg>
  );
}

/**
 * A antena, que era `📡`.
 *
 * Emoji nao serve aqui: o Windows desenha em cor e com dois caracteres de
 * largura, ao lado de icones monocromaticos do mesmo painel. Dois idiomas
 * visuais na mesma linha.
 */
export function IconeSinal({ className }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="12"
      height="12"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="16" r="1.7" fill="currentColor" />
      <path
        d="M8.2 12.8a5.4 5.4 0 010-3.6M15.8 9.2a5.4 5.4 0 010 6.4M5 9.6a10 10 0 010 6.6M19 9.6a10 10 0 010 6.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** O botao de energia: o mesmo arco com a barra vertical. */
export function IconeEnergia({ className }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="14"
      height="14"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M12 3v8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <path
        d="M7.2 6.6a8 8 0 1010.6 0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * Relogio de medicao.
 *
 * Antes era `◷`, um "circulo com um quadrante", que e o caractere mais raro da
 * lista: pertence a um bloco de formas geometricas que a fonte do app nao
 * declara. Um relogio desenhado e lido sem depender de fonte nenhuma.
 */
export function IconeRelogio({ className }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="13"
      height="13"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M12 6.8V12l3.4 2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}