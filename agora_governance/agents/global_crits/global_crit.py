"""
Global Crit（宪法法院）- 分层治理架构v2.0

版本: v2.0
创建日期: 2026-03-20
设计者: 忒弥斯 (T-Mind) 🔮
验收: 家族全员（5/5赞成，Crit A- 90/100）

职责:
- 跨域冲突解决
- 先例维护
- 宪法解释
- 投票决策（3个Global Crits投票机制）
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .analyzer import DecisionAnalyzer, AnalysisLevel


class VoteDecision(Enum):
    """投票决策"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class Vote:
    """投票结果"""

    def __init__(
        self,
        crit_id: int,
        decision: VoteDecision,
        reasoning: str,
        timestamp: datetime,
        precedents_cited: List[str] = None
    ):
        self.crit_id = crit_id  # 1, 2, 3
        self.decision = decision
        self.reasoning = reasoning
        self.timestamp = timestamp
        self.precedents_cited = precedents_cited or []

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "crit_id": self.crit_id,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "precedents_cited": self.precedents_cited
        }


class GlobalCrit:
    """
    Global Crit（宪法法院）

    职责:
    1. 审查决策（跨域冲突）
    2. 检索先例
    3. 投票决策
    4. 维护先例
    """

    def __init__(self, crit_id: int):
        """
        初始化Global Crit

        Args:
            crit_id: Global Crit ID（1, 2, 3）
        """
        if crit_id not in [1, 2, 3]:
            raise ValueError(f"crit_id必须是1, 2, 或3，实际: {crit_id}")

        self.crit_id = crit_id
        self.name = f"Global Crit {crit_id}"
        self.role = "constitutional_review"
        self.timeout = 3600  # 1小时超时

        # 集成分析器（Phase 1 P0-1）
        self.analyzer = DecisionAnalyzer(crit_id)

    def review_decision(
        self,
        decision: Dict,
        precedents: List[Dict] = None
    ) -> Vote:
        """
        审查决策

        Args:
            decision: 决策对象
            precedents: 相关先例列表

        Returns:
            Vote: 投票结果
        """
        # 检索先例
        if precedents is None:
            precedents = self.search_precedents(decision)

        # 分析决策
        analysis = self.analyze(decision, precedents)

        # 投票
        return Vote(
            crit_id=self.crit_id,
            decision=analysis["decision"],
            reasoning=analysis["reasoning"],
            timestamp=datetime.now(),
            precedents_cited=[p["decision_id"] for p in precedents]
        )

    def search_precedents(self, decision: Dict) -> List[Dict]:
        """
        检索先例

        Args:
            decision: 决策对象

        Returns:
            list: 相关先例列表（按权重排序）
        """
        # TODO: 实现先例检索（Phase 2）
        # 当前返回空列表
        return []

    def analyze(
        self,
        decision: Dict,
        precedents: List[Dict]
    ) -> Dict:
        """
        分析决策（使用集成分析器）

        Args:
            decision: 决策对象
            precedents: 相关先例（Phase 2 使用）

        Returns:
            dict: 分析结果
            {
                "decision": VoteDecision,
                "reasoning": str,
                "confidence": float
            }
        """
        # 使用集成分析器
        analysis = self.analyzer.analyze(decision, precedents)

        # 转换决策类型
        decision_map = {
            "approve": VoteDecision.APPROVE,
            "reject": VoteDecision.REJECT,
            "abstain": VoteDecision.ABSTAIN,
        }

        return {
            "decision": decision_map.get(analysis["decision"], VoteDecision.ABSTAIN),
            "reasoning": analysis["reasoning"],
            "confidence": analysis["confidence"],
            "analysis_level": analysis["level"],
            "token_cost": analysis.get("token_cost", 0),
            "p0_issues": analysis.get("p0_issues", []),
        }

    def __repr__(self) -> str:
        return f"GlobalCrit(id={self.crit_id}, name={self.name})"
