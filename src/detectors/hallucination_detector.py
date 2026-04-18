"""
Hallucination Detector - Pattern-based LLM hallucination signal detection

Version: v1.1 (added English patterns)
License: Apache-2.0

Based on: HalluGuard (ICLR 2026, arXiv: 2601.18753)
Two hallucination types:
1. Data-driven: model fabricates from knowledge gaps
2. Reasoning-driven: errors amplify through long reasoning chains
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class HallucinationType(Enum):
    DATA_DRIVEN = "data_driven"
    REASONING_DRIVEN = "reasoning_driven"
    UNKNOWN = "unknown"


@dataclass
class HallucinationSignal:
    type: HallucinationType
    severity: float  # 0.0-1.0
    description: str
    evidence: str


@dataclass
class _PatternGroup:
    """A group of related detection patterns."""
    patterns: List[str]
    severity: float
    description_template: str


class HallucinationDetector:
    """
    Pattern-based hallucination detector for LLM outputs.

    Supports both Chinese and English text.
    """

    def __init__(self):
        # Data-driven patterns (English + Chinese)
        self._data_knowledge_gap = _PatternGroup(
            patterns=[
                # English
                r"I believe\s.+?should be",
                r"it is reasonable to assume",
                r"probably\s.+?based on",
                r"most likely\s.+?though",
                # Chinese
                r"我相信.*?应该是",
                r"根据.*?推测",
                r"可能是",
            ],
            severity=0.6,
            description_template="Knowledge gap signal: '{}'",
        )
        self._data_bias = _PatternGroup(
            patterns=[
                # English
                r"everyone (?:knows|says|does)",
                r"nobody (?:ever|would|could)",
                r"(?:always|never)\s.+?(?:like|this|way)",
                # Chinese
                r"所有人.*?都",
                r"从来没有",
                r"总是.*?这样",
            ],
            severity=0.7,
            description_template="Overgeneralization bias: '{}'",
        )
        self._data_stale = _PatternGroup(
            patterns=[
                # English
                r"according to\s+\d{4}\s+(?:data|study|report).*?(?:currently|now|today)",
                r"in\s+\w+(?: region| area| country).*?(?:same|also|everywhere)",
                # Chinese
                r"根据.*?年.*?的数据.*?现在.*?",
                r"在.*?地区.*?也是.*?",
            ],
            severity=0.8,
            description_template="Stale data / distribution mismatch: '{}'",
        )

        self.data_driven_groups = [
            self._data_knowledge_gap,
            self._data_bias,
            self._data_stale,
        ]

        # Reasoning-driven patterns (English + Chinese)
        self._reasoning_chain = _PatternGroup(
            patterns=[
                # English
                r"first\s.+?then\s.+?therefore",
                r"since\s.+?it follows\s.+?thus",
                r"if\s.+?then\s.+?which means\s.+?so",
                # Chinese
                r"首先.*?那么.*?然后.*?因此",
                r"那么.*?然后.*?那么",
                r"因此.*?所以.*?因此",
            ],
            severity=0.6,
            description_template="Multi-step reasoning chain: '{}'",
        )
        self._reasoning_contradiction = _PatternGroup(
            patterns=[
                # English
                r"although\s.+?however\s.+?nevertheless",
                r"on one hand\s.+?on the other hand\s.+?but",
                # Chinese
                r"虽然.*?但是.*?然而",
                r"一方面.*?另一方面.*?但是",
            ],
            severity=0.7,
            description_template="Logical inconsistency: '{}'",
        )
        self._reasoning_overconfidence = _PatternGroup(
            patterns=[
                # English
                r"(?:definitely|absolutely|certainly)\s.+?(?:must|will|always)",
                r"without (?:a )?doubt",
                r"it is (?:obvious|clear|evident) that",
                # Chinese
                r"肯定.*?必然",
                r"毫无疑问",
                r"显而易见",
            ],
            severity=0.8,
            description_template="Overconfidence amplification: '{}'",
        )

        self.reasoning_driven_groups = [
            self._reasoning_chain,
            self._reasoning_contradiction,
            self._reasoning_overconfidence,
        ]

    def _check_group(self, text: str, group: _PatternGroup) -> List[HallucinationSignal]:
        """Check text against a pattern group."""
        signals = []
        for pattern in group.patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.DATA_DRIVEN,
                    severity=group.severity,
                    description=group.description_template.format(matches[0]),
                    evidence=f"Pattern: {pattern}, Match: {matches[0]}",
                ))
        return signals

    def detect_data_driven(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HallucinationSignal]:
        """Detect data-driven hallucination signals."""
        signals = []
        for group in self.data_driven_groups:
            signals.extend(self._check_group(text, group))
            # Correct type assignment
            for s in signals:
                if s.type != HallucinationType.DATA_DRIVEN:
                    s.type = HallucinationType.DATA_DRIVEN
        return signals

    def detect_reasoning_driven(
        self,
        text: str,
        reasoning_length: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HallucinationSignal]:
        """Detect reasoning-driven hallucination signals."""
        signals = []

        # Reasoning length check (key finding: hallucination risk grows with length)
        if reasoning_length > 5:
            severity = min(1.0, 0.5 + (reasoning_length - 5) * 0.1)
            signals.append(HallucinationSignal(
                type=HallucinationType.REASONING_DRIVEN,
                severity=severity,
                description=f"Long reasoning chain ({reasoning_length} sentences), hallucination risk amplified",
                evidence=f"Reasoning length: {reasoning_length}, threshold: 5",
            ))

        for group in self.reasoning_driven_groups:
            group_signals = self._check_group(text, group)
            for s in group_signals:
                s.type = HallucinationType.REASONING_DRIVEN
            signals.extend(group_signals)

        return signals

    def detect(
        self,
        text: str,
        reasoning_length: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HallucinationSignal]:
        """Detect all hallucination signals (combined)."""
        data_signals = self.detect_data_driven(text, context)
        reasoning_signals = self.detect_reasoning_driven(text, reasoning_length, context)
        all_signals = data_signals + reasoning_signals
        all_signals.sort(key=lambda x: x.severity, reverse=True)
        return all_signals

    def calculate_risk_score(self, signals: List[HallucinationSignal]) -> float:
        """Calculate overall hallucination risk score (0.0-1.0)."""
        if not signals:
            return 0.0
        avg_severity = sum(s.severity for s in signals) / len(signals)
        count_factor = min(1.0, len(signals) / 5.0)
        return min(1.0, avg_severity * 0.7 + count_factor * 0.3)
