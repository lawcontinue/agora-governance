"""
HITL Escalation Tier - Human-in-the-Loop escalation mechanism

Version: v1.1
License: Apache-2.0
"""

import asyncio
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, asdict, field
from enum import Enum


logger = logging.getLogger(__name__)


class EscalationTier(Enum):
    AUTO = "auto"
    NOTIFY = "notify"
    PAUSE = "pause"
    ABORT = "abort"


class HITLStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class HITLRequest:
    """HITL approval request."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    decision: Dict = field(default_factory=dict)
    risk_level: str = ""
    risk_category: str = ""
    status: HITLStatus = HITLStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    tier: EscalationTier = EscalationTier.NOTIFY
    reminders_sent: int = 0
    timeout_seconds: int = 300
    reasoning: str = ""

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> Dict:
        d = {}
        for k, v in asdict(self).items():
            if isinstance(v, Enum):
                d[k] = v.value
            else:
                try:
                    json.dumps(v)
                    d[k] = v
                except (TypeError, ValueError):
                    d[k] = str(v)
        return d


@dataclass
class HITLResult:
    """HITL processing result."""
    approved: bool
    request_id: str
    status: HITLStatus
    tier_reached: EscalationTier
    elapsed_seconds: float
    reasoning: str


ApprovalCallback = Callable[[HITLRequest], Awaitable[bool]]


class HITLEscalation:
    """
    Human-in-the-Loop escalation mechanism.

    Four escalation stages:
    1. AUTO (0-5s): Low-risk auto-pass
    2. NOTIFY (5s-5min): Notify human, await confirmation
    3. PAUSE (5-30min): Pause operation, periodic reminders
    4. ABORT (> 30min): Terminate, default deny
    """

    NOTIFY_THRESHOLD = 5
    PAUSE_THRESHOLD = 300
    ABORT_THRESHOLD = 1800
    REMINDER_INTERVAL = 300

    def __init__(
        self,
        default_timeout: int = 300,
        store_path: Optional[str] = None,
        notify_callback: Optional[ApprovalCallback] = None,
    ):
        self.logger = logging.getLogger("agora.governance.hitl")
        self.default_timeout = default_timeout
        self.store_path = Path(store_path) if store_path else None
        self.notify_callback = notify_callback

        self.pending: Dict[str, HITLRequest] = {}

        # P0-7 fix: use asyncio.Lock instead of threading.Lock
        self._lock = asyncio.Lock()
        self.history: List[HITLRequest] = []
        self.history_limit = 100

        # P0-2 fix: event dict for signaling resolution
        self._events: Dict[str, asyncio.Event] = {}

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
        self.stats["total_requests"] += 1

        if risk_level != "P0":
            return HITLResult(
                approved=True,
                request_id="auto",
                status=HITLStatus.APPROVED,
                tier_reached=EscalationTier.AUTO,
                elapsed_seconds=0,
                reasoning=f"Non-P0 operation ({risk_level}), auto-approved",
            )

        request = HITLRequest(
            decision=decision,
            risk_level=risk_level,
            risk_category=risk_category,
            timeout_seconds=self.default_timeout,
            reasoning=reasoning,
        )

        # Create resolution event for this request
        self._events[request.id] = asyncio.Event()
        self.pending[request.id] = request
        self._persist_request(request)

        if self.notify_callback:
            try:
                await self.notify_callback(request)
            except Exception as e:
                self.logger.error(f"Notify callback failed: {e}")

        self.logger.warning(
            f"[HITL] P0 approval request: {request.id} "
            f"({risk_category}), awaiting human response ({self.default_timeout}s timeout)"
        )

        result = await self._wait_with_escalation(request)

        # Cleanup
        self.pending.pop(request.id, None)
        self._events.pop(request.id, None)
        async with self._lock:
            self.history.append(request)
            if len(self.history) > self.history_limit:
                self.history = self.history[-self.history_limit:]

        return result

    def resolve_request(self, request_id: str, approved: bool) -> bool:
        """Resolve a pending HITL request (call from human-facing endpoint)."""
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

        # P0-2 fix: trigger the event so _wait_with_escalation wakes immediately
        event = self._events.get(request_id)
        if event:
            event.set()

        self.logger.info(
            f"[HITL] Request {request_id} resolved: "
            f"{'APPROVED' if approved else 'DENIED'} "
            f"({request.elapsed_seconds:.1f}s)"
        )
        return True

    async def _wait_with_escalation(self, request: HITLRequest) -> HITLResult:
        event = self._events.get(request.id)
        if not event:
            # Should not happen, but defensive
            event = asyncio.Event()
            self._events[request.id] = event

        deadline = request.created_at + self.ABORT_THRESHOLD
        check_interval = 2.0

        while time.time() < deadline:
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

            # Timeout default-deny (NOTIFY stage exceeded)
            if elapsed >= request.timeout_seconds and request.tier == EscalationTier.NOTIFY:
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
                    reasoning=f"Timeout default-deny ({elapsed:.0f}s)",
                )

            # PAUSE stage escalation
            if elapsed >= self.PAUSE_THRESHOLD:
                request.tier = EscalationTier.PAUSE
                reminders_due = int((elapsed - self.PAUSE_THRESHOLD) / self.REMINDER_INTERVAL)
                if reminders_due > request.reminders_sent:
                    request.reminders_sent = reminders_due
                    if self.notify_callback:
                        try:
                            await self.notify_callback(request)
                        except Exception:
                            pass

            # Wait for resolution event (P0-2 fix: event is set by resolve_request)
            try:
                await asyncio.wait_for(event.wait(), timeout=check_interval)
                event.clear()
            except asyncio.TimeoutError:
                pass

        # > 30 minutes → abort
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
            reasoning="No response after 30 minutes, operation aborted",
        )

    def get_pending(self) -> List[Dict]:
        return [r.to_dict() for r in self.pending.values()]

    def get_stats(self) -> Dict:
        return {**self.stats, "pending_count": len(self.pending)}

    def _persist_request(self, request: HITLRequest):
        if not self.store_path:
            return
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            data = {rid: r.to_dict() for rid, r in self.pending.items()}
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist HITL data: {e}")
