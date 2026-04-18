"""
Trust Manager - Graduated trust scoring for operations

版本: v1.0
创建日期: 2026-04-18


职责:
1. Manage trust scores per operation category
2. Graduated trust (first 3 require confirmation, then auto-approve)
3. 24-hour natural decay (trust_score *= 0.8)
4. Denial resets to 0
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from typing import ClassVar


logger = logging.getLogger(__name__)


@dataclass
class TrustRecord:
    """Trust record for a single category."""
    category: str
    trust_score: int = 0
    last_updated: float = 0.0  # timestamp
    total_confirmed: int = 0
    total_denied: int = 0
    total_auto_approved: int = 0

    DECAY_FACTOR: ClassVar[float] = 0.8
    DECAY_INTERVAL_SECONDS: ClassVar[float] = 86400.0  # 24 hours
    AUTO_APPROVE_THRESHOLD: ClassVar[int] = 3

    def maybe_decay(self):
        """自然衰减（每 24 小时衰减一次）"""
        now = time.time()
        intervals = int((now - self.last_updated) / self.DECAY_INTERVAL_SECONDS)
        if intervals > 0 and self.trust_score > 0:
            self.trust_score = max(0, int(self.trust_score * (self.DECAY_FACTOR ** intervals)))
            self.last_updated = now
            logger.debug(f"Trust decayed for {self.category}: score={self.trust_score}")

    def confirm(self) -> int:
        """Human confirmation -> trust +1"""
        self.maybe_decay()
        self.trust_score = min(self.trust_score + 1, 10)  # Cap at 10
        self.total_confirmed += 1
        self.last_updated = time.time()
        return self.trust_score

    def deny(self):
        """Human denial -> reset to 0"""
        self.trust_score = 0
        self.total_denied += 1
        self.last_updated = time.time()

    def record_auto_approve(self):
        """Record auto-approval"""
        self.total_auto_approved += 1
        self.last_updated = time.time()

    @property
    def can_auto_approve(self) -> bool:
        """Whether auto-approval is allowed"""
        self.maybe_decay()
        return self.trust_score >= self.AUTO_APPROVE_THRESHOLD


class TrustManager:
    """
    Graduated trust manager

    规则:
    - New category: trust_score = 0, requires human confirmation
    - Each confirmation: trust_score += 1
    - trust_score >= 3: can auto-approve
    - Every 24h: trust_score *= 0.8 (natural decay)
    - Human denial: trust_score = 0 (reset)
    """

    def __init__(self, store_path: Optional[str] = None):
        """
        初始化信任管理器

        Args:
            store_path: Optional persistence path (JSON)
        """
        self.logger = logging.getLogger("agora.governance.trust")
        self.records: Dict[str, TrustRecord] = {}
        self.store_path = Path(store_path) if store_path else None

        if self.store_path and self.store_path.exists():
            self._load()

        self.logger.info(f"TrustManager initialized with {len(self.records)} categories")

    def check_trust(self, category: str) -> Tuple[bool, int]:
        """
        Check if category can be auto-approved

        Args:
            category: Operation category (e.g. "batch_delete", "force_push")

        Returns:
            (can_auto_approve, trust_score)
        """
        if category not in self.records:
            return False, 0

        record = self.records[category]
        return record.can_auto_approve, record.trust_score

    def confirm(self, category: str) -> int:
        """
        Record human confirmation

        Args:
            category: Operation category

        Returns:
            Updated trust_score
        """
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        score = self.records[category].confirm()
        self.logger.info(f"Trust confirmed for {category}: score={score}")
        self._persist()
        return score

    def deny(self, category: str):
        """
        Record human denial (reset trust)

        Args:
            category: Operation category
        """
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        self.records[category].deny()
        self.logger.info(f"Trust reset for {category}: score=0")
        self._persist()

    def record_auto_approve(self, category: str):
        """Record auto-approval事件"""
        if category not in self.records:
            self.records[category] = TrustRecord(category=category)

        self.records[category].record_auto_approve()
        self._persist()

    def get_stats(self) -> Dict:
        """Get trust statistics"""
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
        """Persist to disk"""
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
        """Load from disk"""
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
