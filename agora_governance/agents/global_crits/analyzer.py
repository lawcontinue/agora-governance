"""
Global Crit 决策分析器 - 分层治理架构 v2.0

版本: v1.0
创建日期: 2026-03-20
设计者: 忒弥斯 (T-Mind) 🔮 + 家族协作
实施: Code 💻

分级分析策略:
1. Level 1: 规则快速检查（< 10 tokens，即时）
2. Level 2: 先例匹配（Phase 2 实施）
3. Level 3: LLM 深度分析（~5K tokens，复杂决策）

差异性机制:
- Global Crit 1: 温度 0.3（保守）
- Global Crit 2: 温度 0.7（平衡）
- Global Crit 3: 温度 1.0（创新）
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re


# Phase 2: 先例数据库集成
try:
    from agora.governance.precedent_db import PrecedentDatabase
    PRECEDENT_DB_AVAILABLE = True
except ImportError:
    PRECEDENT_DB_AVAILABLE = False


class AnalysisLevel(Enum):
    """分析级别"""
    LEVEL1_RULES = "level1_rules"  # 规则检查
    LEVEL2_PRECEDENT = "level2_precedent"  # 先例匹配
    LEVEL3_LLM = "level3_llm"  # LLM 深度分析


class P0IssueType(Enum):
    """P0 问题类型"""
    SECURITY_VULNERABILITY = "security_vulnerability"  # 安全漏洞
    PRIVACY_VIOLATION = "privacy_violation"  # 隐私侵犯
    COMPLIANCE_RISK = "compliance_risk"  # 合规风险
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # 资源耗尽
    CRITICAL_DEPENDENCY = "critical_dependency"  # 关键依赖


class DecisionAnalyzer:
    """
    Global Crit 决策分析器

    职责:
    1. 分级分析（规则 → 先例 → LLM）
    2. P0 问题检测
    3. 产生差异性分析结果
    """

    def __init__(self, crit_id: int, precedent_db: Optional[PrecedentDatabase] = None):
        """
        初始化分析器

        Args:
            crit_id: Global Crit ID（1, 2, 3）
            precedent_db: 先例数据库（Phase 2 使用）
        """
        self.crit_id = crit_id

        # 差异性配置（Crit 建议）
        self.temperature_configs = {
            1: 0.3,  # 保守
            2: 0.7,  # 平衡
            3: 1.0,  # 创新
        }
        self.temperature = self.temperature_configs.get(crit_id, 0.7)

        # Phase 2: 先例数据库
        self.precedent_db = precedent_db
        if PRECEDENT_DB_AVAILABLE and precedent_db is None:
            # 默认初始化先例数据库
            self.precedent_db = PrecedentDatabase()

        # P0 规则库（Shield 定义，持续扩展）
        self.p0_rules = {
            P0IssueType.SECURITY_VULNERABILITY: [
                r"(?i)(sql injection|xss|csrf|buffer overflow)",  # 明确的注入关键词
                r"(?i)select\s+.*?\s+from\s+.*?\s+where\s+.*?[\"'].*?\{.*?\}.*?[\"']",  # SQL 注入模式（字符串插值）
                r"(?i)hard.?coded\s+(password|key|secret)",  # 硬编码凭证
                r"(?i)(md5|sha1)\s*hash",  # 弱哈希
                r"(?i)http://.*?\.example\.com",  # 不安全 HTTP
            ],
            P0IssueType.PRIVACY_VIOLATION: [
                r"(?i)(pii|personal data).*?(without|lack|no).*(encrypt|anonymiz)",  # PII 数据未加密/匿名化
                r"(?i)(log|print|debug).*?(password|secret|token)",  # 记录敏感信息
                r"(?i)(email|phone|address).*?(plain.?text)",  # 明文存储敏感信息
                r"(?i)(password|secret|key)\s*=\s*\w+.*?#\s*.*(直接|direct|without|no|not).*(加密|encrypt|hash)",  # 未加密的密码存储（中英文）
            ],
            P0IssueType.COMPLIANCE_RISK: [
                r"(?i)(gdpr|ccpa)",  # 任何提到 GDPR/CCPA 的内容（简化规则）
                r"(?i)(data.*transfer|cross.?border).*(without|lack|no).*(consent|legal basis)",  # 跨境数据传输
            ],
            P0IssueType.RESOURCE_EXHAUSTION: [
                r"(?i)(while\s+.*?true|for\s+.*?ever|infinite loop)",
                r"(?i)(recursion).*?(without|lack|no).*(base.?case|termin)",
                r"(?i)(allocat|malloc).*?(unbounded|unlimited)",
            ],
            P0IssueType.CRITICAL_DEPENDENCY: [
                r"(?i)(pip install|npm install).*?(--force|--ignore)?deps",
                r"(?i)(download|fetch).*?(from.*untrusted|unsigned)",
            ],
        }

    def analyze(
        self,
        decision: Dict,
        precedents: List[Dict] = None
    ) -> Dict:
        """
        分析决策（分级策略）

        Args:
            decision: 决策对象
            precedents: 相关先例（Phase 2 使用，已废弃，使用 self.precedent_db）

        Returns:
            dict: 分析结果
            {
                "level": AnalysisLevel,
                "decision": VoteDecision,
                "reasoning": str,
                "confidence": float,
                "p0_issues": List[Dict],
                "token_cost": int,
                "precedents": List[Dict]  # Phase 2 新增
            }
        """
        # Level 1: 规则快速检查
        level1_result = self._level1_rules_check(decision)

        if level1_result["has_p0_issues"]:
            # 发现 P0 问题，直接拒绝
            return {
                "level": AnalysisLevel.LEVEL1_RULES,
                "decision": "reject",
                "reasoning": self._format_p0_rejection(level1_result["p0_issues"]),
                "confidence": 1.0,
                "p0_issues": level1_result["p0_issues"],
                "token_cost": 0,
                "crit_id": self.crit_id,
                "temperature": self.temperature,
                "precedents": [],
            }

        # Level 2: 先例匹配（Phase 2 实施）
        if self.precedent_db is not None and PRECEDENT_DB_AVAILABLE:
            level2_result = self._level2_precedent_match(decision)

            if level2_result["has_strong_precedent"]:
                # 发现强先例，直接跟随
                return {
                    "level": AnalysisLevel.LEVEL2_PRECEDENT,
                    "decision": level2_result["decision"],
                    "reasoning": level2_result["reasoning"],
                    "confidence": level2_result["confidence"],
                    "p0_issues": [],
                    "token_cost": 0,
                    "crit_id": self.crit_id,
                    "temperature": self.temperature,
                    "precedents": level2_result["precedents"],
                }

        # Level 3: LLM 深度分析
        return self._level3_llm_analysis(decision)

    def _level1_rules_check(self, decision: Dict) -> Dict:
        """
        Level 1: 规则快速检查

        Args:
            decision: 决策对象

        Returns:
            dict: 检查结果
        """
        p0_issues = []

        # 提取决策文本
        decision_text = self._extract_text(decision)

        # 检查 P0 规则
        for issue_type, patterns in self.p0_rules.items():
            for pattern in patterns:
                if re.search(pattern, decision_text):
                    p0_issues.append({
                        "type": issue_type.value,
                        "pattern": pattern,
                        "severity": "P0",
                        "description": self._get_issue_description(issue_type),
                    })

        return {
            "has_p0_issues": len(p0_issues) > 0,
            "p0_issues": p0_issues,
        }

    def _level2_precedent_match(self, decision: Dict) -> Dict:
        """
        Level 2: 先例匹配（Phase 2 实施）

        策略:
        1. 搜索相关先例（相似度 ≥ 0.2）
        2. 如果有超级先例（权重 ≥ 5.0），直接跟随
        3. 如果有多个高权重先例（权重 ≥ 3.0），加权投票
        4. 否则，继续到 Level 3

        Args:
            decision: 决策对象

        Returns:
            dict: 匹配结果
        """
        # 提取查询文本
        decision_text = self._extract_text(decision)

        # 搜索先例
        search_results = self.precedent_db.search(
            query=decision_text,
            threshold=0.2,  # 相似度阈值
            top_k=5
        )

        if not search_results:
            # 没有找到相关先例
            return {
                "has_strong_precedent": False,
                "precedents": [],
            }

        # 检查是否有超级先例（权重 ≥ 5.0）
        super_precedents = [
            r for r in search_results
            if r["weight"] >= 5.0 and r["similarity"] >= 0.3
        ]

        if super_precedents:
            # 跟随超级先例
            top_precedent = super_precedents[0]
            precedent = top_precedent["precedent"]

            return {
                "has_strong_precedent": True,
                "decision": "approve" if precedent.approved else "reject",
                "reasoning": f"Global Crit {self.crit_id}：发现超级先例（权重 {top_precedent['weight']:.1f}，相似度 {top_precedent['similarity']:.0%}）：{precedent.decision_id}。历史决策：{'批准' if precedent.approved else '拒绝'}。理由：{precedent.reasoning[:100]}...",
                "confidence": 0.95,
                "precedents": [top_precedent],
            }

        # 检查是否有多个高权重先例（权重 ≥ 3.0）
        high_weight_precedents = [
            r for r in search_results
            if r["weight"] >= 3.0 and r["similarity"] >= 0.25
        ]

        if len(high_weight_precedents) >= 2:
            # 加权投票
            approve_weight = sum(
                r["weight"] * r["similarity"]
                for r in high_weight_precedents
                if r["precedent"].approved
            )
            reject_weight = sum(
                r["weight"] * r["similarity"]
                for r in high_weight_precedents
                if not r["precedent"].approved
            )

            if approve_weight > reject_weight * 1.5:
                # 批准权重显著高于拒绝
                return {
                    "has_strong_precedent": True,
                    "decision": "approve",
                    "reasoning": f"Global Crit {self.crit_id}：{len(high_weight_precedents)} 个高权重先例支持批准（总权重 {approve_weight:.1f} vs {reject_weight:.1f}）",
                    "confidence": 0.85,
                    "precedents": high_weight_precedents[:3],
                }
            elif reject_weight > approve_weight * 1.5:
                # 拒绝权重显著高于批准
                return {
                    "has_strong_precedent": True,
                    "decision": "reject",
                    "reasoning": f"Global Crit {self.crit_id}：{len(high_weight_precedents)} 个高权重先例建议拒绝（总权重 {reject_weight:.1f} vs {approve_weight:.1f}）",
                    "confidence": 0.85,
                    "precedents": high_weight_precedents[:3],
                }

        # 没有足够强的先例，继续到 Level 3
        return {
            "has_strong_precedent": False,
            "precedents": search_results[:2],  # 返回前 2 个供参考
        }

    def _level3_llm_analysis(self, decision: Dict) -> Dict:
        """
        Level 3: LLM 深度分析

        Args:
            decision: 决策对象

        Returns:
            dict: 分析结果
        """
        # TODO: 集成 LLM 调用（Phase 1 P0-2 实施）
        # 当前返回模拟结果

        decision_text = self._extract_text(decision)

        # 简单启发式规则（临时替代 LLM）
        if "risk" in decision_text.lower() and "high" in decision_text.lower():
            decision_outcome = "reject"
            reasoning = f"Global Crit {self.crit_id}（温度 {self.temperature}）：检测到高风险关键词，建议拒绝。"
            confidence = 0.7
        elif "test" in decision_text.lower() and "pass" in decision_text.lower():
            decision_outcome = "approve"
            reasoning = f"Global Crit {self.crit_id}（温度 {self.temperature}）：测试通过，建议批准。"
            confidence = 0.8
        else:
            # 根据温度产生差异性
            if self.temperature <= 0.3:
                # 保守：倾向于弃权
                decision_outcome = "abstain"
                reasoning = f"Global Crit {self.crit_id}（温度 {self.temperature}）：信息不足，保守起见弃权。"
                confidence = 0.5
            elif self.temperature >= 1.0:
                # 创新：倾向于批准
                decision_outcome = "approve"
                reasoning = f"Global Crit {self.crit_id}（温度 {self.temperature}）：鼓励创新，建议批准。"
                confidence = 0.6
            else:
                # 平衡：根据内容判断
                decision_outcome = "approve"
                reasoning = f"Global Crit {self.crit_id}（温度 {self.temperature}）：平衡评估后建议批准。"
                confidence = 0.7

        return {
            "level": AnalysisLevel.LEVEL3_LLM,
            "decision": decision_outcome,
            "reasoning": reasoning,
            "confidence": confidence,
            "p0_issues": [],
            "token_cost": 5000,  # 估算
            "crit_id": self.crit_id,
            "temperature": self.temperature,
            "precedents": [],  # Level 3 没有使用先例
        }

    def _extract_text(self, decision: Dict) -> str:
        """
        从决策对象提取文本

        Args:
            decision: 决策对象

        Returns:
            str: 决策文本
        """
        # 尝试提取各个字段
        text_parts = []

        if "description" in decision:
            text_parts.append(str(decision["description"]))
        if "reasoning" in decision:
            text_parts.append(str(decision["reasoning"]))
        if "content" in decision:
            text_parts.append(str(decision["content"]))
        if "code" in decision:
            text_parts.append(str(decision["code"]))
        if "task" in decision:
            text_parts.append(str(decision["task"]))

        return " ".join(text_parts)

    def _format_p0_rejection(self, p0_issues: List[Dict]) -> str:
        """
        格式化 P0 问题拒绝理由

        Args:
            p0_issues: P0 问题列表

        Returns:
            str: 拒绝理由
        """
        issues_desc = [issue["description"] for issue in p0_issues]
        return f"Global Crit {self.crit_id}：发现 {len(p0_issues)} 个 P0 问题：{'; '.join(issues_desc)}。必须修复后才能批准。"

    def _get_issue_description(self, issue_type: P0IssueType) -> str:
        """
        获取问题描述

        Args:
            issue_type: 问题类型

        Returns:
            str: 问题描述
        """
        descriptions = {
            P0IssueType.SECURITY_VULNERABILITY: "安全漏洞（OWASP Top 10）",
            P0IssueType.PRIVACY_VIOLATION: "隐私侵犯（未加密的 PII 数据）",
            P0IssueType.COMPLIANCE_RISK: "合规风险（违反 GDPR/CCPA）",
            P0IssueType.RESOURCE_EXHAUSTION: "资源耗尽风险（无限循环/递归）",
            P0IssueType.CRITICAL_DEPENDENCY: "关键依赖风险（未验证的第三方库）",
        }
        return descriptions.get(issue_type, "未知 P0 问题")


# 工厂函数
def create_analyzer(crit_id: int, precedent_db: Optional[PrecedentDatabase] = None) -> DecisionAnalyzer:
    """
    创建分析器

    Args:
        crit_id: Global Crit ID（1, 2, 3）
        precedent_db: 先例数据库（可选）

    Returns:
        DecisionAnalyzer: 分析器实例
    """
    return DecisionAnalyzer(crit_id, precedent_db)
