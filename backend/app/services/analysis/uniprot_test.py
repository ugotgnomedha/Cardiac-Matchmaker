"""Unit tests for UniProtHit classification and citation formatting (offline)."""

from app.services.analysis.uniprot import UniProtHit


def _hit(keywords, function="", pubmed=None):
    """Build a UniProtHit fixture with the given keywords/function/PMIDs."""
    return UniProtHit(
        accession="P02675",
        name="Fibrinogen beta chain",
        function=function,
        keywords=keywords,
        pubmed=pubmed or [],
    )


def test_category_prefers_ecm_then_blood_then_intracellular():
    """Classification precedence is ECM, then blood, then intracellular, then other."""
    assert _hit(["Extracellular matrix"]).category() == "ECM/structural"
    assert _hit(["Blood coagulation"]).category() == "blood/plasma (likely contaminant)"
    assert _hit(["Cytoskeleton"]).category() == "intracellular (likely contaminant)"
    assert _hit(["Blood coagulation", "Collagen"]).category() == "ECM/structural"
    assert _hit([]).category() == "other"


def test_refs_lists_and_truncates_pmids():
    """refs() lists PMIDs, truncates beyond n, and notes when there are none."""
    assert _hit([], pubmed=["111", "222"]).refs() == "PMID:111, PMID:222"
    assert _hit([], pubmed=["1", "2", "3", "4"]).refs(n=3) == "PMID:1, PMID:2, PMID:3…"
    assert _hit([]).refs() == "curated entry, no primary ref"


def test_cite_includes_accession_refs_and_function():
    """cite() combines accession, refs, and the function text."""
    cite = _hit(["Collagen"], function="Forms the fibrin matrix.", pubmed=["999"]).cite()
    assert cite == "UniProt P02675 [PMID:999]: Forms the fibrin matrix."


def test_cite_trims_long_function_text():
    """cite() trims an over-long function description with an ellipsis."""
    long_fn = "word " * 100
    cite = _hit([], function=long_fn).cite(width=40)
    assert cite.endswith("…")
    assert len(cite) < 120
