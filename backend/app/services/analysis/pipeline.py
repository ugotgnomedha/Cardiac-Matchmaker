"""End-to-end analysis pipeline: resolve inputs, run the engine, and persist run results."""

import datetime
from typing import Callable, Optional
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
        method: str = "cca",
        n_drivers: int = 5,
    ) -> None:
        """Wire up the (injectable) loader, UniProt client, and retriever factory."""
        self.loader = loader or ProteomicsLoader()
        self._uniprot = uniprot
        self.retriever_factory = retriever_factory or _default_retriever_factory
        self.method = method
        self.n_drivers = n_drivers

    @property
    def uniprot(self):
        """The UniProt client, constructed lazily on first use."""
        if self._uniprot is None:
            self._uniprot = _default_uniprot()
        return self._uniprot

    def run(self, analysis_run) -> object:
        """Execute the full pipeline for a run and return its persisted Report."""
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
        self._step(
            analysis_run, 3, "build_report",
            {"structures": structures},
            lambda: self._build_and_persist(analysis_run, version_id, alignment, structures),
            lambda r: {"structures": [s.structure for s in r.structures]},
        )
        return self._report_row

    def _build_and_persist(self, analysis_run, version_id, alignment, structures):
        """Build the Decision Report (with grounding) and persist all its rows."""
        retriever = self.retriever_factory(getattr(analysis_run, "project_id"))
        report = report_builder.build_report(
            alignment,
            structures,
            retriever=retriever,
            uniprot=self.uniprot,
            n_drivers=self.n_drivers,
        )
        self._persist(analysis_run, version_id, report)
        return report

    def _persist(self, analysis_run, version_id, report) -> None:
        """Write candidate matches, evidence, warnings, and the report for a run."""
        from app.models.base.base_model import db
        from app.models.evidence.evidence_model import ContradictionWarning, EvidenceItem
        from app.models.report.report_model import Report
        from app.models.run.run_model import CandidateMatch

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

            self._report_row = Report.create(
                id=uuid4(),
                analysis_run=analysis_run,
                status="ready",
                json_body=report.to_json(),
                markdown_body=report.to_markdown(),
            )

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
            return [explicit]
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
            step.status = "failed"
            step.error_message = str(exc)
            step.finished_at = utc_now()
            step.save()
            raise
        step.status = "completed"
        step.output_snapshot = summarize(result)
        step.finished_at = utc_now()
        step.save()
        return result
