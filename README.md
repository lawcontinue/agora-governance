# 🏛️ Agora Governance

Production-grade AI Agent governance framework — policy enforcement, trust management, and human-in-the-loop escalation.

> **不只在梦中预见，更在现实中执行。**

[English](#features) | [中文文档](#中文文档)

## Why This Exists

AI agents with tool access can cause real-world impact — deleting databases, sending emails, making payments. Most agent frameworks leave governance as an afterthought. Agora Governance makes it a first-class, deterministic, auditable layer between the agent's decision to act and the action itself.

**The gap**: Policy rules are point-in-time correct. They evaluate actions in isolation. They can't detect trajectory drift — an agent doing the right kind of thing but cumulatively drifting from the original goal. Agora Governance addresses this at multiple layers.

## Features

- **Operation Classification** — Automatic P0/P1/P2 risk classification with configurable patterns
- **Graduated Trust** — Confirmation history per action pattern; trust grows with consistent approval, decays over time, resets on denial
- **HITL Escalation** — 4-stage human-in-the-loop: AUTO → NOTIFY → PAUSE → ABORT, with configurable timeout
- **Default-Deny** — High-risk operations blocked by default; approval is opt-in, not opt-out
- **Batch Detection** — Operations targeting >5 recipients auto-escalate to P0
- **Voting Mechanism** — Multi-agent consensus with majority, unanimous, and weighted voting
- **Hallucination Detection** — Pattern-based detection of common LLM hallucination patterns
- **Precedent Store** — Historical decision retrieval for consistent governance

## Quick Start

```bash
pip install agora-governance
```

```python
from agora_governance.core import OperationClassifier, TrustManager, HITLEscalation
from agora_governance.core.operation_classifier import RiskLevel

# 1. Classify an operation
classifier = OperationClassifier()
risk = classifier.classify({"action": "rm -rf /tmp/old_data"})

print(risk.level)        # RiskLevel.P0
print(risk.default_action)  # "deny"

# 2. Check trust level
trust_mgr = TrustManager()
trust_level = trust_mgr.check("agent-1", "batch_delete")
# First time: requires confirmation

# After 3 approved actions: auto-approve with logging

# 3. HITL escalation (async)
escalation = HITLEscalation(timeout_seconds=300)  # 5min default-deny
result = await escalation.request_approval(
    action="send_email",
    requester="agent-1",
    risk_level=RiskLevel.P1,
)
# If no human responds in 5 minutes: denied by default
```

## Architecture

```
Agent Action
    │
    ▼
┌─────────────────────┐
│  Operation Classifier │ ── P0/P1/P2 risk level
└────────┬────────────┘
         │
    ┌────▼────┐
    │ P0?     │── Yes ──▶ Default DENY + HITL Escalation
    │         │
    │ P1?     │── Yes ──▶ Allow + Audit + Optional HITL
    │         │
    │ P2?     │── Yes ──▶ Allow + Log
    └─────────┘
         │
    ┌────▼────────────┐
    │ Trust Manager    │ ── Graduated trust check
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │ HITL Escalation  │ ── Human approval (if needed)
    └────┬────────────┘
         │
    ┌────▼────┐
    │ Execute  │ or Deny
    └─────────┘
```

## Configuration

Custom risk patterns via JSON:

```json
{
  "p0_patterns": [
    {
      "pattern": "DROP TABLE",
      "category": "db_delete",
      "level": "P0",
      "use_regex": false
    }
  ],
  "p1_patterns": [
    {
      "pattern": "\\bDELETE\\b",
      "category": "delete_op",
      "level": "P1",
      "use_regex": true
    }
  ]
}
```

```python
classifier = OperationClassifier(config_path="policies.json")
```

## Compliance Alignment

Designed to support compliance with:

- **《生成式人工智能服务管理暂行办法》**（中国）
- **EU AI Act**（欧洲）
- **OWASP Agentic Top 10**（安全）
- **ISO 42001**（AI 管理体系）

## Requirements

- Python 3.10+
- No external runtime dependencies (stdlib only)

## License

Apache License 2.0 — enterprise-friendly, permissive.

---

## 中文文档

### 为什么需要这个框架？

当 AI Agent 拥有工具调用能力时，它可以造成真实世界的影响——删除数据库、发送邮件、执行支付。大多数 Agent 框架把治理放在事后考虑。Agora Governance 把它变成一个确定性的、可审计的、一等公民的治理层。

### 核心特性

| 特性 | 说明 |
|------|------|
| **操作分级** | 自动将操作分为 P0（高风险/默认拒绝）、P1（中风险/审计）、P2（低风险/日志） |
| **渐进式信任** | 根据历史确认记录动态调整信任等级，信任可衰减、可重置 |
| **人机协同升级** | 4阶段升级机制：自动 → 通知 → 暂停 → 终止，可配置超时 |
| **批量检测** | 目标 >5 个的操作自动升级为 P0 |
| **投票共识** | 多 Agent 投票，支持多数决、一致同意、加权投票 |
| **幻觉检测** | 基于模式的 LLM 幻觉检测 |
| **先例检索** | 历史决策检索，确保治理一致性 |

### 快速开始

```python
from agora_governance.core import OperationClassifier

classifier = OperationClassifier()
risk = classifier.classify({"action": "drop table users"})

print(risk.level)         # P0
print(risk.default_action)  # deny（默认拒绝）
```

### 合规对齐

- ✅ 《生成式人工智能服务管理暂行办法》
- ✅ EU AI Act
- ✅ OWASP Agentic Top 10
- ✅ ISO 42001

### 许可证

Apache License 2.0
