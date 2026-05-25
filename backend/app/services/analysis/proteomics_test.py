"""Unit tests for build_matrices: replicate averaging, heart filtering, and annotation."""

import math

from app.services.analysis import constants as C
from app.services.analysis.proteomics import build_matrices


def _measurements():
    """Synthetic (sample, gene, value) rows; A/B are in the heart, C is placenta-only."""
    return [
        ("Amnion_decell_1", "A", 4.0),
        ("Amnion_decell_2", "A", 6.0),
        ("Chorion_native_1", "A", 2.0),
        ("Amnion_decell_1", "B", 1.0),
        ("Chorion_native_1", "B", 3.0),
        ("Amnion_decell_1", "C", 7.0),
        ("SL-Valves", "A", 20.0),
        ("Ventricle", "A", 22.0),
        ("SL-Valves", "B", 18.0),
        ("Ventricle", "B", 19.0),
    ]


def _build():
    """Build ProteomicsData from the synthetic fixture."""
    return build_matrices(
        _measurements(),
        present_in_heart={"A", "B"},
        matrisome_division={"A": "Core matrisome", "B": "Core matrisome", "C": None},
        matrisome_category={"A": "Collagens", "B": "ECM Glycoproteins", "C": None},
    )


def test_prep_matrix_averages_replicates_and_spans_all_preps():
    """Replicates average per prep and every prep appears as a column."""
    data = _build()
    prep = data.prep_matrix

    assert list(prep.columns) == list(C.PLACENTA_PREPS)
    assert prep.loc["A", "Amnion_decell"] == 5.0
    assert prep.loc["A", "Chorion_native"] == 2.0
    assert prep["Basaltissue_native"].isna().all()


def test_heart_matrix_keeps_only_heart_proteins_over_all_structures():
    """Only heart-present proteins remain, over all heart structures."""
    data = _build()
    heart = data.heart_matrix

    assert set(heart.index) == {"A", "B"}
    assert list(heart.columns) == C.HEART_REGIONS
    assert heart.loc["A", "SL-Valves"] == 20.0
    assert math.isnan(heart.loc["A", "Atrium"])


def test_annotation_tracks_matrisome_category():
    """Annotation carries the matrisome category and gene name per protein."""
    data = _build()
    assert data.annotation.loc["A", "MatrisomeCategory"] == "Collagens"
    assert data.annotation.loc["A", "GeneName"] == "A"
    assert data.annotation.loc["C", "MatrisomeCategory"] is None
