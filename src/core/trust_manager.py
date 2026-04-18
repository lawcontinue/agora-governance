"""
渐进式信任管理器（Trust Manager）- 操作信任评分

版本: v1.0
创建日期: 2026-04-18


职责:
1. 管理操作类别的信任分数
2. 渐进式信任（前3次确认，之后自动批准）
3. 24小时自然衰减（trust_score *= 0.8）
4. 失败/拒绝重置为 0
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class TrustRecord:
    """信任记录"""
    category: str
    trust_score: int = 0
    last_updated: float = 0.0  # timestamp
    total_confirmed: int = 0
    total_denied: int = 0
    total_auto_approved: int = 0

    # 衰减参数（类常量，不参与 asdict 序列化）
    _DECAY_FACTOR: float = 0.8
    _DECAY_INTERVAL_SECONDS: float = 86400.0  # 24 小时
    _AUTO_APPROVE_THRESHOLD: int = 3

    def maybe_decay(self):
        """自然衰减（每 24 小时衰减一次）"""
        now = time.time()
        intervals = int((now - self.last_updated) / self._DECAY_INTERVAL_SECONDS)
        if intervals > 0 and self.trust_score > 0:
            self.trust_score = max(0, int(self.trust_score * (self._DECAY_FACTOR ** intervals)))
            self.last_updated = now
            logger.debug(f"Trust decayed for {self.category}: score={self.trust_score}")

    def confirm(self) -> int:
        """人类确认 → 信任 +1"""
        self.maybe_decay()
        self.trust_score += 1
        self.total_confirmed += 1
        self.last_updated = time.time()
        return self.trust_score

    def deny(self):
        """人类拒绝 → 重置为 0"""
        self.trust_score = 0
        self.total_denied += 1
        self.last_updated = time.time()

    def record_auto_approve(self):
        """记录自动批准"""
        self.total_auto_approved += 1
        self.last_updated = time.time()

    @property
    def can_auto_approve(self) -> bool:
        """是否可以自动批准"""
        self.maybe_decay()
        return self.trust_score >= self._AUTO_APPROVE_THRESHOLD


class TrustManager:
    """
    渐进式信任管理器

    规则:
    - 新操作类别: trust_score = 0，需要人类确认
    - 每次人类确认: trust_score += 1
    - trust_score >= 3: 可自动批准
    - 每 24 小时: trust_score *= 0.8（自然衰减）
    - 人类拒绝: trust_score = 0（重置）
    """

    def __init__(self, store_path: Optional[str] = None):
        """
        初始化信任管理器

        Args:
            store_path: 可选的持久化路径（JSON）
        """
        self.logger = logging.getLogger("agora.governance.trust")
        self.records: Dict[str, TrustRecord] = {}
        self.store_path = Path(store_path) if store_path else None

        if self.store_path and self.store_path.exists():
            self._load()

        self.logger.info(f"TrustManager initialized with {len(self.records)} categories")

    def check_trust(self, category: str) -> Tuple[bool, int]:
        """
        检查操作类别是否可自动批准

        Args:
            category: 操作类别（如 "batch_delete", "force_push"）

        Returns:
            (can_auto_approve, trust_score)
        """
        if category not in self.records:
            return False, 0

        record = self.records[category]
        return record.can_auto_approve, record.trust_score

    def confirm(self, category: str) -> int:
        """
        记录人类确认

        Args:
            category: 操作类别

        Returns:
            更新后的 trust_score
        """
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        score = self.records[category].confirm()
        self.logger.info(f"Trust confirmed for {category}: score={score}")
        self._persist()
        return score

    def deny(self, category: str):
        """
        记录人类拒绝（重置信任）

        Args:
            category: 操作类别
        """
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        self.records[category].deny()
        self.logger.info(f"Trust reset for {category}: score=0")
        self._persist()

    def record_auto_approve(self, category: str):
        """记录自动批准事件"""
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        self.records[category].record_auto_approve()
        self._persist()

    def get_stats(self) -> Dict:
        """获取信任统计"""
        stats = {}
        for cat, record in self.records.items():
            stats[cat] = {
                "trust_score": record.trust_score,
                "can_auto_approve": record.can_auto_approve,
                "total_confirmed": record.total_confirmed,
                "total_denied": record.total_denied,
                "total_auto_approved": record.total_auto_approved,
            }
        return stats

    def _persist(self):
        """持久化到磁盘"""
        if not self.store_path:
            return
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            data = {cat: asdict(r) for cat, r in self.records.items()}
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist trust data: {e}")

    def _load(self):
        """从磁盘加载"""
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for cat, record_data in data.items():
                record = TrustRecord(category=cat)
                record.trust_score = record_data.get("trust_score", 0)
                record.last_updated = record_data.get("last_updated", 0.0)
                record.total_confirmed = record_data.get("total_confirmed", 0)
                record.total_denied = record_data.get("total_denied", 0)
                record.total_auto_approved = record_data.get("total_auto_approved", 0)
                self.records[cat] = record

            self.logger.info(f"Loaded {len(self.records)} trust records")

        except Exception as e:
            self.logger.error(f"Failed to load trust data: {e}")
