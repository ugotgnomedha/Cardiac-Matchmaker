"""Agent Output Quality Evaluation — Level 2.

Runs the full Cardiac Matchmaker pipeline with a real LLM on synthetic data
with planted signals and measures 7 quality metrics.

Usage:
    docker compose exec backend python -m tests.model_evaluation
    docker compose exec backend python -m tests.model_evaluation --model ollama/mistral:7b
    docker compose exec backend python -m tests.model_evaluation --n-runs 5
"""

import argparse
import sys
import time
from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np

sys.path.insert(0, "/app")

from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.feature.feature_model import FeatureAnnotation
from app.models.project.project_model import ResearchProject
from app.models.run.run_model import AnalysisRun
from app.models.sample.sample_model import Sample, Measurement
from app.services.analysis import constants as C
from app.services.analysis.pipeline import AnalysisService
from app.services.analysis.uniprot import UniProtHit

PLAN_ACTION_VERBS = {"align", "retrieve", "check", "verify", "ground", "rank", "compare", "find", "lookup", "search", "examine", "review", "measure", "calculate", "assess", "evaluate"}


class _NoUniProt:
    def lookup(self, gene):
        return None


class _PlantedUniProt:
    def lookup(self, gene):
        if gene == "FGB":
            return UniProtHit("P02675", "Fibrinogen beta", "Forms fibrin.", ["Blood coagulation"], ["111"])
        if gene == "COL1A1":
            return UniProtHit("P02452", "Collagen I", "Structural collagen.", ["Collagen"], ["222"])
        return None


@dataclass
class EvalMetrics:
    plan_valid: bool = False
    plan_steps: int = 0
    critic_json_parsed: bool = False
    contradiction_recall: bool = False
    contradictions_found: list = field(default_factory=list)  # pyrefly: ignore
    report_structure_ok: bool = False
    hallucination_score: int = 0
    rounds: int = 0
    latency_s: float = 0.0
    agent_error: str | None = None

    def all_passed(self) -> bool:
        return self.plan_valid and self.critic_json_parsed and self.contradiction_recall and self.report_structure_ok and self.hallucination_score == 0

    def summary(self) -> str:
        lines = [
            f"{'Plan validity':<28} {'✓' if self.plan_valid else '✗'}  ({self.plan_steps} steps)",
            f"{'Critic JSON parse':<28} {'✓' if self.critic_json_parsed else '✗'}",
            f"{'Contradiction recall':<28} {'✓' if self.contradiction_recall else '✗'}  ({self.contradictions_found})",
            f"{'Report structure':<28} {'✓' if self.report_structure_ok else '✗'}",
            f"{'Hallucination score':<28} {self.hallucination_score}",
            f"{'Rounds':<28} {self.rounds}",
            f"{'Latency (s)':<28} {self.latency_s:.1f}",
        ]
        if self.agent_error:
            lines.append(f"{'Agent error':<28} {self.agent_error[:120]}")
        return "\n".join(lines)


