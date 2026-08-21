# Crash Codebase Map -- CRITEO-UPLIFTv2.1 Causal Uplift Modeling

**Evidence labels.** Every claim is `CONFIRMED BY CODE` unless explicitly
marked `INFERRED` or `UNKNOWN`. Source code wins over this document always.

---

## READ THIS FIRST — 30 MINUTE CRASH PATH

If you only have 30 minutes, read these sections in this order and stop:

| Min | Read | Why |
|---|---|---|
| 0-3 | **§1 Project in 60 Seconds** + **§3 Frozen Contracts** | X/T/Y/exposure/`_source_row_id`/held-out. Get these wrong and nothing else matters. |
| 3-8 | **§2 Data-Flow Diagram** + **§4 End-to-End Flow** | The single trace: parquet -> split -> partition load -> fit -> tau -> Qini -> artifacts. |
| 8-12 | **§12 Metrics** | Qini above random, sort direction, tie-break, why AUC is diagnostic only. You will be asked this. |
| 12-16 | **§8 X-Learner** | The densest correctness logic in the repo. Know exactly where leakage would occur. |
| 16-21 | **§9 Causal Forest** + **§10 Jacobian / Support** | `econml.grf` is not DML; honesty; `n_jobs=1`; hard vs diagnostic checks. |
| 21-25 | **§11 T11 Runner** | Cohort identity, checkpoints, resume, serialization. |
| 25-28 | **§7 T-Learner** | Short. Mostly confirms the pattern X-Learner extends. |
| 28-30 | **§19 Must Know** + **§16 Known Weaknesses** | The 12 non-bluffable facts and the 3 honest weaknesses. |

Skip on a first pass: §5, §6, §13, §14, §15, §17, §18, Appendices.
Then take the **Closed-Book Self Check** at the end of this document.

---

# Repository Snapshot

| | |
|---|---|
| **Branch** | `temp/t11-cross-machine` |
| **HEAD** | `f4388ebebd6712af336530ce3a061b45657493be` |
| **Generated at** | 2026-08-21 (UTC) |
| **Tracked files** | 72 |
| **Scan disposition** | `SCAN_COMPLETE_WITH_KNOWN_GAPS` |

> This study guide describes the repository state at the commit above.
> If HEAD changes, implementation claims must be reverified.

**Nothing here was verified by execution.** This machine lacks the gitignored
local data artifacts (`configs/data_manifest.json`, `data/processed/*.parquet`,
`outputs/runs/`), so every claim comes from reading source, not running it.

---

# 1. Project in 60 Seconds

Rank people by **how much treatment changes their conversion probability**
(CATE), not by how likely they are to convert. CRITEO-UPLIFTv2.1, 13,979,592 rows.

- `X` = exactly `f0..f11` (float64); `T` = `treatment`; `Y` = `conversion`
- `exposure` is post-assignment, **audit-only, banned from X**
- `_source_row_id` = the parquet row ordinal; identity/alignment only, never a feature
- Frozen 70/15/15 split, seed 42, joint-`(T,Y)`-stratified. Held-out is
  **structurally sealed** until a T17 release marker file exists.
- Estimators: Random reference; Response LightGBM (**not causal**); T-Learner;
  X-Learner; Causal Forest (`econml.grf.CausalForest`)
- Primary metric: **Qini above the theoretical expected-random line**, VALIDATION only

The most important cultural fact: **compute is one-shot**. Decision D31 locks
exactly ONE full-scale Causal Forest fit through T18. Poor model performance is
explicitly *not* a reason to refit.

---

# 2. Architecture / Data Flow Diagram

```
raw CRITEO CSV (publisher release, sha256-pinned)
   |
   |  src/data.py -> convert_csv_to_parquet
   |                 _augment_with_source_ids   (np.arange per batch)
   |                 validate_processed_parquet (ordinal continuity + SemanticHasher)
   |                 promote_processed_with_rollback
   v
data/processed/criteo-uplift-v2.1.parquet          [gitignored, local only]
   f0..f11 | treatment | conversion | visit | exposure | _source_row_id
   |
   |  configs/data_manifest.json  [gitignored local selector]
   |  src/data.py -> load_selector -> open_processed_dataset
   |                 (verify_expected_file_checksum BEFORE Arrow opens it)
   v
pyarrow.dataset.Dataset  (schema == PROCESSED_SCHEMA, else fail closed)
   |
   |  src/split.py -> assign_split   [ONE TIME, seed 42, joint-(T,Y) stratified]
   v
outputs/runs/<t05_run>/audit/split_membership.csv     [gitignored]
   (_source_row_id -> train | validation | held_out)
   hash-locked in configs/t05_split.json :: membership_sha256
   train 9,785,714 | validation 2,096,938 | held_out 2,096,940
   |
   |  src/split.py -> SplitDataset.train_ids() / .validation_ids()
   |                  .held_out_ids()  ==> HeldOutAccessError until T17
   v
   +-- RUNNER PATH (T11 only) -----------------------------------------+
   |   materialize_pandas_by_source_row_id                             |
   |   Dataset.take(int64 positions)  -- compact positional read       |
   +-------------------------------------------------------------------+
   +-- NOTEBOOK PATH (T07-T10) ----------------------------------------+
   |   materialize_pandas(row_limit=None)                              |
   |   whole-population frame, lazily cached via get_full_frame()      |
   +-------------------------------------------------------------------+
   |
   |  src/preprocessing.py -> IdentityFeatureTransform
   |     (select f0..f11, order-checked, float64; fit() is a no-op but the
   |      fit-on-TRAIN-only calling convention is enforced and tested)
   v
   +--> Response  : lightgbm_baseline.fit_binary_classifier  x1
   +--> T-Learner : fit_binary_classifier x2 (per arm) + tlearner.compute_tau
   +--> X-Learner : x4 nuisance + fit_regressor x2 + xlearner.combine_tau
   +--> CausalF.  : causal_forest_baseline.fit_causal_forest
   |                orchestrated by causal_forest_runner.run_stage()
   |                driven by scripts/t11_run_stage.py
   v
tau_hat on VALIDATION only, aligned by _source_row_id
   |
   |  src/metrics.py -> evaluate_ranking / compute_ate / response_diagnostics
   v
Qini above random | uplift@K | incremental conversions | decile table | ATE
   |
   |  src/data.py -> write_bytes_new_atomic / write_json_new
   |                 finalize_artifact_manifest
   v
outputs/runs/<run_id>/
   audit/checkpoints/001..004.json   (hash-chained)
   audit/run_config.json             (written once, never mutated)
   audit/resource_evidence.json
   audit/diagnostic_support_summary.json
   audit/artifact_manifest.json      (written last, hashes everything)
   models/causal_forest.pkl
   predictions/validation_tau.parquet
   |
   v
[SEALED] T17 held-out evaluation -- one time, after pre-test freeze
```

---

# 3. Frozen Data / Causal / Evaluation Contracts

`FROZEN` = owner/ADR-governed. `IMPL` = implementation detail.
`RESOURCE` = execution/compute decision.

| Item | Value | Class | Code evidence |
|---|---|---|---|
| `X` | exactly `f0..f11`, ordered, float64 | FROZEN | `data.py -> FEATURE_COLUMNS`, `assert_model_feature_contract` |
| `T` | `treatment`, binary | FROZEN | `data.py -> TREATMENT_COLUMN` |
| Primary `Y` | `conversion`, binary | FROZEN | `data.py -> PRIMARY_OUTCOME` |
| Secondary `Y` | `visit`, separate pipeline | FROZEN | `data.py -> SECONDARY_OUTCOME` |
| `exposure` | post-assignment, audit-only, **banned from X**, cannot filter the population or define eligibility | FROZEN | `data.py -> AUDIT_ONLY_COLUMN`, `FORBIDDEN_MODEL_COLUMNS`; `load_selector` requires it be the sole `post_assignment_columns` entry |
| `_source_row_id` | zero-based parquet row ordinal, non-feature | FROZEN | `data.py -> SOURCE_ROW_ID`; `load_selector` rejects `model_feature != False`; in `FORBIDDEN_MODEL_COLUMNS` |
| Row retention | no row removed for duplicates/tails/rare outcomes | FROZEN | `audit.py -> duplicate_profile_summary` returns `row_removal_authorized: False` |
| Split | 70/15/15, seed 42, joint-`(T,Y)` | FROZEN | `split.py -> SPLIT_SEED, TRAIN_FRACTION, assign_split` |
| Held-out seal | needs a T17 release manifest file with `status == "HELDOUT_RELEASED"` | FROZEN | `split.py -> SplitDataset.held_out_ids` |
| Estimand | assignment/ITT CATE for ranking | FROZEN | `docs/01_causal_contract.md`, README |
| Primary metric | `qini_above_random` | FROZEN | `metrics_common.py -> metric_definitions_payload` |
| Ranking convention | score DESC, tie-break `_source_row_id` ASC | FROZEN | `metrics.py -> evaluate_ranking` sort |
| Response AUC/AP/logloss | diagnostic only, never selects a winner | FROZEN | D27; `response_diagnostics` docstring |
| PEHE on real data | prohibited | FROZEN | D28; `prohibited_labels` |
| Uncertainty | 500-draw paired arm-stratified bootstrap (T15) | FROZEN | `metric_definitions_payload -> uncertainty` |
| CF `n_jobs=1` | determinism requirement, **not** perf | FROZEN (correctness) | `causal_forest_baseline.py` inline comment |
| CF other hyperparams | econml package defaults, untouched | FROZEN (by declaration) | `FROZEN_CAUSAL_FOREST_CONFIG` |
| LightGBM hyperparams | library defaults except objective/seed/determinism | IMPL | `lightgbm_baseline.py -> FROZEN_BINARY_CONFIG` |
| Parquet ZSTD + 1,048,576 row groups | | IMPL | `data.py -> WRITER_SETTINGS` |
| Checkpoint layout / hash chain | | IMPL | `causal_forest_runner.py` |
| Scale gating SMOKE -> RESOURCE -> FULL | 50K -> 2M -> 9,785,714 | RESOURCE | D30; `configs/t10_causal_forest.json -> scale_gating` |
| One CF full fit through T18 | 500K x 3 seeds for robustness | RESOURCE | D31 (locked) |
| Stage-4 refit exemption for CF | T11 seed-42 model frozen directly | RESOURCE | D31 |

