"""
操作分级器（Operation Classifier）- Default-deny P0 操作

版本: v1.0
创建日期: 2026-04-18



职责:
1. 将操作按风险分为 P0/P1/P2 三级
2. P0 操作 default-deny，P1 allow+审计，P2 allow+轻量日志
3. P0 模式列表可配置（不硬编码）
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    P0 = "P0"  # 高风险：default-deny
    P1 = "P1"  # 中风险：allow + 审计
    P2 = "P2"  # 低风险：allow + 轻量日志


@dataclass
class OperationRisk:
    """操作风险评定"""
    level: RiskLevel
    matched_pattern: Optional[str] = None
    matched_category: Optional[str] = None
    default_action: Literal["deny", "allow"] = "allow"
    requires_audit: bool = False
    reasoning: str = ""


@dataclass
class RiskPattern:
    """风险模式定义"""
    pattern: str
    category: str
    level: RiskLevel
    use_regex: bool = False


class OperationClassifier:
    """
    操作分级器

    职责:
    1. 根据预定义模式将操作分为 P0/P1/P2
    2. 支持可配置的模式列表
    3. 支持正则和精确匹配
    """

    # 默认 P0 模式（硬编码兜底，可被配置覆盖）
    DEFAULT_P0_PATTERNS: List[RiskPattern] = [
        RiskPattern("rm -rf", "batch_delete", RiskLevel.P0),
        RiskPattern("rm -r", "batch_delete", RiskLevel.P0),
        RiskPattern("git push --force", "force_push", RiskLevel.P0),
        RiskPattern("git reset --hard", "hard_reset", RiskLevel.P0),
        RiskPattern("drop table", "db_delete", RiskLevel.P0),
        RiskPattern("truncate table", "db_delete", RiskLevel.P0),
        RiskPattern("sudo", "privilege_escalation", RiskLevel.P0),
        RiskPattern("docker rm", "docker_cleanup", RiskLevel.P0),
        RiskPattern("docker rmi", "docker_cleanup", RiskLevel.P0),
        RiskPattern("docker prune", "docker_cleanup", RiskLevel.P0),
        RiskPattern("docker system prune", "docker_cleanup", RiskLevel.P0),
        RiskPattern("批量删除", "batch_delete", RiskLevel.P0),
        RiskPattern("批量发送", "batch_send", RiskLevel.P0),
        # 配置文件覆盖（使用正则避免误匹配）
        RiskPattern(r"docker-compose\.yml", "config_override", RiskLevel.P0, use_regex=True),
        RiskPattern(r"(?:^|\s|/)\.env(?:\s|$|/)", "config_override", RiskLevel.P0, use_regex=True),
    ]

    # 默认 P1 模式
    DEFAULT_P1_PATTERNS: List[RiskPattern] = [
        RiskPattern(r"\brm\b\s", "single_delete", RiskLevel.P1, use_regex=True),
        RiskPattern("git push", "push", RiskLevel.P1),
        RiskPattern("delete", "delete_op", RiskLevel.P1),
        RiskPattern("remove", "remove_op", RiskLevel.P1),
        RiskPattern("send", "send_op", RiskLevel.P1),
        RiskPattern("overwrite", "overwrite_op", RiskLevel.P1),
    ]

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化操作分级器

        Args:
            config_path: 可选的配置文件路径（JSON）
        """
        self.logger = logging.getLogger("agora.governance.classifier")
        self.p0_patterns: List[RiskPattern] = list(self.DEFAULT_P0_PATTERNS)
        self.p1_patterns: List[RiskPattern] = list(self.DEFAULT_P1_PATTERNS)

        if config_path:
            self._load_config(config_path)

        self.logger.info(
            f"OperationClassifier initialized: "
            f"{len(self.p0_patterns)} P0, {len(self.p1_patterns)} P1 patterns"
        )

    @staticmethod
    def _parse_risk_level(val) -> RiskLevel:
        """容错解析 RiskLevel（P2-1: 支持 str/enum 输入）"""
        if isinstance(val, RiskLevel):
            return val
        try:
            return RiskLevel(val)
        except ValueError:
            try:
                return RiskLevel[val]
            except KeyError:
                return RiskLevel.P2  # 未知等级默认 P2

    def _load_config(self, config_path: str):
        """从 JSON 文件加载自定义模式"""
        try:
            path = Path(config_path)
            if not path.exists():
                self.logger.warning(f"Config not found: {config_path}, using defaults")
                return

            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)

            custom_p0 = []
            for p in config.get("p0_patterns", []):
                p["level"] = self._parse_risk_level(p.get("level", "P0"))
                custom_p0.append(RiskPattern(**p))

            custom_p1 = []
            for p in config.get("p1_patterns", []):
                p["level"] = self._parse_risk_level(p.get("level", "P1"))
                custom_p1.append(RiskPattern(**p))

            self.p0_patterns.extend(custom_p0)
            self.p1_patterns.extend(custom_p1)

            self.logger.info(
                f"Loaded {len(custom_p0)} custom P0, {len(custom_p1)} custom P1 patterns"
            )

        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")

    def classify(self, decision: Dict) -> OperationRisk:
        """
        分类操作风险等级

        Args:
            decision: 决策对象，需包含 "action" 字段

        Returns:
            OperationRisk: 风险评定结果
        """
        action = str(decision.get("action", ""))
        targets = decision.get("targets", [])
        target_count = len(targets) if isinstance(targets, list) else 0

        # Batch operations auto-escalate to P0
        if target_count > 5:
            return OperationRisk(
                level=RiskLevel.P0,
                matched_pattern=f"targets={target_count}",
                matched_category="batch_operation",
                default_action="deny",
                requires_audit=True,
                reasoning=f"批量操作（{target_count} 个目标）自动升级为 P0",
            )

        action_lower = action.lower()

        # 检查 P0 模式（优先级最高）
        for pattern in self.p0_patterns:
            if pattern.use_regex:
                if re.search(pattern.pattern, action_lower):
                    return self._make_risk(pattern)
            else:
                if pattern.pattern.lower() in action_lower:
                    return self._make_risk(pattern)

        # 检查 P1 模式
        for pattern in self.p1_patterns:
            if pattern.use_regex:
                if re.search(pattern.pattern, action_lower):
                    return OperationRisk(
                        level=RiskLevel.P1,
                        matched_pattern=pattern.pattern,
                        matched_category=pattern.category,
                        default_action="allow",
                        requires_audit=True,
                        reasoning=f"匹配 P1 模式: {pattern.pattern} ({pattern.category})",
                    )
            else:
                if pattern.pattern.lower() in action_lower:
                    return OperationRisk(
                        level=RiskLevel.P1,
                        matched_pattern=pattern.pattern,
                        matched_category=pattern.category,
                        default_action="allow",
                        requires_audit=True,
                        reasoning=f"匹配 P1 模式: {pattern.pattern} ({pattern.category})",
                    )

        # 默认 P2
        return OperationRisk(
            level=RiskLevel.P2,
            default_action="allow",
            requires_audit=False,
            reasoning="无匹配模式，默认 P2（低风险）",
        )

    def _make_risk(self, pattern: RiskPattern) -> OperationRisk:
        """根据模式生成 P0 风险评定"""
        return OperationRisk(
            level=RiskLevel.P0,
            matched_pattern=pattern.pattern,
            matched_category=pattern.category,
            default_action="deny",
            requires_audit=True,
            reasoning=f"匹配 P0 模式: {pattern.pattern} ({pattern.category})",
        )

    def add_pattern(self, pattern: RiskPattern):
        """动态添加模式"""
        if pattern.level == RiskLevel.P0:
            self.p0_patterns.append(pattern)
        elif pattern.level == RiskLevel.P1:
            self.p1_patterns.append(pattern)
        self.logger.info(f"Added pattern: {pattern.pattern} ({pattern.level.value})")

    def remove_pattern(self, pattern_str: str) -> bool:
        """移除模式"""
        for patterns in [self.p0_patterns, self.p1_patterns]:
            for i, p in enumerate(patterns):
                if p.pattern == pattern_str:
                    patterns.pop(i)
                    self.logger.info(f"Removed pattern: {pattern_str}")
                    return True
        return False

    def list_patterns(self) -> Dict[str, List[Dict]]:
        """列出所有模式"""
        return {
            "P0": [asdict(p) for p in self.p0_patterns],
            "P1": [asdict(p) for p in self.p1_patterns],
        }