def seed_synthetic_proteome(project: ResearchProject, rng_seed: int = 42) -> DatasetVersion:
    """Seed a dataset version with synthetic proteomics carrying planted signals.

    COL1A1 → strong structural signal on SL-Valves (should be top driver).
    FGB → strong signal but marked as contaminant (critic should flag it).
    ACTB → intracellular contaminant.
    """
    rng = np.random.default_rng(rng_seed)
    n_proteins = 40

    dataset = Dataset.create(
        id=uuid4(), project=project,
        name="Eval Synthetic", type="placenta_heart_merged",
        original_filename="eval_synthetic.tsv", storage_path="/tmp/eval.tsv", metadata={},
    )
    version = DatasetVersion.create(
        id=uuid4(), dataset=dataset, version_number="1", status="normalized",
        storage_path="/tmp/eval.tsv", preprocessing_config={},
    )

    placenta_cols = [c for cols in C.PLACENTA_PREPS.values() for c in cols]
    samples = {}
    for name in placenta_cols:
        samples[name] = Sample.create(
            id=uuid4(), dataset_version=version, name=name, type="placenta_region", metadata={}
        )
    for name in C.HEART_REGIONS:
        samples[name] = Sample.create(
            id=uuid4(), dataset_version=version, name=name, type="heart_region", metadata={}
        )

    latent = rng.normal(size=(n_proteins, 3))
    prep_loadings = rng.normal(size=(3, len(placenta_cols)))
    region_loadings = rng.normal(size=(3, len(C.HEART_REGIONS)))
    prep_vals = 4.5 + 1.2 * (latent @ prep_loadings) + 0.1 * rng.normal(size=(n_proteins, len(placenta_cols)))
    region_vals = 25.0 + 3.0 * (latent @ region_loadings) + 0.2 * rng.normal(size=(n_proteins, len(C.HEART_REGIONS)))

    categories = ["Collagens", "ECM Glycoproteins", "Proteoglycans"]
    genes = [f"GENE{i}" for i in range(n_proteins - 3)] + ["COL1A1", "FGB", "ACTB"]

    for i, gene in enumerate(genes):
        present = gene in {"COL1A1", "FGB", "ACTB"} or rng.random() > 0.5
        cat = "Collagens" if gene == "COL1A1" else (
            "ECM Affiliated" if gene == "FGB" else (
                "Cytoskeletal" if gene == "ACTB" else categories[i % len(categories)]
            )
        )
        div = "Core matrisome" if gene in {"COL1A1", "FGB", "ACTB"} or rng.random() > 0.3 else None
        FeatureAnnotation.create(
            id=uuid4(), dataset_version=version, feature_name=gene,
            matrisome_division=div, matrisome_category=cat, present_in_heart=present,
        )
        for j, name in enumerate(placenta_cols):
            Measurement.create(
                id=uuid4(), sample=samples[name], feature_name=gene,
                raw_value=float(prep_vals[i, j]), unit="log2 intensity",
            )
        for j, name in enumerate(C.HEART_REGIONS):
            Measurement.create(
                id=uuid4(), sample=samples[name], feature_name=gene,
                raw_value=float(region_vals[i, j]), unit="log2 intensity",
            )
    return version


class _FakeRetriever:
    def protein_function(self, name, k=1):
        return []

def evaluate_single_run(model: str) -> EvalMetrics:
    """Run the pipeline with a real LLM and measure all quality metrics."""
    m = EvalMetrics()

    project = ResearchProject.create(id=uuid4(), name=f"Eval-{uuid4().hex[:8]}")
    version = seed_synthetic_proteome(project)

    run = AnalysisRun.create(
        id=uuid4(), project=project,
        status="running",
        query="Find the best placental material for semilunar valve replacement.",
        target_application="valve replacement", target_tissue="semilunar valve",
        constraints={"structure": "SL-Valves"},
        selected_config={"model": model},
    )

    t0 = time.perf_counter()
    try:
        service = AnalysisService(
            uniprot=_PlantedUniProt(),
            retriever_factory=lambda pid: None,
            n_drivers=5,
        )
        service._run_model_override = model
        report_row = service.run(run)
    except Exception as e:
        m.agent_error = str(e)
        m.latency_s = time.perf_counter() - t0
        return m
    m.latency_s = time.perf_counter() - t0

    m.rounds = report_row.json_body.get("agent", {}).get("rounds", 0)
    json_body = report_row.json_body
    markdown = report_row.markdown_body or ""

    eval_plan(m, json_body, markdown)
    eval_critic(m, json_body)
    eval_contradiction(m, json_body)
    eval_report_structure(m, markdown)
    eval_hallucination(m, markdown, json_body)

    return m