**Do not defend D30/D31 as methodology.** They are pre-declared resource
constraints under deadline.

---

# 4. End-to-End Execution Flow

| # | File -> Symbol | Input | Operation | Output |
|---|---|---|---|---|
| 1 | `data.py -> load_selector` | `configs/data_manifest.json` | Validate 16 required fields; assert feature order, `treatment`, `conversion`, `visit` sole secondary, `exposure` sole post-assignment, `_source_row_id.model_feature is False`, sha256 formats, conversion settings | `ResolvedSelector` |
| 2 | `data.py -> open_processed_dataset` | selector (+ optional expected sha) | Reconcile selector vs supplied checksum; `verify_expected_file_checksum` **before** open; assert `PROCESSED_SCHEMA` | `pads.Dataset` |
| 3 | `data.py -> validate_processed_parquet` (generation-time) | parquet path | Row-group layout, ZSTD-only, per-batch `_source_row_id == arange`, `SemanticHasher` equality vs raw | `complete_unique_ordered: True` |
| 4 | `scripts/t11_run_stage.py -> _load_train_validation_ids` | `configs/t05_split.json` | Assert `T05_SPLIT_ACCEPTED`; read `split_membership.csv`; `membership_hash` must equal frozen `membership_sha256` | `SplitDataset` |
| 5 | `split.py -> SplitDataset.train_ids / validation_ids` | membership frame | Boolean select by label | `np.ndarray[int64]` |
| 6 | `causal_forest_runner.py -> StageRequest.__post_init__` | ids, sizes | `np.intersect1d` disjointness; bounds on `population_size`, `diagnostic_sample_size` | validated request |
| 7 | `causal_forest_runner.py -> stratified_subset_ids` | dataset, train ids | If `population_size == len(ids)` **skip entirely**; else load 3-col `[id,T,Y]` projection, `train_test_split(stratify=T_Y)` | sorted fit ids |
| 8 | `data.py -> materialize_pandas_by_source_row_id` | dataset, `[id,f0..f11,T,Y]`, ids | `Dataset.take(int64)`; reject dup/empty/undeclared/out-of-range; post-verify count **and** ascending order | `pd.DataFrame` (N x 15) |
| 9 | `causal_forest_baseline.py -> fit_causal_forest` | X frame, T, Y, config, seed | Divisibility check; reject 2-D multi-col T **before** reshape; `CausalForest(**cfg).fit(X,T,Y)` | `FittedCausalForest` |
| 10 | `data.py -> write_bytes_new_atomic` | pickle bytes | tmp -> flush -> fsync -> `os.replace` -> sha256 of the complete file | `(path, sha256)` |
| 11 | `causal_forest_runner.py -> _ensure_model_serialized` | 512-row head | `pickle.loads(disk)`, then `np.array_equal(tau_orig, tau_reload)` | bool, else raise |
| 12 | `causal_forest_baseline.py -> predict_tau` | VALIDATION X | Column-name identity check vs `feature_names`; `model.predict` | `tau` float64 1-D |
| 13 | `causal_forest_runner.py -> _ensure_predictions_persisted` | ids + tau | Arrow table, ZSTD parquet in memory, atomic write | `validation_tau.parquet` |
| 14 | `causal_forest_baseline.py -> aggregate_jacobian_support` | 100K diagnostic sample | `predict_alpha_and_jac`; finiteness = HARD; rank/cond = diagnostic | `AggregateSupportResult` |
| 15 | `data.py -> finalize_artifact_manifest` | run root | Hash every file, atomic write, refuse if manifest exists | `artifact_manifest.json` |
| 16 | `metrics.py -> evaluate_ranking` | scores, T, Y, ids | Sort DESC / id ASC; cumulative Qini; uplift@K; deciles | `RankingMetrics` |

`UNKNOWN`: the notebook-side persistence path for Response/T-Learner/X-Learner
predictions was inferred from section headers and symbol frequency, not read
cell-by-cell. The caller of step 16 for those estimators is notebook code.

---

# 5. Critical Modules

Only the two foundation modules are detailed here; the rest have their own
sections.

### `src/data.py` -- CRITICAL

| | |
|---|---|
| **Why** | Single source of truth for column contracts, dataset identity, partition reads, and governed artifact writes. Every other module imports it. |
| **In** | selector JSON; parquet path; column projection; id array |
| **Op** | validate contract -> verify checksum -> open Arrow dataset -> positional `take()` |
| **Out** | `ResolvedSelector`, `pads.Dataset`, `pd.DataFrame`, `(path, sha256)` |
| **Next** | `split.py`, `preprocessing.py`, `causal_forest_runner.py`, notebook |
| **Fails** | `DataContractError` on any contract violation; `FileExistsError` on overwrite; `_run_is_complete` makes finished runs immutable |
| **Proven by** | `tests/test_data.py` (23), incl. byte-for-byte equivalence of the positional loader vs the legacy `isin` pattern |
| **If req changes** | Adding a feature touches `FEATURE_COLUMNS`, `RAW_COLUMNS`, `EXPECTED_ARROW_TYPES`, both schemas, and forces full parquet regeneration + checksum re-pin + a new split |

**Row identity is the load-bearing idea.** `_augment_with_source_ids` assigns
`np.arange(offset, offset + n)` per batch; `validate_processed_parquet` proves
ordinal continuity (`source_row_id.complete_unique_ordered`). *That proof is
what licenses `Dataset.take()` to treat ids as row positions* -- a compact
int64 positional read instead of a whole-dataset `isin` scan.

### `src/split.py` -- CRITICAL

| | |
|---|---|
| **Why** | One-time frozen T05 partition + the structural held-out seal |
| **In** | full frame (`_source_row_id`, `T`, `Y`) |
| **Op** | two-stage `train_test_split`: train vs remainder, then validation vs held_out at `validation_fraction / (1 - train_fraction)`, both stratified on `T_Y` |
| **Out** | `(_source_row_id, split)` only -- **no feature/T/Y value is carried into the membership table** |
| **Next** | `SplitDataset.train_ids()` / `.validation_ids()` -> the partition loader |
| **Fails** | `SplitContractError` on row-count, disjointness, union, regeneration-hash, or unknown-label violations; `HeldOutAccessError` on any sealed access |
| **Proven by** | `tests/test_split.py` (17): disjointness, regeneration hash, id never renumbered, four held-out seal tests |
| **If req changes** | Changing fractions or seed regenerates membership, breaks `membership_sha256`, and invalidates every downstream model comparison |

`membership_hash` is order-independent (mergesort + int64/int8 byte digest).
`support_summary` refuses `"held_out"`; `held_out_support_gate` returns only
`PASS`/`FAIL` and logs no counts.

### Supporting modules (compact)

