"""End-to-end analysis pipeline: resolve inputs, run the engine, and persist run results."""

import datetime
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

from app.services.analysis import alignment as align
from app.services.analysis import constants as C
from app.services.analysis import report as report_builder
from app.services.analysis.proteomics import ProteomicsLoader


def utc_now() -> datetime.datetime:
    """Current UTC time."""
    return datetime.datetime.now(datetime.timezone.utc)


class AnalysisError(Exception):
    """Raised when a run cannot be analysed (e.g. no dataset version)."""


def _default_retriever_factory(project_id: UUID):
    """Best-effort project retriever; None if no documents are indexed / Qdrant is down."""
    try:
        from app.services.analysis.rag_store import load_retriever

        retriever = load_retriever(project_id)
        return retriever if retriever.chunks else None
    except Exception:
        return None


def _default_uniprot():
    """Construct the default disk-cached UniProt client."""
    from app.services.analysis.uniprot import UniProt

    return UniProt()


def _warning_type(caveat: str) -> tuple[str, str]:
    """Map a caveat string to a (warning_type, severity) pair."""
    low = caveat.lower()
    if "thin" in low:
        return "thin_margin", "warning"
    if "contaminant" in low:
        return "contaminant_drivers", "warning"
    return "interpretation", "info"


class AnalysisService:
    """Runs the alignment/RAG/report pipeline for a run and persists its results."""

    def __init__(
        self,
        *,
        loader: Optional[ProteomicsLoader] = None,
        uniprot=None,
        retriever_factory: Optional[Callable[[UUID], object]] = None,
        chat_model=None,
        method: str = "cca",
        n_drivers: int = 5,
    ) -> None:
        """Wire up the (injectable) loader, UniProt client, retriever, and chat model."""
        self.loader = loader or ProteomicsLoader()
        self._uniprot = uniprot
        self.retriever_factory = retriever_factory or _default_retriever_factory
        self._chat_model = chat_model
        self.method = method
        self.n_drivers = n_drivers
        self._run_model_override = None

    @property
    def uniprot(self):
        """The UniProt client, constructed lazily on first use."""
        if self._uniprot is None:
            self._uniprot = _default_uniprot()
        return self._uniprot

    @property
    def chat_model(self):
        """The chat model, constructed lazily with optional per-run override."""
        if self._chat_model is None:
            from app.services.analysis.llm import build_chat_model

            self._chat_model = build_chat_model(self._run_model_override)
        return self._chat_model

    def run(self, analysis_run) -> Any:
        """Execute the full pipeline for a run and return its persisted Report."""
        config = getattr(analysis_run, "selected_config", None) or {}
        self._run_model_override = config.get("model")
        version_id = self._resolve_dataset_version(analysis_run)
        structures = self._resolve_structures(analysis_run)

        data = self._step(
            analysis_run, 1, "load_proteomics",
            {"dataset_version_id": str(version_id)},
            lambda: self.loader.load(version_id),
            lambda d: {"n_proteins": d.n_proteins, "n_heart_proteins": int(d.heart_matrix.shape[0])},
        )
        alignment = self._step(
            analysis_run, 2, "align",
            {"method": self.method},
            lambda: align.fit(data, method=self.method),
            lambda a: {"method": a.method, "n_anchor_proteins": len(a.proteins), "quality": list(a.quality)},
        )
        report = self._step(
            analysis_run, 3, "retrieve_and_ground",
            {"structures": structures, "n_drivers": self.n_drivers},
            lambda: self._ground_and_persist(analysis_run, version_id, alignment, structures),
            lambda r: {"recommendations": {s.structure: s.recommendation for s in r.structures}},
        )
        self._step(
            analysis_run, 4, "agent_reasoning",
            {"structures": structures},
            lambda: self._reason_and_persist(analysis_run, alignment, report, getattr(analysis_run, "query")),
            lambda res: {
                "approved": res.approved,
                "rounds": res.rounds,
                "contradictions": res.contradictions,
                "plan": res.plan,
            },
        )
        return self._report_row

    def _ground_and_persist(self, analysis_run, version_id, alignment, structures):
        """Build the deterministic Decision Report and persist its candidates/evidence/caveats."""
        from app.models.base.base_model import db
        from app.models.evidence.evidence_model import ContradictionWarning, EvidenceItem
        from app.models.run.run_model import CandidateMatch

        retriever = self.retriever_factory(getattr(analysis_run, "project_id"))
        report = report_builder.build_report(
            alignment,
            structures,
            retriever=retriever,
            uniprot=self.uniprot,
            n_drivers=self.n_drivers,
        )

        with db.atomic():
            for decision in report.structures:
                best_match = None
                for rank, (prep, score) in enumerate(decision.ranking, start=1):
                    match = CandidateMatch.create(
                        id=uuid4(),
                        analysis_run=analysis_run,
                        dataset_version=version_id,
                        rank=rank,
                        candidate_name=prep,
                        target_name=decision.structure,
                        score=score,
                        method=report.method,
                        features_used=report.n_anchor_proteins,
                        metadata={"use_case": decision.use_case},
                    )
                    if prep == decision.recommendation:
                        best_match = match

                for driver in decision.drivers:
                    EvidenceItem.create(
                        id=uuid4(),
                        analysis_run=analysis_run,
                        candidate_match=best_match,
                        candidate_name=decision.recommendation,
                        claim=f"{driver.gene}: {driver.function}",
                        document=UUID(driver.document_id) if driver.document_id else None,
                        document_chunk=UUID(driver.chunk_id) if driver.chunk_id else None,
                        support_label="supporting",
                        score=driver.contribution,
                        metadata={
                            "structure": decision.structure,
                            "gene": driver.gene,
                            "source": driver.source,
                            "page": driver.page,
                            "pmids": driver.pmids,
                            "uniprot_class": driver.uniprot_class,
                            "matrisome_category": driver.matrisome_category,
                        },
                    )

                for caveat in decision.caveats:
                    warning_type, severity = _warning_type(caveat)
                    ContradictionWarning.create(
                        id=uuid4(),
                        analysis_run=analysis_run,
                        candidate_match=best_match,
                        candidate_name=decision.recommendation,
                        warning_type=warning_type,
                        severity=severity,
                        message=caveat,
                        metadata={"structure": decision.structure},
                    )

        return report

    def _reason_and_persist(self, analysis_run, alignment, report, query):
        """Run the agent loop over the grounded report, persisting its warnings and report."""
        from app.models.base.base_model import db
        from app.models.evidence.evidence_model import ContradictionWarning
        from app.models.report.report_model import Report
        from app.services.analysis.agent import AgentContext, run_agent

        context = AgentContext(llm=self.chat_model, alignment=alignment, decision_report=report)
        result = run_agent(context, query or "")

        with db.atomic():
            for contradiction in result.contradictions:
                ContradictionWarning.create(
                    id=uuid4(),
                    analysis_run=analysis_run,
                    candidate_name=report.structures[0].recommendation if report.structures else None,
                    warning_type="agent_contradiction",
                    severity="warning",
                    message=str(contradiction),
                    metadata={"source": "agent_critic"},
                )
            if result.notes:
                ContradictionWarning.create(
                    id=uuid4(),
                    analysis_run=analysis_run,
                    warning_type="agent_caveat",
                    severity="info",
                    message=result.notes,
                    metadata={"source": "agent_critic"},
                )

            json_body = report.to_json()
            json_body["agent"] = {
                "plan": result.plan,
                "approved": result.approved,
                "rounds": result.rounds,
                "contradictions": result.contradictions,
                "notes": result.notes,
            }
            self._report_row = Report.create(
                id=uuid4(),
                analysis_run=analysis_run,
                status="ready",
                json_body=json_body,
                markdown_body=result.report,
            )
        return result

    def _resolve_dataset_version(self, analysis_run) -> UUID:
        """Pick the project's latest normalized dataset version (else its latest)."""
        from app.models.dataset.dataset_model import Dataset, DatasetVersion

        project_id = getattr(analysis_run, "project_id")
        base = (
            DatasetVersion.select(DatasetVersion)
            .join(Dataset)
            .where(Dataset.project == project_id)
        )
        version = (
            base.where(DatasetVersion.status == "normalized")
            .order_by(DatasetVersion.created_at.desc())
            .first()
            or base.order_by(DatasetVersion.created_at.desc()).first()
        )
        if version is None:
            raise AnalysisError(f"no dataset version found for project {project_id}")
        return getattr(version, "id")

    def _resolve_structures(self, analysis_run) -> list[str]:
        """Resolve the run's target structure(s) from constraints or free-text."""
        constraints = getattr(analysis_run, "constraints", None) or {}
        explicit = constraints.get("structure")
        if explicit in C.HEART_REGIONS:
            return [str(explicit)]
        listed = constraints.get("structures")
        if isinstance(listed, list):
            valid = [s for s in listed if s in C.HEART_REGIONS]
            if valid:
                return valid
        matched = C.match_structure(
            getattr(analysis_run, "target_tissue", None),
            getattr(analysis_run, "target_application", None),
            getattr(analysis_run, "query", None),
        )
        return [matched] if matched else list(C.HEART_REGIONS)

    def _step(self, analysis_run, sequence, name, input_snapshot, work, summarize):
        """Run one stage inside an AnalysisStep, recording its in/out and failures."""
        from app.models.run.run_model import AnalysisStep

        step = AnalysisStep.create(
            id=uuid4(),
            analysis_run=analysis_run,
            sequence_number=sequence,
            step_name=name,
            status="running",
            input_snapshot=input_snapshot,
            started_at=utc_now(),
        )
        try:
            result = work()
        except Exception as exc:
            step.status = "failed"  # pyrefly: ignore
            step.error_message = str(exc)  # pyrefly: ignore
            step.finished_at = utc_now()  # pyrefly: ignore
            step.save()
            raise
        step.status = "completed"  # pyrefly: ignore
        step.output_snapshot = summarize(result)
        step.finished_at = utc_now()  # pyrefly: ignore
        step.save()
        return result
