from typing import Any
from uuid import UUID

from app.models.base.base_model import db
from app.models.evidence.evidence_model import EvidenceItem
from app.models.run.run_model import AnalysisRun, CandidateMatch


class CandidateRepository:
    def create(self, *, analysis_run: AnalysisRun, **values: Any) -> CandidateMatch:
        with db.atomic():
            return CandidateMatch.create(analysis_run=analysis_run, **values)

    def list_for_run(self, run_id: UUID) -> list[CandidateMatch]:
        return list(
            CandidateMatch.select()
            .where(CandidateMatch.analysis_run == run_id)
            .order_by(CandidateMatch.target_name.asc(), CandidateMatch.rank.asc())
        )

    def get(self, candidate_id: UUID) -> CandidateMatch | None:
        return CandidateMatch.get_or_none(CandidateMatch.id == candidate_id)

    def update(self, candidate: CandidateMatch, values: dict[str, Any]) -> CandidateMatch:
        for field_name, value in values.items():
            setattr(candidate, field_name, value)

        with db.atomic():
            candidate.save()
        return candidate

    def delete(self, candidate: CandidateMatch) -> int:
        with db.atomic():
            return candidate.delete_instance(recursive=True)


class EvidenceRepository:
    def create(self, *, analysis_run: AnalysisRun, **values: Any) -> EvidenceItem:
        with db.atomic():
            return EvidenceItem.create(analysis_run=analysis_run, **values)

    def list_for_run(self, run_id: UUID) -> list[EvidenceItem]:
        return list(
            EvidenceItem.select()
            .where(EvidenceItem.analysis_run == run_id)
            .order_by(EvidenceItem.created_at.asc())
        )

    def get(self, evidence_id: UUID) -> EvidenceItem | None:
        return EvidenceItem.get_or_none(EvidenceItem.id == evidence_id)

    def update(self, evidence_item: EvidenceItem, values: dict[str, Any]) -> EvidenceItem:
        for field_name, value in values.items():
            setattr(evidence_item, field_name, value)

        with db.atomic():
            evidence_item.save()
        return evidence_item

    def delete(self, evidence_item: EvidenceItem) -> int:
        with db.atomic():
            return evidence_item.delete_instance(recursive=True)
