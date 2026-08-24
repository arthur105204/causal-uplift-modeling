# Archive

Historical material from this project's earlier, heavily-governed research
phase: the owner-approved decision register, ADRs, and the numbered
causal/data/audit/methodology/experiment/metric contracts, plus the operating
contract (`AGENTS.md`) that enforced them.

None of this is a live specification for the current repository — see the
root `README.md` "Methodology notes" section for the condensed version of
what actually matters (D32 categorical feature handling, the X-Learner
fold-local preprocessing fix, and the Causal Forest categorical encoding
decision, D34). This folder is kept only so the full original rationale and
decision history remains easy to find.

- `docs/decision_register.csv` — the full decision log (D01–D34), in
  Vietnamese, with rationale for each decision and alternatives rejected.
- `docs/adr/` — architecture decision records, including
  `ADR-CF-implementation.md` (Causal Forest implementation and the categorical
  representation blocker D34 resolved).
- `docs/01_causal_contract.md` through `docs/07_metric_specification.md` — the
  original frozen specifications.
- `AGENTS.md` — the operating contract (authority hierarchy, lifecycle,
  held-out isolation) that governed the pre-simplification repository.
