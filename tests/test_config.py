"""configs/config.yaml must stay in sync with the code defaults.

A config file nobody reads is worse than no config file: it looks
authoritative while silently disagreeing with what actually runs. These
tests make the drift impossible.
"""

from __future__ import annotations

import src.evaluation as evaluation
import src.models as models
import src.preprocessing as preprocessing
from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, CSV_FILENAME, PRIMARY_OUTCOME
from src.data import SECONDARY_OUTCOME, TREATMENT_COLUMN, load_config

CONFIG = load_config()


def test_data_section_matches_code() -> None:
    data = CONFIG["data"]
    assert data["csv_filename"] == CSV_FILENAME
    assert data["treatment_column"] == TREATMENT_COLUMN
    assert data["primary_outcome"] == PRIMARY_OUTCOME
    assert data["secondary_outcome"] == SECONDARY_OUTCOME
    assert tuple(data["continuous_features"]) == CONTINUOUS_FEATURES
    assert tuple(data["categorical_features"]) == CATEGORICAL_FEATURES


def test_split_section_matches_code() -> None:
    split = CONFIG["split"]
    assert split["train_fraction"] == preprocessing.TRAIN_FRACTION
    assert split["validation_fraction"] == preprocessing.VALIDATION_FRACTION
    assert split["test_fraction"] == preprocessing.TEST_FRACTION
    assert split["train_fraction"] + split["validation_fraction"] + split["test_fraction"] == 1.0
    assert split["stratify_by"] == [TREATMENT_COLUMN, PRIMARY_OUTCOME]


def test_seed_matches_code() -> None:
    assert CONFIG["seed"] == preprocessing.SPLIT_SEED
    assert CONFIG["seed"] == models.BINARY_CONFIG["seed"]


def test_lightgbm_section_matches_code() -> None:
    lgbm = CONFIG["lightgbm"]
    assert lgbm["objective"] == models.BINARY_CONFIG["objective"]
    assert lgbm["learning_rate"] == models.BINARY_CONFIG["learning_rate"]
    assert lgbm["num_leaves"] == models.BINARY_CONFIG["num_leaves"]
    assert lgbm["min_data_in_leaf"] == models.BINARY_CONFIG["min_data_in_leaf"]
    assert lgbm["num_boost_round_cap"] == models.NUM_BOOST_ROUND_CAP
    assert lgbm["early_stopping_rounds"] == models.EARLY_STOPPING_ROUNDS


def test_xlearner_section_matches_code() -> None:
    xlearner = CONFIG["xlearner"]
    assert xlearner["cross_fitting_folds"] == models.CROSS_FITTING_FOLDS
    assert xlearner["effect_num_boost_round"] == models.EFFECT_NUM_BOOST_ROUND
    assert xlearner["inner_validation_fraction"] == models.INNER_VALIDATION_FRACTION


def test_causal_forest_section_matches_code() -> None:
    forest = CONFIG["causal_forest"]
    for key in (
        "n_estimators", "max_depth", "honest", "inference", "min_samples_leaf",
        "max_samples", "subforest_size", "n_jobs",
    ):
        assert forest[key] == models.CAUSAL_FOREST_CONFIG[key], f"config/code mismatch on causal_forest.{key}"
    assert forest["n_estimators"] % forest["subforest_size"] == 0, "econml requires n_estimators % subforest_size == 0"
    assert forest["categorical_top_k"] in preprocessing.CATEGORICAL_ENCODER_K_LADDER


def test_evaluation_section_matches_code() -> None:
    assert tuple(CONFIG["evaluation"]["uplift_at_k"]) == evaluation.RANKING_K_GRID