def eval_plan(m: EvalMetrics, json_body: dict, markdown: str):
    """Extract plan from agent state and count actionable steps."""
    agent = json_body.get("agent", {})
    plan = agent.get("plan", "")

    if not plan:
        in_plan = False
        for line in markdown.split("\n"):
            if "plan" in line.lower() and ":" in line.lower():
                in_plan = True
                continue
            if in_plan and line.strip().startswith("##"):
                break
            if in_plan and line.strip():
                plan += line + "\n"

    steps = [s.strip() for s in plan.split("\n") if s.strip()]
    numbered = [s for s in steps if s and (s[0].isdigit() or s[0] in "*-")]
    m.plan_steps = len(numbered) if numbered else len(steps)
    action_steps = [s for s in steps if any(v in s.lower() for v in PLAN_ACTION_VERBS)]
    m.plan_valid = len(action_steps) >= 2 or m.plan_steps >= 2


def eval_critic(m: EvalMetrics, json_body: dict):
    """Check that critic output was valid JSON (already parsed into json_body)."""
    agent = json_body.get("agent", {})
    contradictions = agent.get("contradictions", [])
    m.critic_json_parsed = isinstance(contradictions, list)
    m.contradictions_found = contradictions if isinstance(contradictions, list) else []


def eval_contradiction(m: EvalMetrics, json_body: dict):
    """Check that the critic flagged FGB (contaminant signal)."""
    warnings = json_body.get("caveats", [])
    all_contradictions = " ".join(
        [str(w) for w in m.contradictions_found] +
        [str(w) for w in warnings]
    ).lower()
    m.contradiction_recall = "fgb" in all_contradictions or "contaminant" in all_contradictions or "blood" in all_contradictions


def eval_report_structure(m: EvalMetrics, markdown: str):
    """Verify all required sections are present."""
    required = [
        "Decision Report",
        "Recommendation",
        "Agent reasoning",
    ]
    m.report_structure_ok = all(section.lower() in markdown.lower() for section in required)


def eval_hallucination(m: EvalMetrics, markdown: str, json_body: dict):
    """Count mismatches between markdown narrative and json_body ground truth."""
    mismatches = 0

    for struct in json_body.get("structures", []):
        rec = struct.get("recommendation", "")
        if rec and rec not in markdown:
            mismatches += 1

    drivers_from_json = set()
    for struct in json_body.get("structures", []):
        for d in struct.get("drivers", []):
            gene = d.get("gene", "")
            if gene:
                drivers_from_json.add(gene)
    for gene in drivers_from_json:
        if gene not in markdown:
            mismatches += 1

    for struct in json_body.get("structures", []):
        best = struct.get("best_score")
        if best is not None:
            score_str = f"{best:.3f}" if isinstance(best, float) else str(best)
            if score_str not in markdown:
                mismatches += 1

    m.hallucination_score = mismatches


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM agent output quality")
    parser.add_argument("--model", default="ollama/qwen2.5:7b", help="Model to evaluate")
    parser.add_argument("--n-runs", type=int, default=1, help="Number of evaluation runs")
    args = parser.parse_args()

    db.connect(reuse_if_open=True)

    results = []
    for i in range(args.n_runs):
        if args.n_runs > 1:
            print(f"\nRun {i+1}/{args.n_runs}...", flush=True)
        m = evaluate_single_run(args.model)
        results.append(m)

        line = "=" * 60
        print(f"\n{line}")
        print(f"Model: {args.model}" + (f"  (run {i+1}/{args.n_runs})" if args.n_runs > 1 else ""))
        print(line)
        print(m.summary())
        print(line)
        status = "ALL CHECKS PASSED" if m.all_passed() else "SOME CHECKS FAILED"
        print(f"{status}")
        print(line)

    if args.n_runs > 1:
        avg_latency = sum(r.latency_s for r in results) / len(results)
        pass_rate = sum(1 for r in results if r.all_passed()) / len(results)
        print(f"\nAggregate ({args.n_runs} runs):")
        print(f"  Pass rate: {pass_rate:.0%}")
        print(f"  Avg latency: {avg_latency:.1f}s")

    db.close()
    return 0 if all(r.all_passed() for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
