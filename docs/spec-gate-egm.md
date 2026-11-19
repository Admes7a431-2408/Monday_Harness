# Spec Gate / EGM — Proposal (M-008)

**Status:** proposal only; not implemented or released.  
**Purpose:** reduce defects caused by implicit requirements by reviewing a self-contained specification before code, when risk/complexity justifies the overhead.

## 1. Activation policy (adaptive)
- Skip: trivial, local, reversible, unambiguous changes.
- Lightweight/optional: UI prototypes and small changes without consequential business rules.
- Required: complex business logic; money; security; persistent data/migrations; concurrency; public APIs; architecture/refactors; high-impact ambiguity; or explicit leader/human request.

The leader records why the gate is required or skipped. Avoid applying the ceremony universally.

## 2. Protocol
1. **Explorer:** read-only repo research; cite file/line; report facts separately from inference; surface dependencies, invariants, risks, edge cases and open questions.
2. **Elephant (leader with conversation context):** compose a standalone specification with objective/non-goals, business rules/invariants, flows, interfaces/data, error/recovery behavior, security, concurrency/idempotency where relevant, edge cases, verification criteria and open decisions.
3. **Goldfish (fresh-context auditor):** receives only the spec and expressly allowed references—not the original chat or Elephant's narrative. Reviews whether it can understand without guessing; checks contradictions, omissions, edge cases, assumptions, security/data integrity, testability and complexity. Use one auditor by default; add independent passes only when justified.
4. **Reconcile:** leader classifies findings, resolves questions or asks the human, revises the spec and preserves material disagreement.
5. **Gate decision:** explicit approval recorded in the feature plan/spec. Unresolved critical/important issues block implementation. Maximum two correction/re-audit cycles; then escalate or block.
6. **Implementer:** starts only after approval when Gate is required. Works from the spec, scope and acceptance criteria, not chat reinterpretation.
7. **Reviewer:** different from implementer; reviews implementation against contract/spec, quality and evidence. Fresh-context review must be honestly disclosed if isolation was not achievable.

## 3. Spec minimum content
- Purpose, user-visible outcome, non-goals.
- Rules/invariants, actors and flows.
- Inputs, outputs, data model and interfaces.
- Validation and error behavior; recovery and preservation of user data.
- Security/authorization and privacy implications.
- Concurrency, transactionality, idempotency, migration and rollback as applicable.
- Edge cases and acceptance/verification criteria.
- Open questions, decisions, assumptions and risks.

## 4. Boundaries
- EGM is a workflow protocol; the video plugin is not a dependency.
- Fresh-context auditing can find missing details but does not prove correctness.
- Different models do not guarantee independence; context contamination and prompt bias remain possible.
- Spec approval does not replace automated tests, diff review or runtime validation.
- No endless iteration: bounded audit loops and human escalation.
- Core remains platform/model agnostic. Adapters must report actual isolation/delegation capability, not pretend it exists.

## 5. Updated role contracts
- **Explorer:** fact/inference separation and spec-building evidence; no decisions presented as approved.
- **Implementer:** checks Gate status and refuses to code if required spec is absent/unapproved/inconsistent; keeps changes traceable and considers server-side enforcement, data integrity and concurrency.
- **Reviewer:** separate contract/spec and quality/evidence axes; fresh-context check for high-risk work; explicitly disclose limitations.

## 6. Implementation plan
Audit current adapters' real subagent context boundaries and tool/model controls; define a small spec status/artifact convention; wire Gate decisions to leader workflow without creating a redundant agent role; tests for skip/required/block/escalate scenarios; update docs and run deterministic suite plus supported real-agent validation.

M-008 acceptance criteria in `features.json` govern implementation. This proposal branch is intentionally not merged into main.
