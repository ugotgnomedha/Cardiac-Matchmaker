"""Unit tests for AnalysisService target-structure resolution (no database)."""

from types import SimpleNamespace

from app.services.analysis import constants as C
from app.services.analysis.pipeline import AnalysisService


def _run(constraints=None, tissue="", application="", query=""):
    """Build a fake run object with the fields structure resolution reads."""
    return SimpleNamespace(
        constraints=constraints,
        target_tissue=tissue,
        target_application=application,
        query=query,
    )


def test_explicit_structure_constraint_wins():
    """An explicit constraints.structure is used directly."""
    svc = AnalysisService()
    assert svc._resolve_structures(_run(constraints={"structure": "SL-Valves"})) == ["SL-Valves"]


def test_structures_list_filters_to_known_regions():
    """A constraints.structures list is filtered to known heart regions."""
    svc = AnalysisService()
    resolved = svc._resolve_structures(_run(constraints={"structures": ["Atrium", "bogus", "Ventricle"]}))
    assert resolved == ["Atrium", "Ventricle"]


def test_keyword_resolution_from_free_text():
    """Free-text target fields resolve to a structure by keyword."""
    svc = AnalysisService()
    assert svc._resolve_structures(_run(tissue="aortic valve replacement")) == ["SL-Valves"]
    assert svc._resolve_structures(_run(application="coronary artery bypass")) == ["coronaryArtery"]


def test_unresolvable_target_falls_back_to_all_structures():
    """An unresolvable target falls back to reporting all structures."""
    svc = AnalysisService()
    assert svc._resolve_structures(_run(tissue="unspecified soft tissue")) == list(C.HEART_REGIONS)