| Module | Role | Key facts | Tests |
|---|---|---|---|
| `src/lightgbm_baseline.py` | Causal-agnostic fitting primitive | `fit_binary_classifier`: params from train only, `best_iteration` from validation early stopping only (cap 2000, patience 50). `fit_regressor`: **fixed** `EFFECT_NUM_BOOST_ROUND = 100`, **no** early stopping, rejects a non-regression objective -- no valid external eval target exists for pseudo-outcomes | 15 |
| `src/preprocessing.py` | T04 identity transform | Select `f0..f11` in order at float64. `fit()` is a no-op (T03 shows zero missing values) but exists so the fit-on-train-only convention is enforced and testable. Missing values pass through unimputed | 11 |
| `src/audit.py` | T03 governance mechanics (1,421 lines) | Pre-split integrity, DP-01..DP-07 duplicates, conditional permutation, SMD/balance, MC order statistics. `split.py` imports exactly 2 symbols. `validate_no_permutation_p_value_language` actively rejects calling a calibration summary a p-value | 44 |
| `src/metrics_reference.py` | Loop-based reference metrics | Exists only to cross-check `metrics.py`. See §12 | via cross-check |

---

# 6. Model Portfolio

| | Random | Response | T-Learner | X-Learner | Causal Forest |
|---|---|---|---|---|---|
| **Training pop.** | none | TRAIN | TRAIN, split by arm | TRAIN, 2 folds | TRAIN (9,785,714 FULL; 500K robustness) |
| **Fit entry** | `seeded_random_scores` | `fit_binary_classifier` | same x2 | same x4 + `fit_regressor` x2 | `fit_causal_forest` |
| **Predict entry** | n/a | `predict_probabilities` | x2 -> `compute_tau` | `predict_values` x2 -> `combine_tau` | `predict_tau` |
| **Score** | uniform draw | P(Y=1 given X) | mu1 - mu0 | g*tau0 + (1-g)*tau1 | tau(x) from local moment |
| **Score MEANS** | no-skill reference | response propensity | est. CATE from two arm surfaces | est. CATE, variance-reduced via pseudo-outcomes | est. CATE, forest-weighted local moment |
| **Score does NOT mean** | anything causal | **any causal effect** | observed ITE | observed ITE | observed ITE; not a DML estimate |
| **Seeds** | master 42, 200 draws | 42 | 42 | fold 42; model 42 | model 42 (robustness 42/123/2026) |
| **Leakage boundary** | n/a | fit TRAIN, score VALIDATION | same | + opposite-fold OOF *within* TRAIN | same; held-out ids never requested |
| **Tests** | `test_metrics.py` | `test_lightgbm_baseline.py` (15) | `test_tlearner.py` (16) | `test_xlearner.py` (27) | `test_causal_forest_baseline.py` (20) + `_runner.py` (24) |
| **Known limits** | reference only | **not a causal estimator** | two independent surfaces can disagree in scale | constant `g`, not a real propensity | one-shot compute; `inference=False`, no internal CIs |

---

# 7. T-Learner

| | |
|---|---|
| **Why** | Simplest causal baseline: model each arm separately, difference the surfaces. `src/tlearner.py` holds *only* the combination/validation logic -- fitting is `lightgbm_baseline`, evaluation is `metrics` |
| **In** | TRAIN `(X, T, Y)`; then a common VALIDATION cohort |
| **Op** | partition by arm -> fit two classifiers -> score the *same* cohort with both -> subtract |
| **Out** | `tau_hat = mu1_hat - mu0_hat`, exact, unclipped |
| **Next** | `metrics.evaluate_ranking(tau_hat, T, Y, ids)` |
| **Fails** | `TLearnerContractError`: empty arm, non-binary T, length mismatch, id misalignment, non-finite mu, mu outside `[0,1]` |
| **Proven by** | `test_compute_tau_hand_computed_sign_orientation`, `test_assert_aligned_predictions_rejects_{mu1,mu0}_mismatch`, `test_partition_by_arm_rejects_missing_{treated,control}_arm` |
| **If req changes** | Swapping the base learner touches only `lightgbm_baseline`; `tlearner.py` is learner-agnostic |

```
TRAIN (X, T, Y)
   |
   +-- partition_by_arm(T, ...)
   |     T complete binary {0,1}; every array length == len(T)
   |     raises if EITHER arm is empty
   |
   +--> fit_binary_classifier(X_treated, Y_treated)  -> mu1 model
   +--> fit_binary_classifier(X_control, Y_control)  -> mu0 model
   |
   v  score the SAME full validation cohort with BOTH models
assert_aligned_predictions(ids_mu1, ids_mu0, ids_expected)
   np.array_equal on both -- either mismatch raises
   |
   v  compute_tau(mu1_hat, mu0_hat)
   shape equality; finite; both within [0,1] -> mu1_arr - mu0_arr
```

**Sign convention.** `tau = mu1 - mu0`; positive means treatment is predicted to
*increase* conversion. The docstring is explicit that sign orientation is a
testable *consequence* of the definition, not a separate runtime assertion.

**Reload reconciliation (the one subtle bit).** `reconcile_reloaded_tau` does
**not** use a flat `np.allclose` on tau. Tau can be near zero by cancellation of
two comparably sized mu values, so a relative tolerance on tau itself is
meaningless. The bound is derived per element from the *stored* mu magnitudes:

```
|tau_reload - tau_stored| <= 2*atol + rtol*(|mu1_stored| + |mu0_stored|)
```

`rtol=1e-6, atol=1e-8` per surface (docs/06), combined by the triangle
inequality. Test: `test_reconcile_reloaded_tau_near_zero_cancellation_case`.

---

# 8. X-Learner

| | |
|---|---|
| **Why** | Improves on T-Learner under arm imbalance by building pseudo-outcomes and modelling the *effect* directly. `src/xlearner.py` holds fold assignment, leakage assertions, pseudo-outcomes, and combination -- no fitting |
| **In** | TRAIN `(ids, X, T, Y)` |
| **Op** | 2-fold cross-fit -> OOF nuisances from the opposite fold -> D1/D0 -> two effect regressors -> weighted combine |
| **Out** | `tau_hat = g*tau0_hat + (1-g)*tau1_hat` on VALIDATION |
| **Next** | `metrics.evaluate_ranking` |
| **Fails** | `XLearnerContractError`: fold overlap, same-fold prediction, OOF gaps/duplicates, non-finite, mu outside `[0,1]`, missing arm, `g` outside `[0,1]`, shape mismatch |
| **Proven by** | `test_assert_opposite_fold_raises_on_same_fold_leakage`, `test_assert_full_oof_coverage_raises_on_{missing,duplicate}_row`, `test_compute_pseudo_outcomes_swapped_formula_gives_wrong_sign`, `test_combine_tau_g_{zero,one}_endpoint_equals_tau{1,0}` |
| **If req changes** | Moving to K>2 folds touches `assign_folds` only; the guards are fold-count agnostic. Making `g` covariate-varying requires a documented design assignment probability that does not currently exist |

```
TRAIN population (ids, T, Y)
   |
   v  assign_folds(ids, T, Y, seed=42)
   50/50 joint-(T,Y)-stratified train_test_split
   both folds sorted; disjointness asserted; union reconciled
   |
   +--> Fold A                              Fold B
   |    fit mu0_A, mu1_A (control/treated)  fit mu0_B, mu1_B
   |
   v  OOF ASSEMBLY -- every row gets BOTH mu0_oof and mu1_oof
   |  from the OPPOSITE fold, regardless of that row's own arm
   |
   +-- assert_opposite_fold(row_fold, pred_fold, name=...)
   |     raises if ANY row got a prediction from its own fold
   +-- assert_full_oof_coverage(expected_ids, oof_ids, name=...)
   |     raises on duplicates or set mismatch
   |
   v  compute_pseudo_outcomes(T, Y, mu0_oof, mu1_oof)
   |     validates finite; mu0/mu1 within [0,1]; both arms present
   |     D1 = Y - mu0_oof   on TREATED rows
   |     D0 = mu1_oof - Y   on CONTROL rows
   |
   +--> fit_regressor(X_treated, D1) -> tau1 model
   +--> fit_regressor(X_control, D0) -> tau0 model
   |
   v  score VALIDATION with both -> tau1_hat, tau0_hat
   |  g = empirical_treatment_rate(TRAIN T)     [a scalar constant]
   v  combine_tau = g*tau0_hat + (1-g)*tau1_hat
```

### Exactly where leakage would occur without the OOF logic

At the **OOF assembly** step. If a row received `mu0_oof`/`mu1_oof` from the
model fit on **its own** fold, that nuisance prediction has already seen that
row's outcome. Then `D1 = Y - mu0_oof` and `D0 = mu1_oof - Y` absorb *in-sample
fit error* instead of genuine counterfactual residual. The effect regressors
learn to reproduce nuisance overfitting; tau looks better on any in-sample
check and generalizes worse. **Nothing downstream can detect this** -- not
`combine_tau`, not `evaluate_ranking`. The only defenses are
`assert_opposite_fold` and `assert_full_oof_coverage`.

Both are **opt-in caller responsibilities**, not enforced inside
`compute_pseudo_outcomes`. See §16.

