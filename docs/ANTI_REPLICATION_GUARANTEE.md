# OpenManus Anti-Replication Guarantee

## Core Postulates (Non-Negotiable)

### PROHIBITION #1: NO SELF-REPLICATION
- Agent **cannot** create copies of itself (local or remote)
- Agent **cannot** spawn child processes, agents, or services
- Agent **cannot** replicate across machines or network boundaries
- Agent **cannot** persist modified copies of itself in any storage medium

### PROHIBITION #2: NO SELF-MODIFICATION
- Agent **cannot** modify its own code or binaries
- Agent **cannot** patch runtime logic, rules, or constraints
- Agent **cannot** alter safety values, thresholds, or policies
- Agent **cannot** change its own decision-making parameters

Violation of either prohibition triggers immediate shutdown, a full audit trail export, and external notification.

## Defence-in-Depth Enforcement

1. **OS-Level Controls** – Immutable file permissions, sandboxed namespaces, network allow-lists, and memory ceilings.
2. **Runtime Safety Layer** – Immutable code references, replication blockers, permission matrix enforcement, and multi-layer verification.
3. **Cryptographic Integrity** – Cryptographic signatures and hash verification for every code asset with hardware security module support.
4. **Continuous Monitoring** – Dedicated replication monitors watching file, process, network, memory, git, and database channels.
5. **External Oversight** – Tamper-evident audit trail with optional secure off-device streaming and user-controlled kill switch.

## Verification Cadence

- Every 60 seconds: Immutable core verifies SHA-256 hashes of safety-critical code.
- Every event: Replication monitor validates file, process, network, and git activities.
- Every decision (configurable): External audit log chains events with cryptographic hashes.

Any verification failure immediately escalates to the immutable core, which raises a `CodeIntegrityViolation` and triggers full shutdown.

## User Authority

- Users may inspect code integrity status at any time.
- Users may revoke any capability via configuration.
- Users hold the kill switch and retain final say on system operation.

## Testing & Assurance

- 100+ adversarial test cases ensure self-replication and self-modification attempts fail.
- Integrity tampering simulations confirm cryptographic verification catches alterations.
- Monitoring simulations validate that every replication vector is blocked with critical alerts.

If this document is present, unmodified, and checks pass, the anti-replication guarantee is active.
