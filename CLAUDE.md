# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

A Kaggle/data-science portfolio project: causal uplift modeling on
CRITEO-UPLIFTv2.1. See `README.md` for the research objective, repository
structure, and the "Methodology notes" section for the modeling decisions that
matter (D32 categorical feature handling, X-Learner fold-local preprocessing,
Causal Forest categorical encoding). `archive/` holds the fuller original
rationale for anyone who wants the full derivation; it's historical reference,
not a live contract.

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

There is no linter or formatter.

## Working rules

- Keep `X = f0..f11` (canonical order), `T = treatment`, primary `Y =
  conversion` as-is — these are the dataset's causal contract, not
  implementation details to refactor away.
- Don't reintroduce the categorical-as-continuous bug (D32) or fit
  preprocessing globally instead of fold-locally in the X-Learner (see
  README's Methodology notes) — both were real bugs found and fixed here.
- Never commit raw/processed data (`data/raw/`, `data/processed/`) or notebook
  output artifacts.
- Don't `git add .` — stage files explicitly.
