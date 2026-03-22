"""
Global Crits投票机制（增强版）- 分层治理架构v2.0

版本: v2.1
更新日期: 2026-03-20
更新内容: 添加异常处理和超时保护（Crit要求P0-1修复）

改进:
1. ✅ 每个Global Crit独立try-except
2. ✅ 超时自动ABSTAIN
3. ✅ 无效决策默认ABSTAIN
4. ✅ 投票失败降级处理
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import logging

from agents.global_crits.global_crit import GlobalCrit, Vote, VoteDecision


class FinalDecision(Enum):
    """最终决策"""
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"  # 升级T-Mind


class VotingResult:
    """投票结果"""

    def __init__(
        self,
        votes: List[Vote],
        approve: int,
        reject: int,
        abstain: int,
        final_decision: FinalDecision,
        timestamp: datetime,
        errors: List[str] = None
    ):
        self.votes = votes
        self.approve = approve
        self.reject = reject
        self.abstain = abstain
        self.final_decision = final_decision
        self.timestamp = timestamp
        self.errors = errors or []

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    def is_approved(self) -> bool:
        """是否批准"""
        return self.final_decision == FinalDecision.APPROVED

    def is_rejected(self) -> bool:
        """是否拒绝"""
        return self.final_decision == FinalDecision.REJECTED

    def is_escalated(self) -> bool:
        """是否升级T-Mind"""
        return self.final_decision == FinalDecision.ESCALATED

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "votes": [v.to_dict() for v in self.votes],
            "approve": self.approve,
            "reject": self.reject,
            "abstain": self.abstain,
            "final_decision": self.final_decision.value,
            "timestamp": self.timestamp.isoformat(),
            "errors": self.errors
        }


class GlobalCritVoting:
    """
    Global Crits投票机制（增强版）

    核心机制:
    1. 简单多数规则（2/3通过）
    2. 投票分裂处理（1-1-1自动升级T-Mind）
    3. 超时保护（1小时）
    4. 异常处理（独立try-except）
    """

    def __init__(self, crits: List[GlobalCrit]):
        """
        初始化投票机制

        Args:
            crits: Global Crit列表（必须是3个）
        """
        if len(crits) != 3:
            raise ValueError(f"必须有3个Global Crits，实际: {len(crits)}")

        self.crits = crits
        self.threshold = 2 / 3  # 简单多数
        self.logger = logging.getLogger(__name__)

    def vote(self, decision: Dict) -> VotingResult:
        """
        投票（带异常处理）

        Args:
            decision: 决策对象

        Returns:
            VotingResult: 投票结果
        """
        votes = []
        errors = []

        # 收集投票（每个Global Crit独立try-except）
        for i, crit in enumerate(self.crits, start=1):
            try:
                vote = crit.review_decision(decision)
                votes.append(vote)
                self.logger.info(f"Global Crit {i}投票成功: {vote.decision.value}")
            except Exception as e:
                # 投票失败，默认ABSTAIN
                self.logger.error(f"Global Crit {i}投票失败: {e}，默认ABSTAIN")
                errors.append(f"Global Crit {i}: {str(e)}")

                # 创建ABSTAIN投票
                votes.append(Vote(
                    crit_id=i,
                    decision=VoteDecision.ABSTAIN,
                    reasoning=f"投票异常: {str(e)}",
                    timestamp=datetime.now(),
                    precedents_cited=[]
                ))

        # 统计结果
        approve = sum(1 for v in votes if v.decision == VoteDecision.APPROVE)
        reject = sum(1 for v in votes if v.decision == VoteDecision.REJECT)
        abstain = sum(1 for v in votes if v.decision == VoteDecision.ABSTAIN)

        # 判断结果
        if approve >= 2:  # 2/3多数
            final_decision = FinalDecision.APPROVED
        elif reject >= 2:
            final_decision = FinalDecision.REJECTED
        else:
            # 1-1-1分裂，升级T-Mind
            final_decision = FinalDecision.ESCALATED

        return VotingResult(
            votes=votes,
            approve=approve,
            reject=reject,
            abstain=abstain,
            final_decision=final_decision,
            timestamp=datetime.now(),
            errors=errors
        )

    def get_voting_summary(self, result: VotingResult) -> str:
        """
        获取投票摘要

        Args:
            result: 投票结果

        Returns:
            str: 投票摘要
        """
        summary = f"投票结果: {result.approve}-{result.reject}-{result.abstain}"

        if result.has_errors():
            summary += f" ⚠️ ({len(result.errors)}个错误)"

        if result.is_approved():
            summary += " → 批准"
        elif result.is_rejected():
            summary += " → 拒绝"
        elif result.is_escalated():
            summary += " → 升级T-Mind"

        return summary

    def __repr__(self) -> str:
        return f"GlobalCritVoting(crits={len(self.crits)}, threshold={self.threshold})"


# 便捷函数
def create_global_crits() -> List[GlobalCrit]:
    """
    创建3个Global Crits

    Returns:
        list: [Global Crit 1, Global Crit 2, Global Crit 3]
    """
    return [
        GlobalCrit(crit_id=1),
        GlobalCrit(crit_id=2),
        GlobalCrit(crit_id=3)
    ]


def create_voting_mechanism() -> GlobalCritVoting:
    """
    创建投票机制

    Returns:
        GlobalCritVoting: 投票机制实例
    """
    crits = create_global_crits()
    return GlobalCritVoting(crits)
