"""
操作分级器（Operation Classifier）- Default-deny P0 操作

版本: v1.0
创建日期: 2026-04-18



Responsibilities:
1. Classify operations by risk into P0/P1/P2
2. P0 default-deny, P1 allow+audit, P2 allow+lightweight log
3. P0 pattern list is configurable (not hardcoded)
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
    """Risk level"""
    P0 = "P0"  # 高风险：default-deny
    P1 = "P1"  # 中风险：allow + 审计
    P2 = "P2"  # 低风险：allow + 轻量日志


@dataclass
class OperationRisk:
    """Operation risk assessment"""
    level: RiskLevel
    matched_pattern: Optional[str] = None
    matched_category: Optional[str] = None
    default_action: Literal["deny", "allow"] = "allow"
    requires_audit: bool = False
    reasoning: str = ""


@dataclass
class RiskPattern:
    """Risk pattern definition"""
    pattern: str
    category: str
    level: RiskLevel
    use_regex: bool = False


class OperationClassifier:
    """
    操作分级器

    Responsibilities:
    1. 根据预定义模式将操作分为 P0/P1/P2
    2. 支持可配置的模式列表
    3. 支持正则和精确匹配
    """

    # Default P0 patterns (hardcoded fallback, overridable via config)
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
        # Config file patterns (regex to avoid false matches)
        RiskPattern(r"docker-compose\.yml", "config_override", RiskLevel.P0, use_regex=True),
        RiskPattern(r"(?:^|\s|/)\.env(?:\s|$|/)", "config_override", RiskLevel.P0, use_regex=True),
    ]

    # Default P1 patterns
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
        Initialize operation classifier

        Args:
            config_path: Optional config file path (JSON)
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
        """Parse RiskLevel with fallback (supports str/enum)"""
        if isinstance(val, RiskLevel):
            return val
        try:
            return RiskLevel(val)
        except ValueError:
            try:
                return RiskLevel[val]
            except KeyError:
                return RiskLevel.P2  # Unknown level defaults to P2

    def _load_config(self, config_path: str):
        """Load custom patterns from JSON file"""
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
        Classify operation risk level

        Args:
            decision: Decision object, must contain "action" field

        Returns:
            OperationRisk: Risk assessment result
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
                reasoning=f"Batch operation ({target_count} targets) auto-escalated to P0",
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
                        reasoning=f"Matched P1 pattern: {pattern.pattern} ({pattern.category})",
                    )
            else:
                if pattern.pattern.lower() in action_lower:
                    return OperationRisk(
                        level=RiskLevel.P1,
                        matched_pattern=pattern.pattern,
                        matched_category=pattern.category,
                        default_action="allow",
                        requires_audit=True,
                        reasoning=f"Matched P1 pattern: {pattern.pattern} ({pattern.category})",
                    )

        # 默认 P2
        return OperationRisk(
            level=RiskLevel.P2,
            default_action="allow",
            requires_audit=False,
            reasoning="No matching pattern, default P2 (low risk)",
        )

    def _make_risk(self, pattern: RiskPattern) -> OperationRisk:
        """Generate P0 risk assessment from pattern"""
        return OperationRisk(
            level=RiskLevel.P0,
            matched_pattern=pattern.pattern,
            matched_category=pattern.category,
            default_action="deny",
            requires_audit=True,
            reasoning=f"Matched P0 pattern: {pattern.pattern} ({pattern.category})",
        )

    def add_pattern(self, pattern: RiskPattern):
        """Add pattern dynamically"""
        if pattern.level == RiskLevel.P0:
            self.p0_patterns.append(pattern)
        elif pattern.level == RiskLevel.P1:
            self.p1_patterns.append(pattern)
        self.logger.info(f"Added pattern: {pattern.pattern} ({pattern.level.value})")

    def remove_pattern(self, pattern_str: str) -> bool:
        """Remove pattern"""
        for patterns in [self.p0_patterns, self.p1_patterns]:
            for i, p in enumerate(patterns):
                if p.pattern == pattern_str:
                    patterns.pop(i)
                    self.logger.info(f"Removed pattern: {pattern_str}")
                    return True
        return False

    def list_patterns(self) -> Dict[str, List[Dict]]:
        """List all patterns"""
        return {
            "P0": [asdict(p) for p in self.p0_patterns],
            "P1": [asdict(p) for p in self.p1_patterns],
        }
