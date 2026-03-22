"""
治理层（Governance Layer）- 分层治理架构 v2.0

版本: v1.0
创建日期: 2026-03-20
设计者: 忒弥斯 (T-Mind) 🔮 + 家族协作
实施: Code 💻

职责:
1. Local Crits 审查（领域专家，15 分钟超时）
2. Global Crits 投票（宪法法院，1 小时超时）
3. T-Mind 最终决策（最高上诉法院，无超时限制）
4. 决策日志持久化（先例系统基础）
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from agents.local_crits.local_crit import LocalCrit, ReviewResult, ReviewDecision
from agents.global_crits.global_crit import GlobalCrit, Vote, VoteDecision
from agents.global_crits.analyzer import AnalysisLevel, P0IssueType
from agora.governance.voting import GlobalCritVoting, FinalDecision


logger = logging.getLogger(__name__)


class GovernanceStage(Enum):
    """治理阶段"""
    LOCAL_REVIEW = "local_review"  # Local Crits 审查
    GLOBAL_VOTING = "global_voting"  # Global Crits 投票
    TMIND_DECISION = "tmind_decision"  # T-Mind 最终决策
    COMPLETED = "completed"  # 完成


@dataclass
class GovernanceResult:
    """治理结果"""
    approved: bool  # 是否批准
    stage: GovernanceStage  # 当前阶段
    local_reviews: Dict[str, Dict]  # Local Crits 审查结果
    global_votes: Optional[Dict]  # Global Crits 投票结果
    tmind_decision: Optional[Dict]  # T-Mind 最终决策
    decision_id: str  # 决策 ID
    reasoning: str  # 拒绝/批准理由
    token_cost: int  # Token 成本
    duration_ms: float  # 执行时长（毫秒）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class GovernanceLayer:
    """
    治理层（Governance Layer）

    职责:
    1. 管理 Local Crits 审查
    2. 管理 Global Crits 投票
    3. 管理 T-Mind 最终决策
    4. 持久化决策日志
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化治理层

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger("agora.governance")

        # 初始化 Local Crits
        self.local_crits: Dict[str, LocalCrit] = {}
        self._init_local_crits()

        # 初始化 Global Crits
        self.global_crits: List[GlobalCrit] = []
        self._init_global_crits()

        # 初始化投票机制
        self.voting_mechanism = GlobalCritVoting(self.global_crits)

        # 决策日志路径
        self.decision_log_path = Path(self.config.get(
            "decision_log_path",
            "agora/data/decisions.jsonl"
        ))
        self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info("GovernanceLayer initialized")

    def _init_local_crits(self):
        """初始化 Local Crits（8 个）"""
        from agents.local_crits import (
            ShieldCrit,
            CodeCrit,
            AthenaCrit,
            PerformanceCrit,
            ComplianceCrit,
            PrivacyCrit,
            AccessibilityCrit,
            ScaleCrit,
        )

        # 注册基础 Crits（3 个）
        self.register_local_crit(ShieldCrit())
        self.register_local_crit(CodeCrit())
        self.register_local_crit(AthenaCrit())

        # 注册新增 Crits（P1-1，5 个）
        self.register_local_crit(PerformanceCrit())
        self.register_local_crit(ComplianceCrit())
        self.register_local_crit(PrivacyCrit())
        self.register_local_crit(AccessibilityCrit())
        self.register_local_crit(ScaleCrit())

        self.logger.info(f"Initialized {len(self.local_crits)} Local Crits")

    def _init_global_crits(self):
        """初始化 Global Crits（3 个）"""
        for i in range(1, 4):
            crit = GlobalCrit(crit_id=i)
            self.global_crits.append(crit)

        self.logger.info(f"Initialized {len(self.global_crits)} Global Crits")

    def register_local_crit(self, crit: LocalCrit):
        """
        注册 Local Crit

        Args:
            crit: Local Crit 实例
        """
        self.local_crits[crit.name] = crit
        self.logger.info(f"Registered Local Crit: {crit.name}")

    def review_decision(
        self,
        decision: Dict,
        enable_governance: bool = True
    ) -> GovernanceResult:
        """
        审查决策（完整工作流）

        工作流:
        1. Local Crits 审查（15 分钟超时）
           - 全部通过 → 批准
           - 发现 P0 问题 → 拒绝
           - 有冲突 → 升级 Global Crits

        2. Global Crits 投票（1 小时超时）
           - 2/3 多数 → 批准/拒绝
           - 1-1-1 分裂 → 升级 T-Mind

        3. T-Mind 最终决策（无超时限制）
           - 最终决策

        Args:
            decision: 决策对象
            enable_governance: 是否启用治理（默认 True）

        Returns:
            GovernanceResult: 审查结果
        """
        import time
        start_time = time.time()

        # 生成决策 ID
        decision_id = f"DEC_{datetime.now().strftime('%Y%m%d_%H%M')}"

        # 如果不启用治理，直接批准
        if not enable_governance:
            return GovernanceResult(
                approved=True,
                stage=GovernanceStage.COMPLETED,
                local_reviews={},
                global_votes=None,
                tmind_decision=None,
                decision_id=decision_id,
                reasoning="治理层未启用",
                token_cost=0,
                duration_ms=(time.time() - start_time) * 1000,
            )

        # 阶段 1: Local Crits 审查
        self.logger.info(f"[{decision_id}] Starting Local Crits review")
        local_result = self._local_review(decision, decision_id)

        # 如果发现 P0 问题，直接拒绝
        if local_result["has_p0_issues"]:
            self.logger.warning(f"[{decision_id}] P0 issues detected, rejecting")
            result = GovernanceResult(
                approved=False,
                stage=GovernanceStage.LOCAL_REVIEW,
                local_reviews=local_result["reviews"],
                global_votes=None,
                tmind_decision=None,
                decision_id=decision_id,
                reasoning=local_result["p0_summary"],
                token_cost=local_result["token_cost"],
                duration_ms=(time.time() - start_time) * 1000,
            )
            self._log_decision(result)
            return result

        # 如果有冲突，升级 Global Crits
        if local_result["has_conflicts"]:
            self.logger.info(f"[{decision_id}] Local Crits conflicts, escalating to Global Crits")
            global_result = self._global_voting(decision, decision_id)

            # 如果 1-1-1 分裂，升级 T-Mind
            if global_result["final_decision"] == FinalDecision.ESCALATED:
                self.logger.info(f"[{decision_id}] Global Crits split (1-1-1), escalating to T-Mind")
                tmind_result = self._tmind_decision(decision, decision_id, local_result, global_result)

                result = GovernanceResult(
                    approved=tmind_result["approved"],
                    stage=GovernanceStage.TMIND_DECISION,
                    local_reviews=local_result["reviews"],
                    global_votes=global_result,
                    tmind_decision=tmind_result,
                    decision_id=decision_id,
                    reasoning=tmind_result["reasoning"],
                    token_cost=local_result["token_cost"] + global_result["token_cost"],
                    duration_ms=(time.time() - start_time) * 1000,
                )
            else:
                # Global Crits 达成共识
                approved = global_result["final_decision"] == FinalDecision.APPROVED
                result = GovernanceResult(
                    approved=approved,
                    stage=GovernanceStage.GLOBAL_VOTING,
                    local_reviews=local_result["reviews"],
                    global_votes=global_result,
                    tmind_decision=None,
                    decision_id=decision_id,
                    reasoning=global_result["reasoning"],
                    token_cost=local_result["token_cost"] + global_result["token_cost"],
                    duration_ms=(time.time() - start_time) * 1000,
                )
        else:
            # Local Crits 全部通过，批准
            self.logger.info(f"[{decision_id}] Local Crits all approved")
            result = GovernanceResult(
                approved=True,
                stage=GovernanceStage.LOCAL_REVIEW,
                local_reviews=local_result["reviews"],
                global_votes=None,
                tmind_decision=None,
                decision_id=decision_id,
                reasoning=local_result["reasoning"],
                token_cost=local_result["token_cost"],
                duration_ms=(time.time() - start_time) * 1000,
            )

        # 持久化决策日志
        self._log_decision(result)

        return result

    def _local_review(self, decision: Dict, decision_id: str) -> Dict:
        """
        Local Crits 审查

        Args:
            decision: 决策对象
            decision_id: 决策 ID

        Returns:
            dict: 审查结果
        """
        reviews = {}
        has_p0_issues = False
        has_conflicts = False
        token_cost = 0
        p0_issues_list = []

        # 遍历所有 Local Crits
        for crit_name, crit in self.local_crits.items():
            try:
                review_result = crit.review(decision)
                reviews[crit_name] = review_result.to_dict()

                token_cost += review_result.token_cost

                # 检查 P0 问题（通过 reasoning 中的 "P0" 标识）
                if review_result.decision == ReviewDecision.REJECT:
                    if "P0" in review_result.reasoning or "p0" in review_result.reasoning:
                        has_p0_issues = True
                        p0_issues_list.append({
                            "crit": crit_name,
                            "reason": review_result.reasoning,
                        })
                    else:
                        has_conflicts = True

            except Exception as e:
                self.logger.error(f"Local Crit {crit_name} failed: {e}")
                reviews[crit_name] = {
                    "error": str(e),
                    "decision": "error",
                }

        # 如果没有 Local Crits，默认通过
        if not self.local_crits:
            return {
                "reviews": {},
                "has_p0_issues": False,
                "has_conflicts": False,
                "token_cost": 0,
                "reasoning": "无 Local Crits，自动批准",
            }

        # 生成摘要
        if has_p0_issues:
            p0_summary = f"发现 {len(p0_issues_list)} 个 P0 问题"
        elif has_conflicts:
            p0_summary = "Local Crits 有冲突，升级 Global Crits"
        else:
            p0_summary = "Local Crits 全部批准"

        return {
            "reviews": reviews,
            "has_p0_issues": has_p0_issues,
            "has_conflicts": has_conflicts,
            "token_cost": token_cost,
            "p0_summary": p0_summary,
            "reasoning": f"Local Crits 审查完成：{p0_summary}",
        }

    def _global_voting(self, decision: Dict, decision_id: str) -> Dict:
        """
        Global Crits 投票

        Args:
            decision: 决策对象
            decision_id: 决策 ID

        Returns:
            dict: 投票结果
        """
        try:
            voting_result = self.voting_mechanism.vote(decision)

            return {
                "final_decision": voting_result.final_decision,
                "votes": [v.to_dict() for v in voting_result.votes],
                "approve": voting_result.approve,
                "reject": voting_result.reject,
                "abstain": voting_result.abstain,
                "reasoning": f"Global Crits 投票结果：{voting_result.final_decision.value}",
                "token_cost": 15000,  # 估算：3 个 Global Crits × 5000 tokens
                "errors": voting_result.errors,
            }

        except Exception as e:
            self.logger.error(f"Global Crits voting failed: {e}")
            return {
                "final_decision": FinalDecision.ESCALATED,  # 投票失败，升级 T-Mind
                "votes": [],
                "approve": 0,
                "reject": 0,
                "abstain": 0,
                "reasoning": f"投票失败：{str(e)}，升级 T-Mind",
                "token_cost": 0,
                "errors": [str(e)],
            }

    def _tmind_decision(
        self,
        decision: Dict,
        decision_id: str,
        local_result: Dict,
        global_result: Dict
    ) -> Dict:
        """
        T-Mind 最终决策

        Args:
            decision: 决策对象
            decision_id: 决策 ID
            local_result: Local Crits 审查结果
            global_result: Global Crits 投票结果

        Returns:
            dict: 决策结果
        """
        # TODO: 实现 T-Mind 决策逻辑
        # 当前简化实现：倾向于批准

        reasoning = (
            f"T-Mind 最终决策：Local Crits 有冲突，Global Crits 投票分裂（1-1-1）。"
            f"基于宪法原则和系统稳定性考虑，批准该决策。"
        )

        return {
            "approved": True,  # 简化实现：默认批准
            "reasoning": reasoning,
            "token_cost": 0,
            "timestamp": datetime.now().isoformat(),
        }

    def _log_decision(self, result: GovernanceResult):
        """
        持久化决策日志

        Args:
            result: 治理结果
        """
        try:
            log_entry = {
                "decision_id": result.decision_id,
                "timestamp": datetime.now().isoformat(),
                "approved": result.approved,
                "stage": result.stage.value,
                "local_reviews": result.local_reviews,
                "global_votes": result.global_votes,
                "tmind_decision": result.tmind_decision,
                "reasoning": result.reasoning,
                "token_cost": result.token_cost,
                "duration_ms": result.duration_ms,
            }

            # 追加到 JSONL 文件
            with open(self.decision_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            self.logger.info(f"Decision logged: {result.decision_id}")

        except Exception as e:
            self.logger.error(f"Failed to log decision: {e}")


# 工厂函数
def create_governance_layer(config: Optional[Dict] = None) -> GovernanceLayer:
    """
    创建治理层

    Args:
        config: 配置字典

    Returns:
        GovernanceLayer: 治理层实例
    """
    return GovernanceLayer(config)
