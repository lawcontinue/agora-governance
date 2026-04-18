"""
Spending governance example — demonstrates how to use Agora Governance
to control agent spending on API calls and purchases.

This is the same pattern discussed in anthropics/anthropic-cookbook#546.
"""

from agora_governance.core.operation_classifier import (
    OperationClassifier,
    RiskPattern,
    RiskLevel,
)

# Create classifier with spending-specific patterns
classifier = OperationClassifier()

# Add spending-specific P0 patterns
classifier.add_pattern(RiskPattern(
    pattern="payment",
    category="spending",
    level=RiskLevel.P0,
    use_regex=False,
))
classifier.add_pattern(RiskPattern(
    pattern="purchase",
    category="spending",
    level=RiskLevel.P0,
    use_regex=False,
))
classifier.add_pattern(RiskPattern(
    pattern=r"\$\d+",
    category="spending_amount",
    level=RiskLevel.P1,
    use_regex=True,
))

# Test classification
test_actions = [
    {"action": "search documents"},                    # P2 - safe
    {"action": "send email to team"},                  # P1 - medium risk
    {"action": "purchase premium API subscription"},   # P0 - spending!
    {"action": "payment $50 to vendor X"},             # P0 - spending!
    {"action": "send notifications", "targets": list(range(10))},  # P0 - batch!
]

for decision in test_actions:
    risk = classifier.classify(decision)
    action = decision.get("action", "unknown")
    targets = len(decision.get("targets", []))
    print(f"  {action:45s} → {risk.level.value} ({risk.default_action})")
    if targets:
        print(f"    ↳ Batch: {targets} targets → auto-escalated to P0")
