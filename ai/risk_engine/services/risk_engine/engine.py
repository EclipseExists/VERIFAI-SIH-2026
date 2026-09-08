"""Risk Engine Service — Core Scoring Logic.

Adapted from teammate's code. All imports self-contained.
"""

from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from ai.risk_engine.core.risk_config import RiskEngineConfig, default_risk_config
from ai.risk_engine.schemas.risk import (
    RiskAssessment,
    RiskBand,
    RiskSignal,
    SignalDirection,
)


def get_direction_multiplier(direction: SignalDirection) -> float:
    if direction == SignalDirection.INCREASES_RISK:
        return 1.0
    elif direction == SignalDirection.DECREASES_RISK:
        return -1.0
    return 0.0


class RiskEngine:
    """Stateless deterministic risk aggregation engine."""

    def __init__(self, config: Optional[RiskEngineConfig] = None):
        self.config = config or default_risk_config

    def calculate_signal_contribution(self, signal: RiskSignal) -> float:
        multiplier = get_direction_multiplier(signal.direction)
        raw_weight = self.config.get_weight(signal.signal_name)
        return multiplier * signal.magnitude * abs(raw_weight)

    def evaluate(
        self,
        case_id: Union[UUID, str],
        signals: Optional[List[RiskSignal]] = None,
    ) -> RiskAssessment:
        signal_list = signals or []

        if not signal_list:
            return RiskAssessment(
                case_id=case_id,
                overall_score=0.0,
                risk_band=RiskBand.LOW,
                contributing_signals=[],
            )

        raw_score = sum(self.calculate_signal_contribution(s) for s in signal_list)
        clamped = max(self.config.min_score, min(self.config.max_score, raw_score))
        final_score = round(clamped, 2)
        risk_band = self.config.get_risk_band(final_score)

        sorted_signals = sorted(
            signal_list,
            key=lambda s: abs(s.magnitude * abs(self.config.get_weight(s.signal_name))),
            reverse=True,
        )

        return RiskAssessment(
            case_id=case_id,
            overall_score=final_score,
            risk_band=risk_band,
            contributing_signals=sorted_signals,
        )
