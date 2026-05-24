import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.sample.sample_model import Sample, Measurement

def test_sample_measurement_creation():
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()

    project = None
    try:
        # Create a project and a dataset version
        project = ResearchProject.create(name="Sample Test Project", description="Testing Sample & Measurement")
        dataset = Dataset.create(
            project=project,
            name="Placenta proteomics sample test",
            type="placenta",
            original_filename="dummy.txt",
            storage_path="/tmp/dummy.txt",
            metadata={},
        )
        version = DatasetVersion.create(
            dataset=dataset,
            version_number="1",
            status="raw",
            storage_path="/tmp/dummy.txt",
            preprocessing_config={},
        )

        # Create a sample
        sample = Sample.create(
            dataset_version=version,
            name="Amnion_native_1",
            type="placenta_region",
            metadata={"decellularized": False, "replicate": 1},
        )

        # Create a measurement
        measurement = Measurement.create(
            sample=sample,
            feature_name="COL1A1",
            raw_value=12.34,
            normalized_value=0.56,
            unit="log2 intensity",
        )

        # Verify relationships
        assert sample.id == measurement.sample.id
        assert sample.dataset_version.id == version.id

        samples_from_version = list(version.samples)  # pyrefly: ignore
        assert len(samples_from_version) == 1
        assert samples_from_version[0].id == sample.id

        measurements_from_sample = list(sample.measurements)  # pyrefly: ignore
        assert len(measurements_from_sample) == 1
        assert measurements_from_sample[0].id == measurement.id

        print("Sample and measurement test passed.")
    finally:
        if project is not None:
            project.delete_instance(recursive=True)
        db.close()

if __name__ == "__main__":
    test_sample_measurement_creation()