"""Unit test for the LangGraph reasoning loop using a fake chat model (no Ollama)."""

import pandas as pd
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.services.analysis import constants as C
from app.services.analysis.agent import AgentContext, run_agent
from app.services.analysis.report import DecisionReport, DriverEvidence, StructureDecision


class FakeAlignment:
    """Alignment stub for the executor's match-scores tool."""

    method = "cca"
    quality = [0.7]
    proteins = [f"P{i}" for i in range(2790)]

    def best_match_per_region(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"best_prep": {"SL-Valves": "Chorion_native"}, "aligned_cosine": {"SL-Valves": 0.99}}
        )


def _decision_report() -> DecisionReport:
    return DecisionReport(
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
                drivers=[DriverEvidence("COL1A1", 0.04, "Collagens", "ECM/structural", "p.6: collagen", "literature", page=6)],
                caveats=["Scores are cross-dataset patterns, not absolute abundances."],
            )
        ],
    )


def _fake_llm():
    """Canned planner / critic-JSON / reporter replies, in call order."""
    return GenericFakeChatModel(
        messages=iter(
            [
                AIMessage(content="1. align 2. drivers 3. functions 4. robustness"),
                AIMessage(content='{"approved": true, "contradictions": ["FGB is blood-derived"], "notes": "patterns not abundance"}'),
                AIMessage(content="Chorion_native is the closest aligned match for semilunar valves."),
            ]
        )
    )


def test_agent_loop_plans_executes_critiques_and_reports():
    """The loop runs end to end and surfaces plan, findings, contradictions, and a report."""
    context = AgentContext(llm=_fake_llm(), alignment=FakeAlignment(), decision_report=_decision_report())
    result = run_agent(context, "Which placental tissue is best for semilunar valve replacement?")

    assert result.approved is True
    assert result.rounds == 1
    assert "align" in result.plan.lower()
    # Executor grounded its findings in the deterministic engine.
    assert "Chorion_native" in result.findings
    assert "alignment=cca" in result.findings
    # Critic contradictions parsed from the model's JSON.
    assert result.contradictions == ["FGB is blood-derived"]
    # Report = deterministic backbone + agent narration + critic section.
    assert "# Cardiac Matchmaker — Decision Report" in result.report
    assert "## Agent reasoning" in result.report
    assert "closest aligned match" in result.report
    assert "FGB is blood-derived" in result.report
