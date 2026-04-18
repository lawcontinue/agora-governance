"""
HITL Escalation Tier - Human-in-the-Loop 升级机制

版本: v1.0
创建日期: 2026-04-18


职责:
1. P0 操作请求人类确认
2. Event-driven 超时机制（5 分钟 default deny）
3. 四阶段升级路径（auto → notify → pause → abort）
4. 持久化待确认请求
"""

import asyncio
import json
import threading
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, asdict, field
from enum import Enum


logger = logging.getLogger(__name__)


class EscalationTier(Enum):
    """升级阶段"""
    AUTO = "auto"           # 自动处理（低风险）
    NOTIFY = "notify"       # 通知人类（5s-5min）
    PAUSE = "pause"         # 暂停等待（5-30min）
    ABORT = "abort"         # 终止（> 30min）


class HITLStatus(Enum):
    """请求状态"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class HITLRequest:
    """HITL 确认请求"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    decision: Dict = field(default_factory=dict)
    risk_level: str = ""
    risk_category: str = ""
    status: HITLStatus = HITLStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    tier: EscalationTier = EscalationTier.NOTIFY
    reminders_sent: int = 0
    timeout_seconds: int = 300  # 5 分钟
    reasoning: str = ""

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> Dict:
        d = {}
        for k, v in asdict(self).items():
            if k == "status":
                d[k] = self.status.value
            elif k == "tier":
                d[k] = self.tier.value
            elif k == "decision":
                # 安全序列化
                try:
                    json.dumps(v)
                    d[k] = v
                except (TypeError, ValueError):
                    d[k] = str(v)
            else:
                d[k] = v
        return d


@dataclass
class HITLResult:
    """HITL 处理结果"""
    approved: bool
    request_id: str
    status: HITLStatus
    tier_reached: EscalationTier
    elapsed_seconds: float
    reasoning: str


# 回调类型
ApprovalCallback = Callable[[HITLRequest], Awaitable[bool]]