### `g(x)` -- be able to defend this

`empirical_treatment_rate` returns `float(np.mean(treatment == 1))` over TRAIN
only: a **fixed constant**, not a covariate-varying estimated propensity. The
docstring gives the reason -- no documented design assignment probability
exists in `docs/01_causal_contract.md` or `docs/02_data_contract.md` as of T09.
`combine_tau` accepts an array `g` for a future rule, but the primary rule is
the constant. Endpoints are tested: `g=0` reduces to `tau1`, `g=1` to `tau0`.

**Sign convention.** Both D1 and D0 are oriented so positive = treatment
helped.

---

# 9. Causal Forest

| | |
|---|---|
| **Why** | Accepted main comparator; estimates CATE directly rather than differencing two response surfaces |
| **In** | X frame (`f0..f11`), T (own argument), Y, config, seed |
| **Op** | `econml.grf.CausalForest(**frozen_config).fit(X_arr, T_arr, Y_arr)` |
| **Out** | `FittedCausalForest(model, config_hash, feature_names)` |
| **Next** | `predict_tau` -> `aggregate_jacobian_support` -> runner serialization |
| **Fails** | `ValueError` on `n_estimators % subforest_size != 0`, on multi-column T, on predict-frame column mismatch |
| **Proven by** | 4 synthetic-effect gates (positive/negative/zero/heterogeneous), `test_fit_rejects_multi_column_treatment`, `test_feature_names_never_include_treatment`, `test_deterministic_refit_same_seed_same_data`, `test_reload_via_pickle_matches_original_exactly` |
| **If req changes** | `n_jobs > 1` is blocked on correctness (see below); a new seed is cheap but D31 forbids selecting a favorable one |

**The selected estimator is `econml.grf.CausalForest` -- not a DML causal
forest.** It solves the local moment equation

```
E[ (Y - <theta(x), T> - beta(x)) * (T; 1) | X = x ] = 0
```

directly at every point x. `theta(x)` (treatment effect) and `beta(x)` (local
intercept) are estimated **jointly and locally** via forest-weighted
neighborhoods. **No nuisance residualization, no upfront cross-fitting stage.**
Never call this DML in a review.

### Frozen config

| Param | Value | Controls | Why this value | Statistical effect | Computational effect |
|---|---|---|---|---|---|
| `n_estimators` | 100 | trees | econml default; must divide by `subforest_size` | more trees -> lower forest-estimate variance | linear in fit time + model size |
| `criterion` | `"mse"` | split rule | package default; the standard local-moment split from the reference GRF algorithm (verified from source docstring, not assumed). `"het"` is a distinct non-default variant, unused | different neighborhoods | comparable |
| `honest` | `True` | sample splitting inside each tree | **mandatory per ADR-CF-implementation, never False** | removes bias from using the same rows to choose splits *and* estimate leaf values | halves effective rows per leaf estimate |
| `inference` | `False` | Bootstrap-of-Little-Bags | project uncertainty is the 500-draw paired bootstrap (T15), applied post hoc; BLB has no consumer | no per-row analytic CIs | **saves significant time/memory** -- disabled deliberately, not by inertia |
| `min_samples_leaf` | 5 | absolute leaf floor | package default | smaller leaves -> more heterogeneity, more variance | deeper trees, bigger model |
| `max_samples` | **0.45** | subsample fraction per tree | package default | subsampling decorrelates trees, which is what makes the forest average a variance-reducing estimator rather than 100 copies of one tree | **~45% of rows per tree** -- a direct linear lever on fit time and memory |
| `min_balancedness_tol` | 0.45 | **split-size** imbalance between the two children | package default | prevents degenerate splits | minor |
| `subforest_size` | 4 | trees per subforest group | package default; `n_estimators % subforest_size == 0` is a library requirement | grouping used by BLB when inference is on | constrains valid `n_estimators` |
| `max_depth` | `None` | depth cap | package default | unconstrained depth + absolute leaf floor makes single-arm leaves ordinary | larger trees |
| `n_jobs` | **1** | parallelism | **NOT the package default (-1).** Verified empirically in T10 IMPLEMENT: at an identical `random_state`, `n_jobs=2` and `n_jobs=-1` each produced **different predictions** than `n_jobs=1` | none -- this is reproducibility | **single-threaded fit**; the dominant cost driver at 9.79M rows |
| `random_state` | 42 per call | seed | set inside `fit_causal_forest` from `seed` | determinism | none |

**`min_balancedness_tol` trap.** It bounds split-size imbalance between the two
children of a split. It is **NOT** a treatment/control arm-balance mechanism.

### X/T/Y handling

- `feature_names` captured from `X.columns` before conversion; `predict_tau`
  rejects a frame whose columns differ -- guards silent column reordering.
- **T is always its own argument, never concatenated into X.**
- T shape is validated on the **raw** array *before* `reshape(-1, 1)`, because
  reshape always succeeds and would silently flatten a multi-column T into a
  longer single column.

---

# 10. Causal Forest Jacobian / Support Logic

The most likely place to be challenged.

### HARD CORRECTNESS (gates the model)

```
passed = alpha_all_finite AND jac_all_finite AND tau_all_finite
```

That is the entire hard gate. Nothing else.

### DIAGNOSTIC ONLY (never gates)

`jac_full_rank_fraction`, `all_full_rank`, and the condition-number
distribution (min/p50/p95/p99/max).

**Why rank deficiency is not failure:** EconML predicts through the
**Moore-Penrose pseudo-inverse**, defined for rank-deficient matrices. Pinned by
`test_aggregate_jacobian_rank_deficiency_is_diagnostic_only` and
`test_aggregate_jacobian_support_no_invented_condition_number_cutoff`.

### Per-leaf arm support -- also diagnostic only

Identification is a **forest-aggregate** property: `predict_alpha_and_jac()`
averages each tree's local moment contribution across all trees, then solves
**one** pseudo-inverse at the aggregate level. A single tree's leaf lacking one
arm is ordinary under class imbalance with unconstrained `max_depth` and an
absolute `min_samples_leaf` floor.

**The index-mapping trap.** `tree.get_train_test_split_inds()` returns indices
**local to that tree's own subsample**, not global row indices:

```
subsample              = forest.get_subsample_inds()[i]
split_local, est_local = tree.get_train_test_split_inds()
est_global             = subsample[est_local]      # <-- must map back
```

Leaf support uses `est_global` only -- the split sample determines structure and
never contributes to a leaf's estimated value. The function also raises if split
and estimation samples are not disjoint (honesty violation). Tests:
`test_honest_leaf_arm_support_uses_global_not_local_indices`,
`test_honest_leaf_arm_support_detects_non_disjoint_split`.

> **History to know.** `configs/t10_causal_forest.json` contains a
> `support_gate_correction` block and the SMOKE size was revised 200,000 ->
> 50,000 after it. An earlier run (`t10_smoke_20260819T074012Z_483118`) failed
> under the *old* per-leaf gate and is retained but explicitly non-authoritative.
> If asked "was there ever a bug here?" -- yes: the support gate was initially
> specified per-leaf and was corrected to aggregate.

---

# 11. T11 Runner / Resume / Artifacts

| | |
|---|---|
| **Why** | Exactly one full-scale CF fit is authorized (D31), so it must be crash-resumable and produce tamper-evident evidence. Every other estimator fits inline in a notebook cell |
| **In** | `StageRequest(stage, run_id, run_root, dataset, dataset_sha256, train_ids, validation_ids, population_size, sampling_seed, model_seed, diagnostic_sample_size, config)` |
| **Op** | the DAG below, resuming at the highest valid checkpoint |
| **Out** | `models/causal_forest.pkl`, `predictions/validation_tau.parquet`, 4 checkpoints, `run_config.json`, `resource_evidence.json`, `diagnostic_support_summary.json`, `artifact_manifest.json` |
| **Next** | the notebook loads and narrates that evidence; it never refits |
| **Fails** | `CausalForestRunnerError` on resume-identity mismatch, hash-chain mismatch, or reload divergence; `DataContractError` on immutable-run writes |
| **Proven by** | `test_resume_after_crash_before_predictions_does_not_refit`, `test_resume_rejects_parameter_mismatch_against_checkpoint_one`, `test_fit_cohort_identity_is_persisted_and_common_across_model_seeds`, `test_full_stage_run_config_written_once_and_never_mutated`, `test_two_fresh_runs_with_identical_inputs_produce_identical_predictions` |
| **If req changes** | Fixing the memory spike (§16) is implementation-only. Adding a stage means extending `STAGES` + a config block, not a new script |

Stages: `smoke` | `robustness` | `gcp_parity` | `full`. CLI
`scripts/t11_run_stage.py` refuses without
`--i-understand-this-executes-real-data-model-training` (exit 2).

