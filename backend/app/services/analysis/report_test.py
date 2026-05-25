"""Unit tests for the Decision Report builder using a stubbed alignment, retriever, and UniProt."""

import pandas as pd

from app.services.analysis import constants as C
from app.services.analysis.rag import Hit
from app.services.analysis.report import build_report
from app.services.analysis.uniprot import UniProtHit


DRIVERS = {
    "Chorion_native": ["COL1A1", "FGB", "OGN", "XYZ1"],
}


class FakeAlignment:
    """Minimal alignment stub exposing score_matrix and drivers."""

    method = "cca"
    quality = [0.7, 0.31]
    proteins = [f"P{i}" for i in range(2790)]

    def score_matrix(self) -> pd.DataFrame:
        """Scores where Chorion_native wins SL-Valves clearly and Ventricle narrowly."""
        base = {prep: 0.85 for prep in C.PLACENTA_PREPS}
        sl = dict(base, Chorion_native=0.992, Amnion_decell=0.972)
        vent = dict(base, Chorion_native=0.905, Amnion_decell=0.900)
        return pd.DataFrame({"SL-Valves": sl, "Ventricle": vent})

    def drivers(self, prep: str, structure: str, top: int = 5) -> pd.DataFrame:
        """Fixed driver rows for the given prep."""
        genes = DRIVERS[prep][:top]
        cats = {"COL1A1": "Collagens", "FGB": "ECM Glycoproteins", "OGN": "Proteoglycans"}
        return pd.DataFrame(
            {
                "GeneName": genes,
                "MatrisomeCategory": [cats.get(g) for g in genes],
                "contribution": [0.04, 0.03, 0.02, 0.01][: len(genes)],
            }
        )


class StubRetriever:
    """Retriever stub that grounds only COL1A1 in the literature."""

    def protein_function(self, name: str, k: int = 1):
        """Return a single passage for COL1A1, nothing otherwise."""
        if name == "COL1A1":
            return [
                Hit(
                    page=6,
                    score=0.5,
                    text="Fibrillar collagen COL1A1 provides tensile strength to the matrix.",
                    chunk_index=3,
                    chunk_id="chunk-1",
                    document_id="doc-1",
                )
            ]
        return []


class StubUniProt:
    """UniProt stub returning canned hits for a few genes."""

    HITS = {
        "FGB": UniProtHit("P02675", "Fibrinogen beta", "Forms fibrin.", ["Blood coagulation"], ["111"]),
        "OGN": UniProtHit("P20774", "Osteoglycin", "Induces bone formation.", ["Proteoglycan"], []),
        "COL1A1": UniProtHit("P02452", "Collagen I", "Structural collagen.", ["Collagen"], ["222"]),
    }

    def lookup(self, gene: str):
        """Return the canned hit for a gene, or None."""
        return self.HITS.get(gene)


def _report():
    """Build a report over two structures with the stubs."""
    return build_report(
        FakeAlignment(),
        ["SL-Valves", "Ventricle"],
        retriever=StubRetriever(),
        uniprot=StubUniProt(),
        n_drivers=4,
    )


def test_recommendation_and_ranking():
    """The top structure recommends the highest-scoring prep with the right margin."""
    report = _report()
    assert report.method == "cca"
    assert report.n_anchor_proteins == 2790

    sl = report.structures[0]
    assert sl.structure == "SL-Valves"
    assert sl.recommendation == "Chorion_native"
    assert sl.best_score == 0.992
    assert sl.runner_up == "Amnion_decell"
    assert sl.margin == 0.02
    assert sl.use_case == C.USE_CASE["SL-Valves"]


def test_driver_grounding_prefers_literature_then_uniprot():
    """Drivers are grounded in literature first, then UniProt, then marked ungrounded."""
    sl = _report().structures[0]
    by_gene = {d.gene: d for d in sl.drivers}

    assert by_gene["COL1A1"].source == "literature"
    assert by_gene["COL1A1"].page == 6
    assert by_gene["COL1A1"].function.startswith("p.6:")
    assert by_gene["COL1A1"].chunk_id == "chunk-1"

    assert by_gene["FGB"].source == "uniprot"
    assert by_gene["FGB"].is_contaminant is True
    assert by_gene["FGB"].pmids == ["111"]

    assert by_gene["XYZ1"].source == "none"


def test_caveats_flag_contaminants_and_thin_margin():
    """Caveats call out contaminant drivers and thin recommendation margins."""
    report = _report()
    sl_caveats = " ".join(report.structures[0].caveats)
    assert "FGB" in sl_caveats and "contaminant" in sl_caveats

    ventricle = report.structures[1]
    assert ventricle.margin < 0.01
    assert any("thin" in c for c in ventricle.caveats)


def test_markdown_and_json_render():
    """The report renders to markdown and JSON with the recommendation and citations."""
    report = _report()
    md = report.to_markdown()
    assert "**Recommendation: Chorion_native**" in md
    assert "| COL1A1 |" in md
    assert "p.6:" in md

    blob = report.to_json()
    assert blob["structures"][0]["recommendation"] == "Chorion_native"
    assert blob["structures"][0]["ranking"][0]["prep"] == "Chorion_native"
    assert blob["n_anchor_proteins"] == 2790
