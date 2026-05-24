import os
import sys
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.preprocessing.preprocessing_run_model import PreprocessingRun

def test_preprocessing_run_creation():
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()

    project = None
    try:
        project = ResearchProject.create(name="Preprocessing Test Project")
        dataset = Dataset.create(
            project=project,
            name="Test Dataset",
            type="placenta",
            original_filename="test.txt",
            storage_path="/tmp/test.txt",
            metadata={},
        )
        version = DatasetVersion.create(
            dataset=dataset,
            version_number="1",
            status="raw",
            storage_path="/tmp/test.txt",
            preprocessing_config={},
        )

        now = datetime.datetime.now(datetime.timezone.utc)

        run = PreprocessingRun.create(
            dataset_version=version,
            status="completed",
            config={"normalization": "z-score"},
            log_path="/logs/preprocess.log",
            started_at=now,
            finished_at=now,
        )

        assert run.dataset_version.id == version.id
        assert run.status == "completed"
        assert run.config["normalization"] == "z-score"

        runs_from_version = list(version.preprocessing_runs)  # pyrefly: ignore
        assert len(runs_from_version) == 1
        assert runs_from_version[0].id == run.id

        print("PreprocessingRun test passed.")
    finally:
        if project:
            project.delete_instance(recursive=True)
        db.close()

if __name__ == "__main__":
    test_preprocessing_run_creation()