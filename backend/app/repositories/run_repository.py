from typing import Any
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.job.job_model import ProcessingJob
from app.models.project.project_model import ResearchProject
from app.models.run.run_model import AnalysisRun, AnalysisStep, CardiacApplicationQuery


class RunRepository:
    def create_application_query(
        self,
        *,
        project: ResearchProject,
        query_text: str,
        target_application: str,
        target_tissue: str,
        function_target: str | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> CardiacApplicationQuery:
        return CardiacApplicationQuery.create(
            id=uuid4(),
            project=project,
            query_text=query_text,
            target_application=target_application,
            target_tissue=target_tissue,
            function_target=function_target,
            constraints=constraints,
        )

    def create(
        self,
        *,
        project: ResearchProject,
        application_query: CardiacApplicationQuery,
        status: str = "queued",
        selected_config: dict[str, Any] | None = None,
    ) -> AnalysisRun:
        return AnalysisRun.create(
            id=uuid4(),
            project=project,
            application_query=application_query,
            status=status,
            selected_config=selected_config,
        )

    def create_with_query(
        self,
        *,
        project: ResearchProject,
        query_text: str,
        target_application: str,
        target_tissue: str,
        function_target: str | None = None,
        constraints: dict[str, Any] | None = None,
        selected_config: dict[str, Any] | None = None,
    ) -> AnalysisRun:
        with db.atomic():
            application_query = self.create_application_query(
                project=project,
                query_text=query_text,
                target_application=target_application,
                target_tissue=target_tissue,
                function_target=function_target,
                constraints=constraints,
            )
            return self.create(
                project=project,
                application_query=application_query,
                selected_config=selected_config,
            )

    def create_with_query_and_job(
        self,
        *,
        project: ResearchProject,
        query_text: str,
        target_application: str,
        target_tissue: str,
        function_target: str | None = None,
        constraints: dict[str, Any] | None = None,
        selected_config: dict[str, Any] | None = None,
    ) -> AnalysisRun:
        with db.atomic():
            run = self.create_with_query(
                project=project,
                query_text=query_text,
                target_application=target_application,
                target_tissue=target_tissue,
                function_target=function_target,
                constraints=constraints,
                selected_config=selected_config,
            )
            ProcessingJob.create(
                id=uuid4(),
                job_type="analysis_run",
                status="queued",
                payload={
                    "analysis_run_id": str(getattr(run, "id")),
                    "project_id": str(getattr(project, "id")),
                },
            )
            return run

    def list_for_project(self, project_id: UUID) -> list[AnalysisRun]:
        return list(
            AnalysisRun.select()
            .join(CardiacApplicationQuery)
            .switch(AnalysisRun)
            .where(AnalysisRun.project == project_id)
            .order_by(AnalysisRun.created_at.desc())
        )

    def get(self, run_id: UUID) -> AnalysisRun | None:
        return AnalysisRun.get_or_none(AnalysisRun.id == run_id)

    def update(self, run: AnalysisRun, values: dict[str, Any]) -> AnalysisRun:
        for field_name, value in values.items():
            setattr(run, field_name, value)

        with db.atomic():
            run.save()
        return run

    def delete(self, run: AnalysisRun) -> int:
        with db.atomic():
            return run.delete_instance(recursive=True)

    def list_steps(self, run_id: UUID) -> list[AnalysisStep]:
        return list(
            AnalysisStep.select()
            .where(AnalysisStep.analysis_run == run_id)
            .order_by(AnalysisStep.sequence_number.asc(), AnalysisStep.created_at.asc())
        )