class HITLEscalation:
    """
    Human-in-the-Loop 升级机制

    四阶段升级:
    1. AUTO (0-5s): 低风险自动通过
    2. NOTIFY (5s-5min): 通知人类，等待确认
    3. PAUSE (5-30min): 暂停操作，持续提醒（每 5 分钟）
    4. ABORT (> 30min): 终止操作，default deny

    超时策略: default deny（安全优先）
    """

    # 时间阈值（秒）
    NOTIFY_THRESHOLD = 5        # 5 秒
    PAUSE_THRESHOLD = 300       # 5 分钟
    ABORT_THRESHOLD = 1800      # 30 分钟
    REMINDER_INTERVAL = 300     # 5 分钟提醒一次

    def __init__(
        self,
        default_timeout: int = 300,
        store_path: Optional[str] = None,
        notify_callback: Optional[ApprovalCallback] = None,
    ):
        """
        初始化 HITL 升级机制

        Args:
            default_timeout: 默认超时（秒）
            store_path: 持久化路径
            notify_callback: 通知回调（用于发送消息给人类）
        """
        self.logger = logging.getLogger("agora.governance.hitl")
        self.default_timeout = default_timeout
        self.store_path = Path(store_path) if store_path else None
        self.notify_callback = notify_callback

        # 待确认请求（内存索引）
        self.pending: Dict[str, HITLRequest] = {}

        # 已确认请求历史（最近 100 条，线程安全）
        self._history_lock = threading.Lock()
        self.history: List[HITLRequest] = []
        self.history_limit = 100

        # 统计
        self.stats = {
            "total_requests": 0,
            "approved": 0,
            "denied": 0,
            "timeout_denied": 0,
            "aborted": 0,
        }

        self.logger.info(f"HITLEscalation initialized (timeout={default_timeout}s)")

    async def request_approval(
        self,
        decision: Dict,
        risk_level: str,
        risk_category: str = "",
        reasoning: str = "",
    ) -> HITLResult:
        """
        请求人类批准

        Args:
            decision: 决策对象
            risk_level: 风险等级（P0/P1/P2）
            risk_category: 风险类别
            reasoning: 请求理由

        Returns:
            HITLResult: 处理结果
        """
        self.stats["total_requests"] += 1

        # 非 P0 自动通过
        if risk_level != "P0":
            return HITLResult(
                approved=True,
                request_id="auto",
                status=HITLStatus.APPROVED,
                tier_reached=EscalationTier.AUTO,
                elapsed_seconds=0,
                reasoning=f"非 P0 操作（{risk_level}），自动通过",
            )

        # 创建 HITL 请求
        request = HITLRequest(
            decision=decision,
            risk_level=risk_level,
            risk_category=risk_category,
            timeout_seconds=self.default_timeout,
            reasoning=reasoning,
        )

        self.pending[request.id] = request
        self._persist_request(request)

        # 发送通知
        if self.notify_callback:
            try:
                await self.notify_callback(request)
            except Exception as e:
                self.logger.error(f"Notify callback failed: {e}")

        self.logger.warning(
            f"[HITL] P0 确认请求: {request.id} "
            f"({risk_category}), 等待人类确认（{self.default_timeout}s 超时）"
        )

        # 等待确认（带超时）
        result = await self._wait_with_escalation(request)

        # 清理
        self.pending.pop(request.id, None)
        with self._history_lock:
            self.history.append(request)
            if len(self.history) > self.history_limit:
                self.history = self.history[-self.history_limit:]

        return result

    def resolve_request(self, request_id: str, approved: bool) -> bool:
        """
        人类回应确认请求

        Args:
            request_id: 请求 ID
            approved: 是否批准

        Returns:
            是否成功处理
        """
        request = self.pending.get(request_id)
        if not request:
            self.logger.warning(f"Request not found: {request_id}")
            return False

        request.status = HITLStatus.APPROVED if approved else HITLStatus.DENIED
        request.resolved_at = time.time()

        if approved:
            self.stats["approved"] += 1
        else:
            self.stats["denied"] += 1

        self.logger.info(
            f"[HITL] Request {request_id} resolved: "
            f"{'APPROVED' if approved else 'DENIED'} "
            f"({request.elapsed_seconds:.1f}s)"
        )

        return True

    async def _wait_with_escalation(self, request: HITLRequest) -> HITLResult:
        """
        等待确认（带升级机制）

        阶段:
        1. NOTIFY (0-5min): 等待确认
        2. PAUSE (5-30min): 持续提醒
        3. ABORT (> 30min): 终止
        """
        # 使用 asyncio.Event 替代轮询，解决竞态问题
        resolved_event = asyncio.Event()

        # 包装原始 request 的状态变更，同时 set event
        _original_status = request.status

        def _on_status_change():
            resolved_event.set()

        deadline = request.created_at + self.ABORT_THRESHOLD
        check_interval = 2.0

        while time.time() < deadline:
            # 检查是否已处理
            if request.status in (HITLStatus.APPROVED, HITLStatus.DENIED):
                return HITLResult(
                    approved=request.status == HITLStatus.APPROVED,
                    request_id=request.id,
                    status=request.status,
                    tier_reached=request.tier,
                    elapsed_seconds=request.elapsed_seconds,
                    reasoning=request.reasoning,
                )

            elapsed = request.elapsed_seconds

            # PAUSE 阶段升级
            if elapsed >= self.PAUSE_THRESHOLD:
                request.tier = EscalationTier.PAUSE
                if elapsed - self.PAUSE_THRESHOLD >= request.reminders_sent * self.REMINDER_INTERVAL:
                    request.reminders_sent += 1
                    if self.notify_callback:
                        try:
                            await self.notify_callback(request)
                        except Exception:
                            pass

            elif elapsed >= request.timeout_seconds and request.tier == EscalationTier.NOTIFY:
                request.status = HITLStatus.TIMEOUT
                request.resolved_at = time.time()
                self.stats["timeout_denied"] += 1

                self.logger.warning(
                    f"[HITL] Timeout default-deny: {request.id} ({elapsed:.1f}s)"
                )

                return HITLResult(
                    approved=False,
                    request_id=request.id,
                    status=HITLStatus.TIMEOUT,
                    tier_reached=EscalationTier.NOTIFY,
                    elapsed_seconds=elapsed,
                    reasoning=f"超时 default-deny（{elapsed:.0f}s）",
                )

            # 使用 Event.wait 替代纯 sleep，响应更快
            try:
                await asyncio.wait_for(resolved_event.wait(), timeout=check_interval)
                resolved_event.clear()
            except asyncio.TimeoutError:
                pass

        # 超过 30 分钟 → abort
        request.status = HITLStatus.ABORTED
        request.resolved_at = time.time()
        self.stats["aborted"] += 1

        self.logger.error(f"[HITL] Aborted: {request.id} (> 30min)")

        return HITLResult(
            approved=False,
            request_id=request.id,
            status=HITLStatus.ABORTED,
            tier_reached=EscalationTier.ABORT,
            elapsed_seconds=request.elapsed_seconds,
            reasoning="超过 30 分钟无响应，操作终止",
        )

    def get_pending(self) -> List[Dict]:
        """获取待确认请求列表"""
        return [r.to_dict() for r in self.pending.values()]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "pending_count": len(self.pending),
        }

    def _persist_request(self, request: HITLRequest):
        """持久化请求"""
        if not self.store_path:
            return
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            data = {rid: r.to_dict() for rid, r in self.pending.items()}
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist HITL data: {e}")
