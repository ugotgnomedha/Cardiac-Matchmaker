"""Unit tests for the alignment engine on synthetic data with a planted cross-domain signal."""

import numpy as np
import pandas as pd
import pytest

from app.services.analysis import alignment as A
from app.services.analysis import constants as C
from app.services.analysis.proteomics import ProteomicsData


def _synthetic_data(seed: int = 0) -> ProteomicsData:
    """Placental and cardiac matrices sharing a latent signal on very different scales."""
    rng = np.random.default_rng(seed)
    n = 60
    proteins = pd.Index([f"P{i}" for i in range(n)])

    latent = rng.normal(size=(n, 3))
    prep_loadings = rng.normal(size=(3, len(C.PLACENTA_PREPS)))
    region_loadings = rng.normal(size=(3, len(C.HEART_REGIONS)))

    prep_vals = 4.5 + 1.2 * (latent @ prep_loadings) + 0.1 * rng.normal(size=(n, len(C.PLACENTA_PREPS)))
    region_vals = 25.0 + 3.0 * (latent @ region_loadings) + 0.2 * rng.normal(size=(n, len(C.HEART_REGIONS)))

    prep_matrix = pd.DataFrame(prep_vals, index=proteins, columns=list(C.PLACENTA_PREPS))
    heart_matrix = pd.DataFrame(region_vals, index=proteins, columns=C.HEART_REGIONS)
    categories = ["Collagens", "ECM Glycoproteins", "Proteoglycans"]
    annotation = pd.DataFrame(
        {
            "GeneName": proteins,
            "MatrisomeDivision": "Core matrisome",
            "MatrisomeCategory": [categories[i % len(categories)] for i in range(n)],
        },
        index=proteins,
    )
    return ProteomicsData(prep_matrix, heart_matrix, annotation)


def test_cca_alignment_recovers_shared_structure():
    """CCA recovers the shared signal despite the scale gap and improves cross-domain correlation."""
    alignment = A.fit(_synthetic_data(), method="cca")

    assert alignment.quality[0] > 0.5
    before, after = A.cross_domain_gain(alignment)
    assert after > before


def test_score_matrix_is_well_formed_cosine():
    """The score matrix has the right shape and finite cosines in [-1, 1]."""
    scores = A.fit(_synthetic_data(), method="cca").score_matrix()

    assert list(scores.index) == list(C.PLACENTA_PREPS)
    assert list(scores.columns) == C.HEART_REGIONS
    assert np.isfinite(scores.to_numpy()).all()
    assert scores.to_numpy().min() >= -1.0001
    assert scores.to_numpy().max() <= 1.0001


def test_drivers_and_translate_shapes():
    """Drivers are ranked by contribution and translate ranks all structures."""
    alignment = A.fit(_synthetic_data(), method="cca")
    best = alignment.best_match_per_region()
    prep = best.loc["SL-Valves", "best_prep"]

    drivers = alignment.drivers(prep, "SL-Valves", top=5)
    assert len(drivers) == 5
    assert list(drivers.columns) == ["GeneName", "MatrisomeCategory", "prep_abundance", "contribution"]
    assert drivers["contribution"].is_monotonic_decreasing

    ranking = alignment.translate(prep)
    assert set(ranking.index) == set(C.HEART_REGIONS)
    assert ranking.is_monotonic_decreasing


def test_procrustes_method_also_scores():
    """The Procrustes method produces a finite score matrix too."""
    scores = A.fit(_synthetic_data(), method="procrustes").score_matrix()
    assert scores.shape == (len(C.PLACENTA_PREPS), len(C.HEART_REGIONS))
    assert np.isfinite(scores.to_numpy()).all()


def test_fit_rejects_too_few_anchor_proteins():
    """Fitting fails clearly when too few proteins are shared by both domains."""
    data = _synthetic_data()
    tiny = ProteomicsData(
        data.prep_matrix,
        data.heart_matrix.iloc[:2],
        data.annotation,
    )
    with pytest.raises(ValueError, match="too few anchor proteins"):
        A.fit(tiny, method="cca")
