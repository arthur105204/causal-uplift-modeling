# Data directory

## Data is not version controlled

Raw and processed data are local inputs and must not be committed. Only this
README is versioned under `data/`.

The repository's MIT License applies to code and documentation, not to
CRITEO-UPLIFTv2.1 itself — the dataset remains subject to the publisher's
separate terms and license.

## Expected local layout

```text
data/
├── README.md
├── raw/          criteo-uplift-v2.1.csv (or the Kaggle-attached input)
└── processed/    optional Parquet output from notebooks/01_data_processing.ipynb
```

## Expected columns

- numeric features `f0` through `f11`;
- binary `treatment` assignment;
- binary primary outcome `conversion`;
- optional secondary outcome `visit`;
- optional post-assignment/audit field `exposure` (never used as a feature).

## Causal usage

- `X` is exactly ordered `f0`–`f11`. Per D32, `f0`, `f2`, `f7`, `f10` are
  continuous; `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11` are categorical
  numeric tokens with no ordinal meaning (see README.md "Methodology notes").
- `treatment` defines `T`.
- `conversion` is the primary `Y`; `visit` is an optional secondary outcome.
- `exposure` is post-assignment and must never enter `X`, define eligibility,
  or replace treatment assignment.

## On Kaggle

Attach a Kaggle dataset containing `criteo-uplift-v2.1.csv`; `notebooks/01_data_processing.ipynb`
auto-detects the Kaggle input path, falling back to `data/raw/` for local runs.

## Privacy

Do not commit raw or processed rows, row-level samples, predictions, or model
artifacts. Review any artifact you do want to share for aggregation and
publisher-license compliance first.
