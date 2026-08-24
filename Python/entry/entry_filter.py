"""
XAU_AI_PRO - Entry Filter
V1.0

Responsabilidades:
- Filtrar entradas de baixa qualidade
- Responder: "Esta operação possui vantagem estatística?"
- Reduzir número de operações, melhorando a qualidade
- Usar múltiplos critérios de validação

Critérios de qualidade:
1. Confiança do modelo (probabilidade)
2. RSI (evitar sobrecompra/sobrevenda extremos)
3. ADX (tendência forte)
4. ATR (volatilidade adequada)
5. Volume (liquidez)
6. Spread (custo de execução)
7. Consistência histórica (vantagem estatística)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.ENTRY")


# ============================================================
# CONFIG
# ============================================================


@dataclass
class EntryConfig:
    """
    Configuração do filtro de entradas.

    Valores padrão conservadores para reduzir
    o número de operações e melhorar a qualidade.
    """

    # --------------------------------------------------------
    # CONFIANÇA DO MODELO
    # --------------------------------------------------------

    min_confidence: float = 0.65  # confiança mínima do modelo
    min_score: float = 65.0  # score mínimo (0-100)

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi_min: float = 30.0  # RSI mínimo para BUY
    rsi_max: float = 70.0  # RSI máximo para SELL

    # --------------------------------------------------------
    # ADX (TENDÊNCIA)
    # --------------------------------------------------------

    min_adx: float = 20.0  # ADX mínimo para tendência

    # --------------------------------------------------------
    # ATR (VOLATILIDADE)
    # --------------------------------------------------------

    min_atr_pct: float = 0.05  # ATR mínimo (% do preço)
    max_atr_pct: float = 5.0  # ATR máximo (% do preço)

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    min_volume_ratio: float = 0.8  # volume mínimo relativo

    # --------------------------------------------------------
    # SPREAD
    # --------------------------------------------------------

    max_spread_pct: float = 0.5  # spread máximo (% do preço)

    # --------------------------------------------------------
    # VANTAGEM ESTATÍSTICA
    # --------------------------------------------------------

    min_historical_win_rate: float = 0.52  # win rate mínimo histórico
    min_historical_trades: int = 20  # trades mínimos para validar

    # --------------------------------------------------------
    # PERSISTÊNCIA
    # --------------------------------------------------------

    stats_file: str | Path | None = None

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    def validate(self) -> None:
        """Valida os valores da configuração."""

        if not 0.0 < self.min_confidence < 1.0:
            raise ValueError("min_confidence deve estar entre 0 e 1.")

        if not 0.0 < self.min_score < 100.0:
            raise ValueError("min_score deve estar entre 0 e 100.")

        if not 0.0 < self.rsi_min < self.rsi_max < 100.0:
            raise ValueError("RSI inválido: rsi_min < rsi_max.")

        if self.min_adx < 0:
            raise ValueError("min_adx deve ser >= 0.")

        if self.min_atr_pct <= 0:
            raise ValueError("min_atr_pct deve ser > 0.")

        if self.max_atr_pct <= self.min_atr_pct:
            raise ValueError("max_atr_pct deve ser > min_atr_pct.")

        if self.min_volume_ratio <= 0:
            raise ValueError("min_volume_ratio deve ser > 0.")

        if self.max_spread_pct <= 0:
            raise ValueError("max_spread_pct deve ser > 0.")

        if not 0.0 < self.min_historical_win_rate < 1.0:
            raise ValueError("min_historical_win_rate deve estar entre 0 e 1.")

        if self.min_historical_trades < 1:
            raise ValueError("min_historical_trades deve ser >= 1.")


# ============================================================
# DECISION
# ============================================================


@dataclass
class EntryDecision:
    """
    Decisão de qualidade de entrada.

    allow: True = entrada de qualidade, False = rejeitada
    reason: motivo da rejeição (se houver)
    score: score de qualidade (0-100)
    checks: detalhes de cada verificação
    """

    allow: bool
    reason: str = ""
    score: float = 0.0
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""

        return {
            "allow": self.allow,
            "reason": self.reason,
            "score": self.score,
            "checks": self.checks,
        }


# ============================================================
# ENTRY FILTER
# ============================================================


class EntryFilter:
    """
    Filtro de qualidade de entradas.

    Uso:

        config = EntryConfig()
        filter = EntryFilter(config)

        decision = filter.evaluate(
            symbol="XAUUSDc",
            signal="BUY",
            confidence=0.75,
            rsi=45.0,
            adx=25.0,
            atr_pct=0.5,
            volume_ratio=1.2,
            spread_pct=0.1,
        )

        if decision.allow:
            # executar operação
            pass
    """

    def __init__(
        self,
        config: EntryConfig | None = None,
    ) -> None:

        self.config = config if config is not None else EntryConfig()

        self.config.validate()

        # ----------------------------------------------------
        # ESTATÍSTICAS HISTÓRICAS POR SÍMBOLO
        # ----------------------------------------------------

        self.symbol_stats: dict[
            str,
            dict[str, Any],
        ] = {}

        self._load_stats()

    # ========================================================
    # AVALIAÇÃO
    # ========================================================

    def evaluate(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        rsi: float | None = None,
        adx: float | None = None,
        atr_pct: float | None = None,
        volume_ratio: float | None = None,
        spread_pct: float | None = None,
    ) -> EntryDecision:
        """
        Avalia a qualidade de uma entrada.

        Retorna EntryDecision com allow=True apenas
        se TODOS os critérios forem satisfeitos.
        """

        normalized_symbol = symbol.strip().upper()

        normalized_signal = signal.strip().upper()

        checks: dict[
            str,
            dict[str, Any],
        ] = {}

        # ----------------------------------------------------
        # 1. CONFIANÇA DO MODELO
        # ----------------------------------------------------

        confidence_check = self._check_confidence(confidence)

        checks["confidence"] = confidence_check

        # ----------------------------------------------------
        # 2. RSI
        # ----------------------------------------------------

        rsi_check = self._check_rsi(
            rsi,
            normalized_signal,
        )

        checks["rsi"] = rsi_check

        # ----------------------------------------------------
        # 3. ADX (TENDÊNCIA)
        # ----------------------------------------------------

        adx_check = self._check_adx(adx)

        checks["adx"] = adx_check

        # ----------------------------------------------------
        # 4. ATR (VOLATILIDADE)
        # ----------------------------------------------------

        atr_check = self._check_atr(atr_pct)

        checks["atr"] = atr_check

        # ----------------------------------------------------
        # 5. VOLUME
        # ----------------------------------------------------

        volume_check = self._check_volume(volume_ratio)

        checks["volume"] = volume_check

        # ----------------------------------------------------
        # 6. SPREAD
        # ----------------------------------------------------

        spread_check = self._check_spread(spread_pct)

        checks["spread"] = spread_check

        # ----------------------------------------------------
        # 7. VANTAGEM ESTATÍSTICA
        # ----------------------------------------------------

        edge_check = self._check_statistical_edge(
            normalized_symbol,
            normalized_signal,
        )

        checks["statistical_edge"] = edge_check

        # ----------------------------------------------------
        # SCORE DE QUALIDADE
        # ----------------------------------------------------

        score = self._calculate_score(checks)

        # ----------------------------------------------------
        # DECISÃO FINAL
        # ----------------------------------------------------

        failed = [
            name for name, check in checks.items() if not check.get("passed", False)
        ]

        if failed:

            return EntryDecision(
                allow=False,
                reason=("Entrada rejeitada. " "Critérios falhos: " + ", ".join(failed)),
                score=score,
                checks=checks,
            )

        return EntryDecision(
            allow=True,
            reason=("Entrada de qualidade. " "Vantagem estatística confirmada."),
            score=score,
            checks=checks,
        )

    # ========================================================
    # VERIFICAÇÕES INDIVIDUAIS
    # ========================================================

    def _check_confidence(
        self,
        confidence: float,
    ) -> dict[str, Any]:
        """Verifica a confiança do modelo."""

        if confidence is None:
            return {
                "passed": False,
                "value": None,
                "required": self.config.min_confidence,
                "message": "Confiança não informada.",
            }

        passed = confidence >= self.config.min_confidence

        return {
            "passed": passed,
            "value": confidence,
            "required": self.config.min_confidence,
            "message": (
                "Confiança suficiente."
                if passed
                else (
                    f"Confiança baixa: {confidence:.2f} "
                    f"(mínimo: "
                    f"{self.config.min_confidence:.2f})"
                )
            ),
        }

    def _check_rsi(
        self,
        rsi: float | None,
        signal: str,
    ) -> dict[str, Any]:
        """Verifica RSI para evitar extremos."""

        if rsi is None:
            return {
                "passed": True,
                "value": None,
                "message": "RSI não informado, ignorado.",
            }

        if signal == "BUY":

            passed = rsi >= self.config.rsi_min

            message = (
                "RSI adequado para BUY."
                if passed
                else (
                    f"RSI {rsi:.1f} abaixo do mínimo "
                    f"{self.config.rsi_min:.1f} para BUY."
                )
            )

        elif signal == "SELL":

            passed = rsi <= self.config.rsi_max

            message = (
                "RSI adequado para SELL."
                if passed
                else (
                    f"RSI {rsi:.1f} acima do máximo "
                    f"{self.config.rsi_max:.1f} para SELL."
                )
            )

        else:

            passed = True
            message = "Sinal não é BUY/SELL, RSI ignorado."

        return {
            "passed": passed,
            "value": rsi,
            "required": (f"{self.config.rsi_min}-{self.config.rsi_max}"),
            "message": message,
        }

    def _check_adx(
        self,
        adx: float | None,
    ) -> dict[str, Any]:
        """Verifica ADX para tendência."""

        if adx is None:
            return {
                "passed": True,
                "value": None,
                "message": "ADX não informado, ignorado.",
            }

        passed = adx >= self.config.min_adx

        return {
            "passed": passed,
            "value": adx,
            "required": self.config.min_adx,
            "message": (
                "Tendência forte."
                if passed
                else (
                    f"ADX {adx:.1f} abaixo do mínimo "
                    f"{self.config.min_adx:.1f}. "
                    "Mercado sem tendência."
                )
            ),
        }

    def _check_atr(
        self,
        atr_pct: float | None,
    ) -> dict[str, Any]:
        """Verifica ATR para volatilidade adequada."""

        if atr_pct is None:
            return {
                "passed": True,
                "value": None,
                "message": "ATR não informado, ignorado.",
            }

        passed = self.config.min_atr_pct <= atr_pct <= self.config.max_atr_pct

        return {
            "passed": passed,
            "value": atr_pct,
            "required": (f"{self.config.min_atr_pct}-" f"{self.config.max_atr_pct}"),
            "message": (
                "Volatilidade adequada."
                if passed
                else (
                    f"ATR {atr_pct:.2f}% fora do intervalo "
                    f"{self.config.min_atr_pct}%-"
                    f"{self.config.max_atr_pct}%."
                )
            ),
        }

    def _check_volume(
        self,
        volume_ratio: float | None,
    ) -> dict[str, Any]:
        """Verifica volume relativo."""

        if volume_ratio is None:
            return {
                "passed": True,
                "value": None,
                "message": "Volume não informado, ignorado.",
            }

        passed = volume_ratio >= self.config.min_volume_ratio

        return {
            "passed": passed,
            "value": volume_ratio,
            "required": self.config.min_volume_ratio,
            "message": (
                "Volume adequado."
                if passed
                else (
                    f"Volume {volume_ratio:.2f} abaixo do mínimo "
                    f"{self.config.min_volume_ratio:.2f}."
                )
            ),
        }

    def _check_spread(
        self,
        spread_pct: float | None,
    ) -> dict[str, Any]:
        """Verifica spread."""

        if spread_pct is None:
            return {
                "passed": True,
                "value": None,
                "message": "Spread não informado, ignorado.",
            }

        passed = spread_pct <= self.config.max_spread_pct

        return {
            "passed": passed,
            "value": spread_pct,
            "required": self.config.max_spread_pct,
            "message": (
                "Spread adequado."
                if passed
                else (
                    f"Spread {spread_pct:.2f}% acima do máximo "
                    f"{self.config.max_spread_pct:.2f}%."
                )
            ),
        }

    def _check_statistical_edge(
        self,
        symbol: str,
        signal: str,
    ) -> dict[str, Any]:
        """
        Verifica se o símbolo possui vantagem estatística
        com base no histórico de operações.
        """

        stats = self.symbol_stats.get(
            symbol,
            {},
        )

        signal_stats = stats.get(
            signal,
            {},
        )

        trades = int(
            signal_stats.get(
                "trades",
                0,
            )
        )

        win_rate = float(
            signal_stats.get(
                "win_rate",
                0.0,
            )
        )

        # ----------------------------------------------------
        # SEM HISTÓRICO SUFICIENTE
        # ----------------------------------------------------

        if trades < self.config.min_historical_trades:

            return {
                "passed": True,
                "value": {
                    "trades": trades,
                    "win_rate": win_rate,
                },
                "required": {
                    "min_trades": (self.config.min_historical_trades),
                    "min_win_rate": (self.config.min_historical_win_rate),
                },
                "message": (
                    f"Histórico insuficiente "
                    f"({trades} trades). "
                    "Aguardando mais dados."
                ),
            }

        # ----------------------------------------------------
        # HISTÓRICO SUFICIENTE
        # ----------------------------------------------------

        passed = win_rate >= self.config.min_historical_win_rate

        return {
            "passed": passed,
            "value": {
                "trades": trades,
                "win_rate": win_rate,
            },
            "required": {
                "min_trades": (self.config.min_historical_trades),
                "min_win_rate": (self.config.min_historical_win_rate),
            },
            "message": (
                "Vantagem estatística confirmada."
                if passed
                else (
                    f"Win rate {win_rate:.2f} abaixo do mínimo "
                    f"{self.config.min_historical_win_rate:.2f} "
                    f"em {trades} trades."
                )
            ),
        }

    # ========================================================
    # SCORE
    # ========================================================

    def _calculate_score(
        self,
        checks: dict[str, dict[str, Any]],
    ) -> float:
        """
        Calcula score de qualidade (0-100).

        Cada critério vale 100/7 pontos.
        """

        total_checks = len(checks)

        if total_checks == 0:
            return 0.0

        passed_checks = sum(
            1 for check in checks.values() if check.get("passed", False)
        )

        score = passed_checks / total_checks * 100.0

        return round(score, 2)

    # ========================================================
    # REGISTRO DE RESULTADO
    # ========================================================

    def record_result(
        self,
        symbol: str,
        signal: str,
        won: bool,
    ) -> None:
        """
        Registra o resultado de uma operação
        para atualizar a vantagem estatística.
        """

        normalized_symbol = symbol.strip().upper()

        normalized_signal = signal.strip().upper()

        stats = self.symbol_stats.setdefault(
            normalized_symbol,
            {},
        )

        signal_stats = stats.setdefault(
            normalized_signal,
            {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
            },
        )

        signal_stats["trades"] += 1

        if won:
            signal_stats["wins"] += 1
        else:
            signal_stats["losses"] += 1

        signal_stats["win_rate"] = signal_stats["wins"] / signal_stats["trades"]

        self._save_stats()

        logger.info(
            "Resultado registrado | %s | %s | " "won=%s | win_rate=%.2f",
            normalized_symbol,
            normalized_signal,
            won,
            signal_stats["win_rate"],
        )

    # ========================================================
    # PERSISTÊNCIA
    # ========================================================

    def _stats_path(self) -> Path:
        """Retorna o caminho do arquivo de estatísticas."""

        if self.config.stats_file is not None:
            return Path(self.config.stats_file).expanduser()

        return Path(__file__).resolve().parent / "entry_stats.json"

    def _save_stats(self) -> None:
        """Salva estatísticas em JSON."""

        path = self._stats_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                self.symbol_stats,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load_stats(self) -> None:
        """Carrega estatísticas de JSON se existir."""

        path = self._stats_path()

        if not path.exists():
            return

        try:

            self.symbol_stats = json.loads(path.read_text(encoding="utf-8"))

            logger.info(
                "Estatísticas de entrada carregadas: %s",
                path,
            )

        except Exception as exc:

            logger.warning(
                "Não foi possível carregar estatísticas: %s",
                exc,
            )

    # ========================================================
    # STATUS
    # ========================================================

    def status(self) -> dict[str, Any]:
        """
        Retorna o status do filtro de entradas.
        """

        return {
            "min_confidence": self.config.min_confidence,
            "min_score": self.config.min_score,
            "rsi_range": [
                self.config.rsi_min,
                self.config.rsi_max,
            ],
            "min_adx": self.config.min_adx,
            "atr_range": [
                self.config.min_atr_pct,
                self.config.max_atr_pct,
            ],
            "min_volume_ratio": self.config.min_volume_ratio,
            "max_spread_pct": self.config.max_spread_pct,
            "min_historical_win_rate": (self.config.min_historical_win_rate),
            "min_historical_trades": (self.config.min_historical_trades),
            "symbols": sorted(self.symbol_stats.keys()),
        }


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(" XAU_AI_PRO ENTRY FILTER")
    print("=" * 70)
    print()

    config = EntryConfig()

    entry_filter = EntryFilter(config)

    print("Status:")
    print(entry_filter.status())
    print()

    # --------------------------------------------------------
    # TESTE 1: ENTRADA DE QUALIDADE
    # --------------------------------------------------------

    decision = entry_filter.evaluate(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.75,
        rsi=45.0,
        adx=25.0,
        atr_pct=0.5,
        volume_ratio=1.2,
        spread_pct=0.1,
    )

    print("Decisão 1 (entrada de qualidade):")
    print(decision.to_dict())
    print()

    # --------------------------------------------------------
    # TESTE 2: ENTRADA DE BAIXA QUALIDADE
    # --------------------------------------------------------

    decision = entry_filter.evaluate(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.50,
        rsi=80.0,
        adx=10.0,
        atr_pct=0.01,
        volume_ratio=0.3,
        spread_pct=2.0,
    )

    print("Decisão 2 (entrada de baixa qualidade):")
    print(decision.to_dict())
    print()

    # --------------------------------------------------------
    # TESTE 3: REGISTRO DE RESULTADOS
    # --------------------------------------------------------

    for i in range(25):

        entry_filter.record_result(
            symbol="XAUUSDc",
            signal="BUY",
            won=(i % 2 == 0),
        )

    print("Após 25 resultados:")
    print(entry_filter.status())
    print()

    print("=" * 70)
