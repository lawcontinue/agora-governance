# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Agora Governance, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email: [security@example.com] (replace with actual security contact)
3. Include: description, steps to reproduce, potential impact

## Security Model

Agora Governance follows these security principles:

- **Default-deny**: High-risk operations are blocked by default
- **Defense in depth**: Multiple layers (classification, trust, HITL)
- **Fail-safe**: If the governance layer is unreachable, actions are denied
- **Audit trail**: All governance decisions are logged
- **No secrets in code**: API keys and credentials must be provided via environment variables

## Scope

Security vulnerabilities in:
- Policy bypass mechanisms
- Trust escalation flaws
- HITL escalation race conditions
- Audit log tampering

## Out of Scope

- Vulnerabilities in downstream dependencies
- Social engineering attacks
- Issues in example code that don't affect the core library