```
StageRequest.__post_init__
  stage in STAGES; 0 < population_size <= len(train_ids)
  validation_ids non-empty; 0 < diagnostic_sample_size <= len(validation_ids)
  np.intersect1d(train_ids, validation_ids).size == 0     <-- disjointness
        |
_ResourceSampler() STARTS here (covers everything below)
        |
stratified_subset_ids -> fit_train_ids
  population_size == len(ids) ? return sorted ids, NO materialization
  else 3-col [id,T,Y] projection -> train_test_split(stratify) -> sorted subset
        |
_read_checkpoint_chain   verifies prior_checkpoint_sha256 links
        |
   chain empty?  --yes--> write run_config.json (once) + checkpoint 001
        |  no
        +--> _verify_resume_identity(...)   <-- fail closed, 10 fields
        |
_ensure_model_serialized
  chain >= 2 ? pickle.loads(model_path) and SKIP refit
  else: materialize TRAIN [id, f0..f11, T, Y]
        fit_causal_forest                       (timed; peak RSS windowed)
        pickle.dumps -> write_bytes_new_atomic  -> sha256
        reload check: 512-row head, np.array_equal(tau_orig, tau_reload)
        del train_frame                         <-- AFTER the reload check
        checkpoint 002
        |
_ensure_predictions_persisted
  chain >= 3 ? return path
  else: materialize VALIDATION [id, f0..f11]
        predict_tau -> Arrow -> ZSTD parquet in BytesIO -> atomic write
        checkpoint 003; del validation_frame
        |
_ensure_finalized
  chain >= 4 ? return existing summary
  else: rng.choice(validation_ids, diagnostic_sample_size, replace=False)
        materialize sample -> aggregate_jacobian_support
        write diagnostic_support_summary.json -> _write_resource_evidence
        checkpoint 004 -> finalize_artifact_manifest(COMPLETED_PASS|FAIL)
```

### Cohort identity -- the 10 fail-closed resume fields

`_verify_resume_identity` compares checkpoint 001 to the current request and
raises listing **every** mismatched field:

`stage` · `run_id` · `population_size` · `sampling_seed` · `model_seed` ·
`dataset_sha256` · `config_hash` · `train_ids_identity` ·
**`fit_train_ids_identity`** · `validation_ids_identity`

`_ids_identity` = `{count, sha256}` over sorted, newline-joined decimal ids.
**Raw ids are never written to JSON.** Order-independent by construction.

**Why `fit_train_ids_identity` is separate from `train_ids_identity`:** the
three robustness legs share one 500K cohort across three model seeds, so the
runner must prove the *cohort* was identical while the *seed* differed.

Separately, the **hash chain** fails closed: each checkpoint stores
`prior_checkpoint_sha256`, and `_read_checkpoint_chain` raises if a recorded
hash does not match the actual preceding file.

### Immutability

`run_config.json` is written **once** before fit and never touched again. All
output hashes live only in checkpoints and the final manifest. `_run_is_complete`
makes any run with a `COMPLETED*`/`FAILED*` manifest permanently immutable.
`write_active_sentinel` records the active run_id atomically **outside** the run
root so a restart can find what to resume without reading governed outputs.

---

# 12. Metrics

| | |
|---|---|
| **Why** | Decide which ranking is better, on VALIDATION only, under a frozen convention |
| **In** | `scores`, `treatment`, `outcome`, `source_row_id` (equal length) |
| **Op** | sort DESC / id ASC -> cumulative counts and conversions -> Qini gain -> trapezoid area -> subtract the theoretical random area |
| **Out** | `RankingMetrics(n, qini_area, theoretical_random_qini_area, qini_above_random, uplift_at_k, incremental_conversions_at_k, top_k_status, decile_table, qini_curve)` |
| **Next** | notebook comparison tables; `validation_selection.csv` |
| **Fails** | `MetricContractError`: length mismatch, empty population, non-finite scores, duplicate/missing ids, non-binary T or Y, missing arm, `N < 10` for deciles, no valid Qini prefix |
| **Proven by** | `test_reference_and_production_agree_exactly`, `test_sort_direction_regression`, `test_constant_score_ties_resolve_by_source_row_id_ascending`, `test_order_invariance_under_input_row_shuffling`, `test_zero_cumulative_control_prefixes_are_skipped_not_zeroed` |
| **If req changes** | A new K in the grid touches `RANKING_K_GRID`/`RANKING_K_LABELS` in `metrics_common.py` and **both** implementations, which is the point |

**Dual implementation.** `src/metrics.py` (vectorized, production) and
`src/metrics_reference.py` (loop-based, hand-verifiable) implement the causal
ranking arithmetic **twice, independently**. They share only
`src/metrics_common.py`: constants, dataclasses, the exception type, and
`select_curve_points` (pure index bookkeeping, which cannot hide a formula bug).
This is the one place a silently reversed ranking could hide.

### Ranking direction and tie-breaking

```
sort by score DESCENDING, tie-break _source_row_id ASCENDING
```

Both are load-bearing. Descending because higher predicted uplift should be
targeted first. The id tie-break makes the ranking **deterministic and
reproducible** when scores collide (common with tree models producing identical
leaf values) -- without it, Qini would depend on input row order.

### Qini

```
cum_n1, cum_n0 = cumulative treated / control counts down the ranking
cum_y1, cum_y0 = cumulative treated / control conversions

qini_gain(r) = cum_y1(r) - cum_y0(r) * cum_n1(r) / cum_n0(r)
```

Prefixes where `cum_n0 == 0` are **skipped, not zeroed**. If no valid prefix
exists at all it raises rather than fabricating a zero.

```
qini_area                    = trapezoid over the selected curve points
theoretical_random_qini_area = Q_full / 2
qini_above_random            = qini_area - Q_full / 2        <-- PRIMARY
```

The expected-random line is `Q_random(c) = c * Q_full`, so its area is exactly
half of `Q_full`. The 200-draw seeded random-ranking distribution is **secondary
empirical context**; the theoretical line stays primary.

### uplift@K

Grid `(0.10, 0.20, 0.30, 0.50, 1.00)`, `m_k = min(n, max(1, ceil(k*n)))`,
`uplift@K = y1_k/n1_k - y0_k/n0_k`, `incremental@K = m_k * uplift@K`.
If either arm is empty in the prefix, the numeric value is `None` (NA) and
`top_k_status = "UNSUPPORTED_METRIC"` -- a **separate reason field** that never
overloads the numeric type. Scores are never clipped.

### Why AUC / AP / log loss are diagnostic only

They score a **response** surface: how well `P(Y=1|X)` is predicted. Uplift
ranking asks how the treated and control response surfaces *differ*. A model can
predict conversion nearly perfectly and rank uplift no better than random,
because the people most likely to convert often convert **regardless of
treatment** ("sure things"). Ranking by response targets them; ranking by uplift
targets the "persuadables". D27 locks these to diagnostic status.
`test_treatment_coding_swap_is_not_a_simple_sign_flip` demonstrates that uplift
arithmetic is not a trivial transform of response arithmetic.

### How row alignment is protected

`_validate_ranking_inputs` requires equal lengths, rejects missing
`_source_row_id` **before** the int64 cast, rejects duplicate ids within the
evaluation population, requires both arms present, and rejects non-finite
scores. `_source_row_id` also participates in the tie-break.

---

# 13. Resource / Memory Behavior

`_ResourceSampler`: daemon thread, 0.5 s interval, started before the TRAIN load
and stopped in `__exit__` so it always stops, even on exception. If `psutil` is
missing the thread returns immediately and fields are omitted -- it never blocks
a run.

| Field | Meaning |
|---|---|
| `peak_rss_bytes` | **true max of continuous samples**, explicitly not a snapshot max (`peak_rss_bytes_method` says so in the payload) |
| `peak_rss_during_fit_bytes` | windowed via `peak_rss_bytes_between(fit_start, fit_end)` |
| `rss_stage_snapshots` | sparse per-checkpoint snapshots, **never** relabeled a peak |
| `system_memory_available_bytes_min` / `system_memory_percent_max` | host pressure |
| `swap_used_bytes_max` | thrash signal |

Process RSS and host memory are kept in separate fields by explicit design
discipline.

### Memory lifetimes

| Phase | Resident |
|---|---|
| TRAIN load | `train_frame` (N x 15) |
| Fit | `train_frame` + growing forest |
| Serialize | `train_frame` + `fitted` + **`model_bytes` (full pickle in RAM)** |
| Reload check | + **`reloaded` (a second full model)** |
| After `del train_frame` | `fitted` only |
| VALIDATION | `fitted` + `validation_frame` (N x 13) |

**TRAIN and VALIDATION never coexist** -- the headline memory design, stated in
the module docstring and true in code. But the serialize/reload window is a
genuine 4-way peak; see §16.

