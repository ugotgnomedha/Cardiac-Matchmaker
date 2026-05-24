import os

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.document.document_model import Document, DocumentChunk
from app.models.evidence.evidence_model import ContradictionWarning, EvidenceItem
from app.models.job.job_model import ProcessingJob
from app.models.project.project_model import ResearchProject
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun, AnalysisStep, CandidateMatch


def ensure_schema() -> None:
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()


def test_dataset_creation():
    ensure_schema()
    project = None
    try:
        project = ResearchProject.create(name="Test Project", description="For MVP testing")

        file_path = "../../data/datasets/placenta_annotated_forAnalysis.txt"
        abs_path = os.path.abspath(file_path)

        dataset = Dataset.create(
            project=project,
            name="Placenta + Heart merged proteomics",
            type="placenta_heart_merged",
            original_filename="placenta_annotated_forAnalysis.txt",
            storage_path=abs_path,
            metadata={"rows": 1234, "columns": 32, "delimiter": "tab"},
        )
        version = DatasetVersion.create(
            dataset=dataset,
            version_number="1",
            status="raw",
            storage_path=abs_path,
            preprocessing_config={},
        )

        fetched_dataset = Dataset.get_by_id(dataset.id)

        assert fetched_dataset.name == dataset.name
        assert version.dataset.id == dataset.id
    finally:
        if project is not None:
            project.delete_instance(recursive=True)
        db.close()


def test_phase_one_persistence_trace_creation():
    ensure_schema()
    project = None
    job = None
    try:
        project = ResearchProject.create(name="Trace Project", description="End-to-end schema smoke test")
        dataset = Dataset.create(
            project=project,
            name="Placenta proteomics",
            type="placenta",
            original_filename="placenta.tsv",
            storage_path="/data/raw/placenta.tsv",
            metadata={"delimiter": "tab"},
        )
        version = DatasetVersion.create(
            dataset=dataset,
            version_number="1",
            status="normalized",
            storage_path="/data/processed/placenta_normalized.tsv",
            preprocessing_config={"method": "z_score_by_dataset"},
        )
        document = Document.create(
            project=project,
            title="Heart Map",
            original_filename="heart-map.pdf",
            storage_path="/data/pdfs/heart-map.pdf",
            status="indexed",
            metadata={"paper": "Doll et al."},
        )
        chunk = DocumentChunk.create(
            document=document,
            chunk_index=0,
            page_number=12,
            text="Extracellular matrix proteins support cardiac tissue mechanics.",
            vector_id="heart-map:0",
            metadata={"section": "results"},
        )
        run = AnalysisRun.create(
            project=project,
            status="running",
            query="Find the best placental material for myocardial patch support.",
            target_application="myocardial patch",
            target_tissue="left ventricle",
            constraints={"max_candidates": 5},
        )
        step = AnalysisStep.create(
            analysis_run=run,
            sequence_number=1,
            step_name="alignment",
            status="done",
            input_snapshot={"dataset_version_id": str(version.id)},
            output_snapshot={"method": "z_score_common_features_cosine_v1"},
        )
        candidate = CandidateMatch.create(
            analysis_run=run,
            dataset_version=version,
            rank=1,
            candidate_name="Amnion",
            target_name="left ventricle",
            score=0.78,
            method="z_score_common_features_cosine_v1",
            features_used=421,
            metadata={"scale_handling": "z_score_each_source"},
        )
        evidence = EvidenceItem.create(
            analysis_run=run,
            candidate_match=candidate,
            candidate_name="Amnion",
            claim="Candidate has extracellular matrix support relevant to myocardial patch use.",
            document=document,
            document_chunk=chunk,
            support_label="supports",
            score=0.82,
            metadata={"retrieval_query": "Amnion myocardial extracellular matrix"},
        )
        warning = ContradictionWarning.create(
            analysis_run=run,
            candidate_match=candidate,
            candidate_name="Amnion",
            warning_type="unsupported_numeric_match",
            severity="warning",
            message="Ranking should be reviewed if literature evidence is sparse.",
            metadata={"rule": "alignment_score_without_multiple_sources"},
        )
        report = Report.create(
            analysis_run=run,
            status="draft",
            json_body={"top_candidate": "Amnion", "evidence_count": 1},
            markdown_body="# Draft report\n\nTop candidate: Amnion",
            storage_path="/data/reports/run.md",
        )
        job = ProcessingJob.create(
            job_type="analysis_run",
            status="queued",
            payload={"analysis_run_id": str(run.id)},
        )

        assert AnalysisRun.get_by_id(run.id).project.id == project.id
        assert AnalysisStep.get_by_id(step.id).analysis_run.id == run.id
        assert CandidateMatch.get_by_id(candidate.id).dataset_version.id == version.id
        assert EvidenceItem.get_by_id(evidence.id).document_chunk.id == chunk.id
        assert ContradictionWarning.get_by_id(warning.id).candidate_match.id == candidate.id
        assert Report.get_by_id(report.id).analysis_run.id == run.id
        assert ProcessingJob.get_by_id(job.id).payload["analysis_run_id"] == str(run.id)
    finally:
        if job is not None:
            job.delete_instance()
        if project is not None:
            project.delete_instance(recursive=True)
        db.close()

if __name__ == "__main__":
    test_dataset_creation()
