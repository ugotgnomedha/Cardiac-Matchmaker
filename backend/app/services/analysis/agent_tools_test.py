"""Unit tests for the agent tool views (no LLM)."""

import pandas as pd

from app.services.analysis import agent_tools as T
from app.services.analysis import constants as C
from app.services.analysis.rag import Hit
from app.services.analysis.report import DecisionReport, DriverEvidence, StructureDecision
from app.services.analysis.uniprot import UniProtHit


class FakeAlignment:
    """Alignment stub exposing the views the tools read."""

    method = "cca"
    quality = [0.7]
    proteins = [f"P{i}" for i in range(10)]

    def best_match_per_region(self) -> pd.DataFrame:
        """Best prep + cosine per structure."""
        return pd.DataFrame(
            {"best_prep": {"SL-Valves": "Chorion_native"}, "aligned_cosine": {"SL-Valves": 0.99}}
        )

    def drivers(self, prep: str, region: str, top: int = 8) -> pd.DataFrame:
        """A couple of driver rows."""
        return pd.DataFrame({"GeneName": ["COL1A1", "FN1"], "contribution": [0.04, 0.03]})

    def translate(self, prep: str) -> pd.Series:
        """A ranking over structures."""
        return pd.Series({"SL-Valves": 0.99, "Ventricle": 0.95})


class StubRetriever:
    """Retriever stub grounding only COL1A1."""

    def protein_function(self, name: str, k: int = 3):
        if name == "COL1A1":
            return [Hit(page=6, score=0.5, text="COL1A1 collagen provides strength.", chunk_index=0)]
        return []


class StubUniProt:
    """UniProt stub for FGB only."""

    def lookup(self, gene: str):
        if gene == "FGB":
            return UniProtHit("P02675", "Fibrinogen beta", "Forms fibrin.", ["Blood coagulation"], ["111"])
        return None


def test_match_scores_text_includes_quality_and_table():
    """The scores view reports method, quality, anchors, and the best-match table."""
    text = T.match_scores_text(FakeAlignment())
    assert "alignment=cca" in text
    assert "anchors=10" in text
    assert "Chorion_native" in text


def test_drivers_and_translate_text():
    """Driver and translate views render their tables."""
    assert "COL1A1" in T.drivers_text(FakeAlignment(), "Chorion_native", "SL-Valves")
    assert "Ventricle" in T.translate_text(FakeAlignment(), "Chorion_native")


def test_protein_function_text_prefers_literature_then_uniprot():
    """Literature citation wins; UniProt is the fallback; otherwise a not-found note."""
    retriever, uniprot = StubRetriever(), StubUniProt()
    assert T.protein_function_text(retriever, uniprot, "COL1A1").startswith("Literature:")
    assert "p.6" in T.protein_function_text(retriever, uniprot, "COL1A1")
    assert "UniProt P02675" in T.protein_function_text(retriever, uniprot, "FGB")
    assert "no function" in T.protein_function_text(retriever, uniprot, "NOPE")


def test_findings_from_report_summarises_recommendation_and_drivers():
    """The findings text lists the recommendation, ranking, drivers, and caveats."""
    report = DecisionReport(
        method="cca",
        n_anchor_proteins=2790,
        alignment_quality=[0.7],
        matrisome_only=False,
        structures=[
            StructureDecision(
                structure="SL-Valves",
                use_case=C.USE_CASE["SL-Valves"],
                recommendation="Chorion_native",
                best_score=0.992,
                runner_up="Amnion_decell",
                runner_up_score=0.972,
                margin=0.02,
                ranking=[("Chorion_native", 0.992), ("Amnion_decell", 0.972)],
                drivers=[
                    DriverEvidence("COL1A1", 0.04, "Collagens", "ECM/structural", "p.6: collagen", "literature", page=6)
                ],
                caveats=["Scores are cross-dataset patterns, not absolute abundances."],
            )
        ],
    )
    text = T.findings_from_report(report)
    assert "recommend Chorion_native" in text
    assert "COL1A1 [ECM/structural; literature]" in text
    assert "Caveats:" in text