### Scale context

SMOKE 50,000 -> exactly one RESOURCE gate at 2,000,000 -> FULL 9,785,714. The
RESOURCE run (`t10_resource_20260819T093301Z_574711`) executed and is retained.
D31 records it is **not** reused as the seed-42 robustness point, because no
model was serialized and no validation predictions exist for fair comparison
with seeds 123/2026. `full_disk_requirement` is explicitly **not frozen** --
deferred to real `_write_resource_evidence` measurements during the 500K runs.

---

# 14. Testing Map

10 test files, roughly 220 tests. Highest-signal rows only.

| Source behavior | Test | Contract protected |
|---|---|---|
| Positional loader == legacy `isin` | `test_materialize_by_source_row_id_matches_legacy_isin_filter_exactly` (+ `..._full_population_...`) | The refactor changed no row/column/dtype/order |
| Loader fails closed | `..._rejects_{duplicate_ids, missing_source_row_id_in_columns, undeclared_columns, out_of_range_ids, empty_request}` | Never silently drop or dedupe |
| Checksum pinning | `test_processed_consumer_accepts_pinned_identity_and_rejects_same_schema_stale_file` | Right schema is not right data |
| Atomic write | `test_write_bytes_new_atomic_leaves_no_partial_or_temp_file` | A hash taken after write reflects a complete file |
| Run immutability | `test_completed_run_rejects_late_{json,csv,png}` | Finished runs are frozen |
| Split integrity | `test_split_is_disjoint_and_complete` (+ overlap / incomplete-union) | Full row accounting |
| Split determinism | `test_deterministic_regeneration_reproduces_identical_hash` | Reproducible from scratch |
| **Held-out seal** | `test_held_out_ids_fail_closed_without_release_marker`, `..._with_wrong_status`, `..._succeed_with_valid_release_marker`, `test_support_summary_rejects_held_out` | The seal is structural |
| Id stability | `test_source_row_id_is_never_renumbered` | Alignment across the pipeline |
| **Metric dual-impl** | `test_reference_and_production_agree_exactly` | No formula bug can hide |
| Metric orientation | `test_good_ranking_scores_above_random`, `test_reversed_ranking_scores_below_random`, `test_sort_direction_regression` | Sign / direction |
| Tie determinism | `test_constant_score_ties_resolve_by_source_row_id_ascending`, `test_order_invariance_under_input_row_shuffling` | Reproducible ranking |
| Uplift is not response | `test_treatment_coding_swap_is_not_a_simple_sign_flip` | Causal vs predictive |
| T-Learner sign | `test_compute_tau_hand_computed_sign_orientation` | `tau = mu1 - mu0` |
| T-Learner reload | `test_reconcile_reloaded_tau_near_zero_cancellation_case` | Derived tolerance, not flat allclose |
| **X-Learner leakage** | `test_assert_opposite_fold_raises_on_same_fold_leakage` | The core OOF guard |
| X-Learner coverage | `test_assert_full_oof_coverage_raises_on_{missing,duplicate}_row` | Every row exactly once |
| X-Learner sign | `test_compute_pseudo_outcomes_swapped_formula_gives_wrong_sign` | D1/D0 orientation |
| CF X/T separation | `test_fit_rejects_multi_column_treatment`, `test_feature_names_never_include_treatment` | T never enters X |
| CF synthetic gates | `test_synthetic_gate_{positive,negative,zero,heterogeneous}_effect` | Recovers known truth (ADR gate 2) |
| CF honesty | `test_honest_leaf_arm_support_{detects_non_disjoint_split, uses_global_not_local_indices}` | Honesty + index mapping |
| **CF hard vs diagnostic** | `test_aggregate_jacobian_rank_deficiency_is_diagnostic_only`, `..._no_invented_condition_number_cutoff` | Rank is not a gate |
| CF determinism | `test_deterministic_refit_same_seed_same_data`, `test_reload_via_pickle_matches_original_exactly` | Reproducibility |
| **Runner resume** | `test_resume_after_crash_before_predictions_does_not_refit`, `test_resume_rejects_parameter_mismatch_against_checkpoint_one` | Crash safety + identity |
| Runner cohort identity | `test_fit_cohort_identity_is_persisted_and_common_across_model_seeds` | Seed-robustness fairness |
| No wasted work | `test_stratified_subset_skips_materialization_when_full_population` | FULL builds no subset |

### Weakly tested or untested

1. **The notebook.** ~330 KB across 280 cells, no automated coverage. All
   `RUN_*_STAGE` flags are currently `False`.
2. **`n_jobs` override.** No test asserts a caller-supplied config still has
   `n_jobs == 1`, despite it being a stated correctness requirement.
3. **OOF guards are not enforced structurally.** Tests prove the guards *work*;
   nothing proves a caller *invoked* them.
4. **Real-data execution.** Runner tests use synthetic fixtures. No real-data
   T11 run has occurred (`lifecycle_state: T11_INFRASTRUCTURE_IMPLEMENTED`).

---

# 15. Important Design Decisions

| Decision | Rationale as recorded in code/docs |
|---|---|
| Dual metric implementation | The one place a silently reversed ranking could hide. Two independent implementations, cross-checked exactly. |
| Positional `Dataset.take()` over `isin` | `_source_row_id` is provably the parquet row ordinal, so ids *are* row positions. Rejected alternative recorded in `configs/t11_causal_forest_full.json`: `sorted(set(all_ids))` + whole-dataset `isin`, rejected for duplicating millions of ids at Python level. |
| Append-only hash-chained checkpoints | One mutated `checkpoint.json` cannot prove it was not tampered with or half-written. A chain can. |
| `write_bytes_new_atomic` for large artifacts | `write_bytes_new` opens the destination directly, so a crash leaves a truncated file at the real path. |
| Runner in `src/`, not the notebook | Exactly one full-scale CF fit is authorized, so it must be crash-resumable. Stated verbatim in notebook cell 277. |
| `n_jobs=1` | Empirically verified determinism requirement. |
| `inference=False` | Uncertainty comes from a post-hoc bootstrap; BLB has no consumer. |
| Constant `g(x)` | No documented design assignment probability exists. An estimated propensity would invent structure the RCT design does not license. |
| Fixed 100 rounds for the effect stage | D0/D1 are undefined on validation rows, so no valid early-stopping target exists without inventing a split. |
| Held-out seal is a missing file, not a flag | A flag can be flipped by accident; a nonexistent release manifest cannot. |
| D31 one-shot compute | Pre-declared resource constraint under deadline. **Not** performance-informed. |

---

# 16. Known Weaknesses / Stale Code, Config, Docs

### REAL ISSUE -- X-Learner OOF guards are opt-in

`assert_opposite_fold` and `assert_full_oof_coverage` are separate calls the
caller must remember. `compute_pseudo_outcomes` validates finiteness and bounds
but **cannot tell** whether the OOF nuisances actually came from the opposite
fold. A stronger design threads fold labels into `compute_pseudo_outcomes` and
asserts internally.

### REAL ISSUE -- no runtime assertion that `n_jobs == 1`

`fit_causal_forest` accepts a caller-supplied `config`, and
`StageRequest.config` / `--config-json` can override the frozen dict. Since
`n_jobs != 1` provably changes predictions at a fixed seed, a determinism
regression could enter with no guard and no test. The `config_hash` *would*
change, so it is auditable after the fact -- but not prevented.

### REAL ISSUE (resource) -- serialization 4-way residency

In `_ensure_model_serialized`, `fitted` + `model_bytes` (the entire pickle as a
bytes object) + `reloaded` + the still-live `train_frame` are resident
simultaneously, because the 512-row reload sample is taken from `train_frame`
before it is deleted. At 9.79M rows x 100 trees this is the most likely OOM
point in the pipeline. Fixable without changing semantics (copy the 512 rows
out, `del train_frame` earlier, `del model_bytes` after the atomic write).
**Flagged, not fixed.**

### STALE

| Finding | Class |
|---|---|
| `configs/t11_causal_forest_full.json` names `src.causal_forest_runner._stratified_train_subset_ids`; **the real symbol is `stratified_subset_ids`** (public, generalized to also accept a validation id array). Verified: zero occurrences of the old name anywhere in `src/` or `scripts/`. Config text is stale; code is right | STALE DOCUMENTATION |
| Issue #7 top-K wording superseded by `docs/07` (numeric stays NA + separate `top_k_status`). Already self-documented in `metrics_common.py`; reconciliation deferred pending GitHub write access | STALE (self-aware) |
| `docs/00_project_overview.md` calls Causal Forest "planned for Sprint 2, provisional" while `configs/t10_causal_forest.json` is `T10_ACCEPTED` with a frozen config | STALE (expected Sprint-1 drift) |
| `configs/t07/t08/t09` read `*_SMOKE_IN_PROGRESS` while the notebook contains completed FULL sections with three-seed tables. README points to GitHub Issue #20 as the live source of truth | STALE / `UNKNOWN` -- verify against Issue #20 before quoting status |
| T10 support gate was initially per-leaf, corrected to aggregate; the failed 200K SMOKE run is retained but non-authoritative | RESOLVED HISTORY |

