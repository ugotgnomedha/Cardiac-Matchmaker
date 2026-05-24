import io
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.preprocessing.preprocessing_run_model import PreprocessingRun
from app.models.sample.sample_model import Sample, Measurement
from app.services.data_preparation.data_preparation_service import DataPreparationService

TEST_TSV_CONTENT = """GeneName\tUniProt\tLocation\tMatrisomeDivision\tMatrisomeCategory\tAmnion_decell_1\tUmbilicalCord_native_1\tlargeArtery
IGLV3\tA0A075B6K5\tNA\tNA\tNA\t4.38087\t5.79614\t26.79953
IGHV3\tA0A0A0MS15\tNA\tNA\tNA\t4.7168\t5.6076\t27.054565
"""

def test_ingest_tsv_creates_samples_and_measurements():
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()

    # Create a project, dataset, and version
    project = ResearchProject.create(name="Ingestion Test Project")
    dataset = Dataset.create(
        project=project,
        name="Test Dataset",
        type="placenta_heart_merged",
        original_filename="test.tsv",
        storage_path="/tmp/test.tsv",
        metadata={},
    )
    version = DatasetVersion.create(
        dataset=dataset,
        version_number="1",
        status="raw",
        storage_path="/tmp/test.tsv",
        preprocessing_config={},
    )

    # Write test TSV to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as tmp:
        tmp.write(TEST_TSV_CONTENT)
        tmp_path = Path(tmp.name)

    try:
        service = DataPreparationService()
        run = service.ingest_dataset_version(version.id, tmp_path)  # pyrefly: ignore

        # Check preprocessing run status
        assert run.status == "completed"
        assert run.error_message is None

        # Check samples created
        samples = Sample.select().where(Sample.dataset_version == version)
        sample_names = {s.name for s in samples}
        expected_samples = {"Amnion_decell_1", "UmbilicalCord_native_1", "largeArtery"}
        assert sample_names == expected_samples

        # Check sample types
        for s in samples:
            if s.name == "largeArtery":
                assert s.type == "heart_region"
            else:
                assert s.type == "placenta_region"

        # Check measurements
        for s in samples:
            measurements = list(Measurement.select().where(Measurement.sample == s))
            if s.name == "Amnion_decell_1":
                assert len(measurements) == 2
                values = {m.raw_value for m in measurements}
                assert 4.38087 in values
                assert 4.7168 in values
            elif s.name == "UmbilicalCord_native_1":
                assert len(measurements) == 2
                values = {m.raw_value for m in measurements}
                assert 5.79614 in values
                assert 5.6076 in values
            elif s.name == "largeArtery":
                assert len(measurements) == 2
                values = {m.raw_value for m in measurements}
                assert 26.79953 in values
                assert 27.054565 in values

        # Check dataset version status updated
        version = DatasetVersion.get_by_id(version.id)
        assert version.status == "normalized"

        print("Data preparation test passed.")
    finally:
        # Clean up
        project.delete_instance(recursive=True)
        tmp_path.unlink(missing_ok=True)
        db.close()

if __name__ == "__main__":
    test_ingest_tsv_creates_samples_and_measurements()