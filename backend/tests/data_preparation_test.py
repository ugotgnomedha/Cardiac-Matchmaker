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
from app.models.feature.feature_model import FeatureAnnotation
from app.services.data_preparation.data_preparation_service import DataPreparationService

TEST_TSV_CONTENT = """GeneName\tUniProt\tLocation\tMatrisomeDivision\tMatrisomeCategory\tAmnion_decell_1\tUmbilicalCord_native_1\tlargeArtery
IGLV3\tA0A075B6K5\tNA\tNA\tNA\t4.38087\t5.79614\t26.79953
IGHV3\tA0A0A0MS15\tNA\tNA\tNA\t4.7168\t5.6076\t27.054565
"""

# Uses the "largeAtery" spelling from the real source file and carries
# match_in_heart + matrisome columns so annotation persistence is exercised.
ANNOTATED_TSV_CONTENT = """GeneName\tUniProt\tLocation\tMatrisomeDivision\tMatrisomeCategory\tmatch_in_heart\tAmnion_decell_1\tlargeAtery
COL1A1\tP02452\tECM\tCore matrisome\tCollagens\tTRUE\t5.1\t24.3
FGB\tP02675\tSecreted\tNA\tECM Glycoproteins\tFALSE\t3.2\t22.1
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


def test_ingest_tsv_persists_feature_annotation_and_heart_samples():
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()

    project = ResearchProject.create(name="Annotation Test Project")
    dataset = Dataset.create(
        project=project,
        name="Annotated Dataset",
        type="placenta_heart_merged",
        original_filename="annotated.tsv",
        storage_path="/tmp/annotated.tsv",
        metadata={},
    )
    version = DatasetVersion.create(
        dataset=dataset,
        version_number="1",
        status="raw",
        storage_path="/tmp/annotated.tsv",
        preprocessing_config={},
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as tmp:
        tmp.write(ANNOTATED_TSV_CONTENT)
        tmp_path = Path(tmp.name)

    try:
        run = DataPreparationService().ingest_dataset_version(version.id, tmp_path)  # pyrefly: ignore
        assert run.status == "completed"

        # The real heart column "largeAtery" must classify as a heart region.
        large_artery = Sample.get(
            (Sample.dataset_version == version) & (Sample.name == "largeAtery")
        )
        assert large_artery.type == "heart_region"

        annotations = {
            a.feature_name: a
            for a in FeatureAnnotation.select().where(FeatureAnnotation.dataset_version == version)
        }
        assert set(annotations) == {"COL1A1", "FGB"}

        col1a1 = annotations["COL1A1"]
        assert col1a1.uniprot == "P02452"
        assert col1a1.matrisome_category == "Collagens"
        assert col1a1.matrisome_division == "Core matrisome"
        assert col1a1.present_in_heart is True

        fgb = annotations["FGB"]
        assert fgb.matrisome_category == "ECM Glycoproteins"
        assert fgb.matrisome_division is None  # "NA" normalised away
        assert fgb.present_in_heart is False

        print("Feature annotation test passed.")
    finally:
        project.delete_instance(recursive=True)
        tmp_path.unlink(missing_ok=True)
        db.close()


if __name__ == "__main__":
    test_ingest_tsv_creates_samples_and_measurements()
    test_ingest_tsv_persists_feature_annotation_and_heart_samples()