"""
LLM prediction gate for AutoPilot.

Before AutoPilot commits capital to a candidate, it can ask an LLM whether the
stock is likely to hit the day's per-trade profit target. This runs in a
synchronous Celery worker context, so we use the *synchronous* OpenAI client
(the app's AIService uses the async client for streaming HTTP responses).

Backends (same precedence as AIService):
  - Groq (Llama 3.3 70B) if GROQ_API_KEY is set — free & fast
  - OpenAI (gpt-4o-mini) if OPENAI_API_KEY is set

The gate degrades gracefully:
  - No API key           → returns a neutral "allow" verdict flagged as no-LLM
  - Malformed response   → neutral verdict, logged
so AutoPilot can still run technicals-only when the LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from config import settings
from autopilot.scanner import Candidate

logger = logging.getLogger(__name__)


@dataclass
class LLMVerdict:
    """The LLM's assessment of a candidate's intraday profit potential."""
    will_hit_target: bool
    predicted_move_pct: float
    confidence: float          # 0–100
    direction: str             # "up" | "down" | "flat"
    reasoning: str
    llm_used: bool = True      # False when we fell back to a neutral verdict

    def to_dict(self) -> dict:
        return {
            "will_hit_target": self.will_hit_target,
            "predicted_move_pct": round(self.predicted_move_pct, 2),
            "confidence": round(self.confidence, 1),
            "direction": self.direction,
            "reasoning": self.reasoning,
            "llm_used": self.llm_used,
        }


_SYSTEM_PROMPT = (
    "You are a disciplined intraday trading analyst. You assess whether a stock "
    "is likely to achieve a specific intraday percentage gain TODAY based on its "
    "current momentum, volume, and technical indicators. You are skeptical and "
    "risk-aware: most stocks do NOT hit aggressive intraday targets, so only "
    "express high confidence when momentum and volume strongly align. "
    "Respond ONLY with a compact JSON object."
)


def _build_prompt(candidate: Candidate, target_pct: float, market_type: str) -> str:
    ind = candidate.indicators or {}
    rsi_val = ind.get("rsi")
    macd_hist = ind.get("macd_hist")
    return (
        f"Stock: {candidate.ticker} ({market_type} market)\n"
        f"Current price: ${candidate.price:.4f}\n"
        f"Intraday change so far: {candidate.change_pct:+.2f}%\n"
        f"Volume ratio (vs avg): {candidate.volume_ratio:.2f}x\n"
        f"RSI(14): {rsi_val if rsi_val is not None else 'n/a'}\n"
        f"MACD histogram: {macd_hist if macd_hist is not None else 'n/a'}\n"
        f"Composite momentum score: {candidate.momentum_score:.0f}/100\n\n"
        f"Question: From the CURRENT price, is {candidate.ticker} likely to rise "
        f"an additional {target_pct:.1f}% intraday today (before market close)?\n\n"
        "Respond with JSON only, exactly this shape:\n"
        "{\n"
        '  "will_hit_target": true|false,\n'
        '  "predicted_move_pct": <number, expected additional % move from now>,\n'
        '  "confidence": <0-100 integer>,\n'
        '  "direction": "up"|"down"|"flat",\n'
        '  "reasoning": "<one concise sentence>"\n'
        "}"
    )


class LLMPredictionGate:
    """Synchronous LLM gate. Instantiate once per executor run."""

    def __init__(self) -> None:
        self.client = None
        self.model = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
        except Exception as exc:  # openai not installed
            logger.warning("openai package unavailable: %s", exc)
            return

        if settings.groq_api_key:
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = "llama-3.3-70b-versatile"
            logger.info("AutoPilot LLM gate using Groq (Llama 3.3 70B)")
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            logger.info("AutoPilot LLM gate using OpenAI (%s)", self.model)
        else:
            logger.info("No LLM API key configured — AutoPilot runs technicals-only.")

    @property
    def available(self) -> bool:
        return self.client is not None

    def predict_intraday_profit(
        self,
        candidate: Candidate,
        target_pct: float,
        market_type: str,
    ) -> LLMVerdict:
        """
        Ask the LLM whether the candidate can gain ``target_pct`` more today.

        Never raises — returns a neutral (allow) verdict on any failure so the
        caller can fall back to technicals-only gating.
        """
        if not self.available:
            return self._neutral(candidate, "LLM unavailable — technicals only")

        prompt = _build_prompt(candidate, target_pct, market_type)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=256,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
            return LLMVerdict(
                will_hit_target=bool(data.get("will_hit_target", False)),
                predicted_move_pct=float(data.get("predicted_move_pct", 0.0)),
                confidence=float(data.get("confidence", 0.0)),
                direction=str(data.get("direction", "flat")),
                reasoning=str(data.get("reasoning", ""))[:300],
                llm_used=True,
            )
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned non-JSON for %s: %s", candidate.ticker, exc)
            return self._neutral(candidate, "LLM parse error — technicals only")
        except Exception as exc:
            logger.warning("LLM prediction failed for %s: %s", candidate.ticker, exc)
            return self._neutral(candidate, f"LLM error: {exc}")

    @staticmethod
    def _neutral(candidate: Candidate, reason: str) -> LLMVerdict:
        """
        Neutral fallback: defer to technicals.

        confidence mirrors the momentum score so downstream gating still has a
        meaningful number, and llm_used=False marks it as not a real LLM call.
        """
        return LLMVerdict(
            will_hit_target=candidate.momentum_score >= 60,
            predicted_move_pct=0.0,
            confidence=candidate.momentum_score,
            direction="up" if candidate.change_pct > 0 else "flat",
            reasoning=reason,
            llm_used=False,
        )
