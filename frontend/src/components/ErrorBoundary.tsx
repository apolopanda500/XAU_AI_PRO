// Barreira de erro por painel.
//
// POR QUE ISTO EXISTE
// ===================
// A aba Robo monta oito paineis. Sem uma barreira, UM erro de render em
// qualquer um deles desmonta a arvore React inteira: a aba fica branca e o
// usuario perde o app inteiro, sem dizer qual painel falhou. Foi exatamente
// o que aconteceu — "tudo some".
//
// Com a barreira, o painel que falha mostra o que houve e o resto da aba
// continua funcionando. O erro NAO fica escondido: o nome do painel e a
// mensagem vao para o console, para o log e para a tela.
import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { nome: string; children: ReactNode };
type State = { erro: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { erro: null };

  static getDerivedStateFromError(erro: Error): State {
    return { erro };
  }

  componentDidCatch(erro: Error, info: ErrorInfo): void {
    // `console.error` mantem o stack no DevTools do webview, que e onde se
    // descobre a causa real.
    console.error(`[${this.props.nome}] falhou ao renderizar`, erro, info.componentStack);
  }

  render(): ReactNode {
    const { erro } = this.state;
    if (!erro) return this.props.children;
    return (
      <section className="card compact-card panel-error" role="alert">
        <strong>{this.props.nome} indisponivel</strong>
        <p className="muted">{erro.message}</p>
        <button
          className="btn xs ghost"
          type="button"
          onClick={() => this.setState({ erro: null })}
        >
          Tentar de novo
        </button>
      </section>
    );
  }
}
