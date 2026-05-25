"""LangGraph reasoning loop: Planner -> Executor -> Critic -> Reporter.

The Executor runs the deterministic engine tools (the numbers and citations come
from there, never the model); the Planner drafts the research plan, the Critic
flags contradictions between the numerical matches and the literature, and the
Reporter narrates the final Decision Report. The chat model is injected so the
loop can be exercised with a fake model in tests.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.services.analysis import agent_tools as tools

MAX_ROUNDS = 2

DOMAIN = (
    "Cardiac Matchmaker recommends which placental preparation (Amnion, Basaltissue, "
    "Chorion, UmbilicalCord — native or decellularized) best suits a heart structure "
    "(largeAtery, coronaryArtery, Atrium, Ventricle, AV-Valves, SL-Valves) for tissue "
    "engineering. Placenta and heart were measured on different scales (log2 ~2-7 vs "
    "~20-30); a domain-adaptation alignment makes them comparable — only PATTERNS are "
    "comparable, never absolute abundances."
)

PLANNER_SYS = (
    f"You are the PLANNER. {DOMAIN}\n\nOutput a short numbered plan (2-5 steps): get the "
    "aligned matches, get drivers for the recommendation, look up driver-protein functions "
    "in the literature, and check robustness."
)

CRITIC_SYS = (
    "You are the CRITIC, a skeptical proteomics reviewer. Examine the proposed answer "
    "against the cited evidence and flag CONTRADICTIONS between the numerical match and the "
    "literature (e.g. a 'driver' the literature calls blood-derived/contaminant rather than "
    "structural ECM, or one tied to a different structure). Enforce: claims are about "
    "PATTERNS not absolute abundance; ECM-only rankings beyond umbilical-cord<->large-artery "
    "are unstable.\n"
    'Respond with ONLY JSON: {"approved": bool, "contradictions": ["..."], '
    '"critique": "what to fix", "notes": "caveats for the report"}.'
)

REPORTER_SYS = (
    f"You are the REPORTER. {DOMAIN}\n\nWrite a concise, quantitative narrative naming the "
    "recommended preparation, its aligned score, the driver proteins with their functions "
    "and citations, and the robustness. Do not invent numbers — use only the evidence."
)


class State(TypedDict, total=False):
    """Mutable state passed through the agent graph."""

    query: str
    plan: str
    findings: str
    contradictions: list
    notes: str
    critique: str
    approved: bool
    rounds: int
    report: str


@dataclass
class AgentContext:
    """Everything a run's graph needs: the model and the run's engine outputs."""

    llm: Any
    alignment: Any
    decision_report: Any


@dataclass
class AgentResult:
    """The graph's output, ready to persist as steps, warnings, and a report."""

    plan: str = ""
    findings: str = ""
    contradictions: list = field(default_factory=list)
    notes: str = ""
    critique: str = ""
    approved: bool = False
    rounds: int = 0
    report: str = ""


def _extract_json(text: str) -> dict:
    """Best-effort parse of a JSON object from an LLM reply."""
    text = re.sub(r"```(?:json)?|```", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def build_graph(context: AgentContext):
    """Compile the Planner->Executor->Critic->Reporter graph for one run."""

    def planner(state: State) -> dict:
        """Draft the research plan for the query."""
        msg = context.llm.invoke([("system", PLANNER_SYS), ("human", state["query"])])
        return {"plan": msg.content, "rounds": 0}

    def executor(state: State) -> dict:
        """Run the deterministic engine tools into a grounded findings narrative."""
        findings = (
            tools.match_scores_text(context.alignment)
            + "\n\n"
            + tools.findings_from_report(context.decision_report)
        )
        return {"findings": findings}

    def critic(state: State) -> dict:
        """Flag numerical-vs-literature contradictions (capped at MAX_ROUNDS)."""
        review = context.llm.invoke(
            [
                ("system", CRITIC_SYS),
                ("human", f"Question:\n{state['query']}\n\nAnswer + evidence:\n{state['findings']}"),
            ]
        )
        data = _extract_json(review.content)
        rounds = state.get("rounds", 0) + 1
        return {
            "approved": bool(data.get("approved")) or rounds >= MAX_ROUNDS,
            "contradictions": data.get("contradictions", []),
            "notes": data.get("notes", ""),
            "critique": data.get("critique", ""),
            "rounds": rounds,
        }

    def reporter(state: State) -> dict:
        """Narrate the final report on top of the deterministic backbone."""
        narration = context.llm.invoke(
            [
                ("system", REPORTER_SYS),
                (
                    "human",
                    f"Question:\n{state['query']}\n\nEvidence:\n{state['findings']}\n\n"
                    f"Critic caveats:\n{state.get('notes', '')}",
                ),
            ]
        ).content
        parts = [context.decision_report.to_markdown(), "\n---\n## Agent reasoning\n", narration]
        if state.get("contradictions"):
            parts.append("\n## Critic — numerical-vs-literature contradictions")
            parts += [f"- {c}" for c in state["contradictions"]]
        if state.get("notes"):
            parts.append(f"\n## Critic — caveats\n{state['notes']}")
        return {"report": "\n".join(parts)}

    g = StateGraph(State)  # pyrefly: ignore
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_node("critic", critic)
    g.add_node("reporter", reporter)
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "critic")
    g.add_conditional_edges(
        "critic",
        lambda s: "reporter" if s["approved"] else "executor",
        {"reporter": "reporter", "executor": "executor"},
    )
    g.add_edge("reporter", END)
    return g.compile()


def run_agent(context: AgentContext, query: str) -> AgentResult:
    """Run the reasoning loop for a query and return its result."""
    final = build_graph(context).invoke({"query": query}, config={"recursion_limit": 50})
    return AgentResult(
        plan=final.get("plan", ""),
        findings=final.get("findings", ""),
        contradictions=final.get("contradictions", []),
        notes=final.get("notes", ""),
        critique=final.get("critique", ""),
        approved=bool(final.get("approved")),
        rounds=final.get("rounds", 0),
        report=final.get("report", ""),
    )
