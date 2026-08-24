# CLAUDE.md

Guidance for Claude Code in this repository.

## Read this first

Read `AGENTS.md` before any non-trivial work — it is the authoritative
operating contract (authority order, frozen foundations, Kaggle execution
model, feature-semantics rule, lifecycle, verification, review, and hygiene
rules). This file does not duplicate it.

## Authority hierarchy

Follow `AGENTS.md` §1. When sources conflict: `docs/decision_register.csv` >
frozen contracts/specs (`docs/01`-`docs/07`) and accepted ADRs > accepted
empirical evidence > GitHub Issue wording > existing implementation. Use
`docs/index.md` to locate the current contract for any question; use
`docs/decision_register.csv` for owner-approved decisions (in Vietnamese).

## Execution model

GitHub Issues define execution tasks — MASTER #20 is the current plan.
Kaggle is the primary heavy-compute environment; a full pipeline may span
multiple Kaggle sessions connected by immutable artifacts under
`outputs/runs/<run_id>/`. Local execution is for editing, unit tests, and
small/synthetic verification.

## Commands

The virtual environment at `.venv/` has the dependencies; the system Python
does not. Run everything from the repository root so `src.*` resolves on
`sys.path`.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests/ -q                       # full suite
.venv\Scripts\python.exe -m pytest tests/test_data.py -q           # one file
.venv\Scripts\jupyter.exe lab                                      # notebooks
```

There is no linter or formatter. Tests are a regression aid, not the
verification gate — see `AGENTS.md` §11.

## Working rules

One writer per working tree; keep parallel agent work isolated to its own
branch/worktree (`AGENTS.md` §14). Do not auto-advance lifecycle phases — the
user controls transitions (`AGENTS.md` §6). Do not access held-out data or
results before T17 authorization (`AGENTS.md` §9). Never `git add .`; never
commit raw/processed data or `outputs/` artifacts.