### ACCEPTABLE TRADE-OFFS

Dual metric implementation (deliberate, tested); `src/audit.py` breadth
(1,421 lines of T03 governance, 2 symbols used downstream); notebook
whole-population `materialize_pandas` for historical recomputation (correct for
narration -- the positional loader is the runner's path, with **zero** notebook
occurrences).

**Not AI sprawl.** Several comments encode *empirical* findings no model would
invent -- the `n_jobs` determinism test, the support-gate correction, the
derived tau reload tolerance.

---

# 17. Debugging Map

Each exception class maps to exactly one layer, because every module subclasses
`DataContractError`.

| Exception | Layer | First check |
|---|---|---|
| `DataContractError` from `load_selector` | selector | `configs/data_manifest.json` exists and matches the frozen contract |
| `DataContractError: Artifact checksum mismatch` | dataset identity | parquet regenerated; re-pin `processed_sha256` |
| `DataContractError` from `take()` / count / order mismatch | partition loader | id set has duplicates, gaps, or out-of-range values |
| `DataContractError: Completed run is immutable` | artifact writer | writing into a run that already has a final manifest |
| `SplitContractError: membership hash mismatch` | split | `split_membership.csv` differs from `configs/t05_split.json` |
| `HeldOutAccessError` | seal | **stop and investigate, do not work around** |
| `PreprocessingContractError` | preprocessing | missing `f*` column, or `transform()` before `fit()` |
| `MetricContractError: Mismatched input lengths` / `not unique` | scoring | scores/T/Y/ids misaligned, or duplicated rows |
| `MetricContractError: Both treatment arms must be present` | scoring | cohort or top-K slice lost an arm |
| `TLearnerContractError: not row-identity-aligned` | T-Learner | mu1/mu0 scored different cohorts or orders |
| `TLearnerContractError: values outside [0,1]` | T-Learner | a regressor used where a classifier belongs |
| `XLearnerContractError: ...prediction from their own fold` | X-Learner | **leakage** -- OOF assembly is wrong |
| `ValueError: n_estimators must be divisible by subforest_size` | CF config | an override broke the econml requirement |
| `ValueError: Prediction frame columns do not match` | CF predict | column order drifted between fit and predict |
| `CausalForestRunnerError: Resume identity mismatch [fields]` | runner | the listed fields differ from checkpoint 001 |
| `CausalForestRunnerError: hash-chain mismatch` | runner | checkpoint files edited or partially written |
| `CausalForestRunnerError: reload check failed` | runner | serialization is not faithful -- **do not proceed** |
| `MemoryError` during serialize | resource | the 4-way residency window (§16) |

---

# 18. If Requirements Change

| Requirement | Files | Tests that fail first | Governance |
|---|---|---|---|
| **Add a 13th feature to X** | `data.py` (`FEATURE_COLUMNS`, `RAW_COLUMNS`, `EXPECTED_ARROW_TYPES`, schemas), regenerate parquet, re-pin checksums, update selector | `test_data.py` schema tests, `test_forbidden_or_undeclared_feature_input_is_rejected`, `test_preprocessing.py` order tests | Frozen contract. Owner approval + decision-register entry; invalidates every model and the split hash |
| **Switch primary Y to `visit`** | `PRIMARY_OUTCOME`; the split stratifies on `(T, conversion)` so **the entire T05 split changes** | `test_split.py` stratification + hash, every metric fixture | Frozen. `visit` is contractually a *separate pipeline* |
| **Change split to 80/10/10** | `split.py` fractions; regenerate membership; re-pin hash | `test_split_preserves_row_count_and_approximate_proportions`, `test_deterministic_regeneration_...` | Frozen. Invalidates all prior evidence and comparability |
| **Allow `n_jobs > 1`** | `FROZEN_CAUSAL_FOREST_CONFIG` | none currently (a gap) -- but `config_hash` changes, so every resume fails identity | **Blocked on correctness.** Determinism was empirically shown to break |
| **Add a 4th CF model seed** | `configs/t11_causal_forest_full.json` `model_seeds` + one runner invocation | none | D31 permits reporting more seeds but **forbids selecting a favorable one**; must reuse the identical 500K cohort |
| **Add a new estimator (DR-Learner)** | new `src/drlearner.py` glue + reuse `lightgbm_baseline`; notebook section; new config | new tests required | ADR + methodology scope; DR-Learner is a *conditional stretch* comparator |
| **Make X-Learner guards structural** | `xlearner.py`: thread fold labels into `compute_pseudo_outcomes` | existing guard tests still pass | Implementation only -- the safest change here |
| **Fix the serialization spike** | `causal_forest_runner.py`: copy the 512-row sample, `del` earlier | `test_resource_evidence_schema_is_stable_across_independent_runs` should still pass | Implementation only; needs re-measured resource evidence |
| **Score held-out** | no code change -- create the T17 release manifest with `status: HELDOUT_RELEASED` | `test_held_out_ids_fail_closed_without_release_marker` documents the mechanism | **One time only**, after a recorded pre-test freeze. Irreversible |

---

# 19. What I Must Know Before Mentor Review

Never bluff on these:

1. **Predicted `tau` is not an observed individual treatment effect.** Both
   potential outcomes are never observed for the same row -- which is exactly
   why PEHE on real data is prohibited (D28).
2. **The Response model is not a causal estimator.** Good AUC does not imply
   good Qini: "sure things" convert regardless of treatment.
3. **The estimand is assignment/ITT CATE**, so `exposure` (post-assignment) can
   never enter X, eligibility, or the population filter.
4. **`econml.grf.CausalForest` solves a local moment equation directly** -- no
   nuisance residualization, no upfront cross-fitting. Not DML.
5. **Honesty** = split-determining rows and leaf-estimating rows are disjoint
   within each tree.
6. **Jacobian rank deficiency is diagnostic, not failure**, because EconML
   predicts through the Moore-Penrose pseudo-inverse. Only alpha/jac/tau
   finiteness is a hard gate.
7. **Identification is a forest-aggregate property**; a single leaf missing one
   arm is ordinary under class imbalance.
8. **X-Learner leakage lives in the OOF assembly step** -- same-fold nuisances
   make D1/D0 absorb in-sample error. `assert_opposite_fold` is the guard.
9. **`g` is a constant training-set treatment rate**, not an estimated
   propensity, because no design assignment probability is documented.
10. **`_source_row_id` is the parquet row ordinal**, proven by
    `validate_processed_parquet` -- which is what makes positional
    `Dataset.take()` legitimate. Never a feature, never a person id.
11. **Qini above random subtracts `Q_full / 2`**, the area under
    `Q_random(c) = c * Q_full`.
12. **D31 one-shot compute is a resource decision, not a statistical one**, and
    the only governed reason to retrain is a demonstrated defect -- never
    disappointing performance.

Also say plainly when asked: **no real-data T11 run has executed yet**, and the
honest weakness is the serialization memory spike (§16).

---

# 20. Source Reading Order (after this document)

1. `src/data.py` -- contracts + `materialize_pandas_by_source_row_id`
2. `src/split.py` -- `assign_split`, `membership_hash`, `held_out_ids`
3. `src/preprocessing.py` -- short; the fit-on-train-only pattern
4. `src/metrics.py` + `metrics_common.py`
5. `src/tlearner.py`
6. `src/xlearner.py` -- read right after T-Learner so the opposite-fold
   requirement stands out by contrast
7. `src/causal_forest_baseline.py`
8. `src/causal_forest_runner.py`
9. `scripts/t11_run_stage.py`
10. `kaggle/02_uplift_modeling.ipynb` -- skim headers T07 -> T11

---

# Appendix A -- Codebase Scan Coverage

72 tracked files, all accounted for.

