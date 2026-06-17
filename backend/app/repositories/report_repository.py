from typing import Any
from uuid import UUID

from app.models.base.base_model import db
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun


class ReportRepository:
    def create(self, *, analysis_run: AnalysisRun, **values: Any) -> Report:
        with db.atomic():
            return Report.create(analysis_run=analysis_run, **values)

    def list_for_run(self, run_id: UUID) -> list[Report]:
        return list(
            Report.select()
            .where(Report.analysis_run == run_id)
            .order_by(Report.created_at.desc())
        )

    def get_latest_for_run(self, run_id: UUID) -> Report | None:
        return (
            Report.select()
            .where(Report.analysis_run == run_id)
            .order_by(Report.created_at.desc())
            .first()
        )

    def get(self, report_id: UUID) -> Report | None:
        return Report.get_or_none(Report.id == report_id)

    def update(self, report: Report, values: dict[str, Any]) -> Report:
        for field_name, value in values.items():
            setattr(report, field_name, value)

        with db.atomic():
            report.save()
        return report

    def delete(self, report: Report) -> int:
        with db.atomic():
            return report.delete_instance(recursive=True)
