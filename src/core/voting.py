"""
Voting mechanism for multi-agent governance decisions.

Supports majority voting, unanimous consensus, and weighted voting
with configurable thresholds and tie-breaking.
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


class VoteDecision(Enum):
    APPROVE = "approve"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    voter_id: str
    decision: VoteDecision
    reasoning: str = ""
    weight: float = 1.0


@dataclass
class VotingResult:
    passed: bool
    approve_count: int = 0
    deny_count: int = 0
    abstain_count: int = 0
    total_weight_approve: float = 0.0
    total_weight_deny: float = 0.0
    votes: List[Vote] = field(default_factory=list)
    tie_broken: bool = False


class VotingMechanism:
    """
    Configurable voting mechanism for governance decisions.
    
    Supports:
    - Simple majority
    - Unanimous approval
    - Weighted voting
    - Custom thresholds
    """

    def __init__(
        self,
        threshold: float = 0.5,
        require_unanimous: bool = False,
        deny_on_tie: bool = True,
    ):
        self.threshold = threshold
        self.require_unanimous = require_unanimous
        self.deny_on_tie = deny_on_tie

    def tally(self, votes: List[Vote]) -> VotingResult:
        """Tally votes and determine outcome."""
        if not votes:
            return VotingResult(passed=False)

        approve_count = sum(1 for v in votes if v.decision == VoteDecision.APPROVE)
        deny_count = sum(1 for v in votes if v.decision == VoteDecision.DENY)
        abstain_count = sum(1 for v in votes if v.decision == VoteDecision.ABSTAIN)

        weight_approve = sum(v.weight for v in votes if v.decision == VoteDecision.APPROVE)
        weight_deny = sum(v.weight for v in votes if v.decision == VoteDecision.DENY)

        total = approve_count + deny_count
        passed = False
        tie_broken = False

        if self.require_unanimous:
            passed = deny_count == 0 and approve_count > 0
        elif total > 0:
            ratio = weight_approve / (weight_approve + weight_deny) if (weight_approve + weight_deny) > 0 else 0
            if ratio > self.threshold:
                passed = True
            elif ratio == self.threshold:
                passed = not self.deny_on_tie
                tie_broken = True

        return VotingResult(
            passed=passed,
            approve_count=approve_count,
            deny_count=deny_count,
            abstain_count=abstain_count,
            total_weight_approve=weight_approve,
            total_weight_deny=weight_deny,
            votes=votes,
            tie_broken=tie_broken,
        )