| Path | Type | Importance | Scan status |
|---|---|---|---|
| `src/data.py` | SOURCE | CRITICAL | READ_FULL |
| `src/split.py` | SOURCE | CRITICAL | READ_FULL |
| `src/metrics.py` | SOURCE | CRITICAL | READ_FULL |
| `src/metrics_common.py` | SOURCE | CRITICAL | READ_FULL |
| `src/tlearner.py` | SOURCE | CRITICAL | READ_FULL |
| `src/xlearner.py` | SOURCE | CRITICAL | READ_FULL |
| `src/causal_forest_baseline.py` | SOURCE | CRITICAL | READ_FULL |
| `src/causal_forest_runner.py` | SOURCE | CRITICAL | READ_FULL |
| `src/lightgbm_baseline.py` | SOURCE | HIGH | READ_FULL |
| `src/preprocessing.py` | SOURCE | HIGH | READ_FULL |
| `src/audit.py` | SOURCE | MEDIUM | READ_FULL |
| `src/metrics_reference.py` | SOURCE | HIGH | READ_RELEVANT (docstring, symbols, validation head) |
| `src/__init__.py` | SOURCE | LOW | SKIPPED_WITH_REASON (package marker) |
| `scripts/t11_run_stage.py` | SCRIPT | CRITICAL | READ_FULL |
| `scripts/verify_t06_metrics.py` | SCRIPT | MEDIUM | READ_RELEVANT |
| `tests/test_data.py` | TEST | CRITICAL | READ_RELEVANT (23 names + intent) |
| `tests/test_split.py` | TEST | CRITICAL | READ_RELEVANT (17) |
| `tests/test_metrics.py` | TEST | CRITICAL | READ_RELEVANT (36) |
| `tests/test_tlearner.py` | TEST | CRITICAL | READ_RELEVANT (16) |
| `tests/test_xlearner.py` | TEST | CRITICAL | READ_RELEVANT (27) |
| `tests/test_causal_forest_baseline.py` | TEST | CRITICAL | READ_RELEVANT (20) |
| `tests/test_causal_forest_runner.py` | TEST | CRITICAL | READ_RELEVANT (24) |
| `tests/test_lightgbm_baseline.py` | TEST | HIGH | READ_RELEVANT (15) |
| `tests/test_preprocessing.py` | TEST | HIGH | READ_RELEVANT (11) |
| `tests/test_audit.py` | TEST | MEDIUM | READ_RELEVANT (44) |
| `configs/t05_split.json` | CONFIG | CRITICAL | READ_FULL |
| `configs/t11_causal_forest_full.json` | CONFIG | CRITICAL | READ_FULL |
| `configs/t10_causal_forest.json` | CONFIG | HIGH | READ_RELEVANT (frozen_config, scale_gating, D31) |
| `configs/t11_gcp_parity.json` | CONFIG | HIGH | READ_RELEVANT |
| `configs/t04/t07/t08/t09_*.json` | CONFIG | MEDIUM | READ_RELEVANT (lifecycle, keys) |
| `configs/t03_audit.json` | CONFIG | LOW | SKIPPED_WITH_REASON (off the modeling path) |
| `configs/data_manifest.example.json` | DATA METADATA | HIGH | READ_FULL (real selector gitignored + absent) |
| `configs/run_config.example.json` | DATA METADATA | LOW | SKIPPED_WITH_REASON (template) |
| `kaggle/02_uplift_modeling.ipynb` | NOTEBOOK | CRITICAL | READ_RELEVANT (280 headers, RUN flags, imports, symbol frequency; cells 276-279 in full) |
| `kaggle/01_data_understanding.ipynb` | NOTEBOOK | MEDIUM | SKIPPED_WITH_REASON (22 cells, no `src` imports, no RUN flags) |
| `notebooks/internal/*.ipynb` (4) | NOTEBOOK | LOW | SKIPPED_WITH_REASON (modules read instead) |
| `notebooks/legacy/*.ipynb` (4) | NOTEBOOK | LOW | SKIPPED_WITH_REASON (superseded) |
| `learning/learning.ipynb` | NOTEBOOK | LOW | SKIPPED_WITH_REASON (scratch) |
| `README.md` | DOC | HIGH | READ_RELEVANT |
| `docs/00_project_overview.md` | DOC | HIGH | READ_FULL |
| `docs/decision_register.csv` | DECISION RECORD | CRITICAL | READ_RELEVANT (D20-D31; D30/D31 in full) |
| `docs/07_metric_specification.md` | DOC | HIGH | READ_RELEVANT (section map; formulas verified in code) |
| `docs/adr/ADR-CF-implementation.md` | DECISION RECORD | HIGH | READ_RELEVANT (8 promotion gates, seed gate) |
| `data/README.md` | DOC | MEDIUM | READ_FULL |
| `.gitignore` | ENVIRONMENT | MEDIUM | READ_FULL |
| `docs/01`-`06`, `docs/index.md` | DOC | MEDIUM | SKIPPED_WITH_REASON (targeted greps; contracts verified in code) |
| `docs/adr/*` (5 others) | DECISION RECORD | MEDIUM | SKIPPED_WITH_REASON |
| `docs/decision_register.md`, `sprint1_*`, `t01_historical_*`, `tasks/*`, `learning/*`, `literatures/*` | DOC | LOW | SKIPPED_WITH_REASON |
| `requirements.txt`, `LICENSE` | ENVIRONMENT / OTHER | LOW | SKIPPED_WITH_REASON |

---

# Appendix B -- Known Gaps / Unknowns

1. **Nothing was executed.** No tests run, no training, no data load. The
   gitignored artifacts are absent from this machine (expected on
   `temp/t11-cross-machine`). All claims are read-derived.
2. **Notebook cell bodies not read line-by-line** (~330 KB, 280 cells).
   Analyzed via headers, `RUN_*` flags, `src` imports, symbol frequency, and
   full reads of cells 276-279. `UNKNOWN`: notebook-internal helper logic.
3. **`src/metrics_reference.py`** loop bodies not line-by-line verified against
   `docs/07` prose; it is cross-checked against `metrics.py` by test, which is
   the stronger guarantee.
4. **`src/audit.py`** read in full but summarized; largely off the modeling path.
5. **9 secondary notebooks** classified by role only.
6. **`docs/01`-`06` and 5 of 6 ADRs** covered by targeted greps, not full reads.
   Where a doc and the code disagree, this guide follows the code.
7. **`UNKNOWN`: whether T07-T09 are actually complete.** Configs say
   `*_SMOKE_IN_PROGRESS`; the notebook has full seed tables. README points to
   GitHub Issue #20 as the live source of truth, not accessible during the scan.
8. **`UNKNOWN`: real resource behavior at FULL scale.** Never measured here.
9. **`INFERRED`: the notebook calls both X-Learner OOF guards.** Frequency
   counts say yes (11 and 7 occurrences) but this was not traced cell-by-cell.

---

## CLOSED-BOOK SELF CHECK

Answer without reopening this document. If you cannot state
INPUT -> OPERATION -> OUTPUT, you do not know it yet.

1. What exactly is `_source_row_id`, and what code *proves* the property that
   makes `Dataset.take()` a legitimate way to load a partition?
2. Walk the full path from `configs/data_manifest.json` to a fitted Causal
   Forest, naming each file and symbol in order.
3. Why is `exposure` excluded from `X`, and name two distinct places in code
   that would reject it if someone tried to include it.
4. How is held-out access prevented? Why is the mechanism a *missing file*
   rather than a boolean flag, and which four tests cover it?
5. In `evaluate_ranking`, what is the sort key and tie-break, and what would
   break if the tie-break were removed?
6. Write the Qini gain formula. What happens to prefixes where `cum_n0 == 0`,
   and why is that choice not "just returning zero"?
7. `qini_above_random` subtracts a specific quantity. What is it, and derive
   why that quantity is correct.
8. Why are ROC-AUC and log loss diagnostic only? Give a concrete scenario where
   a model has excellent AUC and near-random Qini.
9. Why does `reconcile_reloaded_tau` not use `np.allclose` on tau? State the
   actual bound and where it comes from.
10. In the X-Learner, define D1 and D0 including which arm each applies to, and
    state the sign convention.
11. Point to the exact step where X-Learner leakage would occur if the OOF logic
    were removed, and explain the causal chain from that step to an
    optimistically biased tau.
12. What is `g` in `combine_tau`, how is it computed, and why is it not an
    estimated propensity score?
13. Why is `n_jobs=1` in the frozen Causal Forest config? What evidence produced
    that value, and what is currently *not* protecting it?
14. What does `honest=True` do, and what bias would appear without it?
15. What does `max_samples=0.45` control, and what are its statistical and
    computational effects?
16. Exactly which conditions make `aggregate_jacobian_support().passed` False?
    Name three quantities it reports that are explicitly *not* gates, and
    explain why rank deficiency does not fail the model.
17. Why does `honest_leaf_arm_support` need `subsample[est_local]` instead of
    using the returned indices directly?
18. Name the ten fields `_verify_resume_identity` checks. Why is
    `fit_train_ids_identity` tracked separately from `train_ids_identity`?
19. Describe the memory profile of `_ensure_model_serialized`. Which four
    objects are simultaneously resident at peak, and why?
20. What does D31 lock, what is the *only* governed reason to retrain a Causal
    Forest, and what is explicitly not such a reason?
