import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject
from app.models.dataset.dataset_model import Dataset, DatasetVersion

def test_dataset_creation():
    db.connect(reuse_if_open=True)
    db.create_tables([ResearchProject, Dataset, DatasetVersion], safe=True)

    # Create a research project
    project = ResearchProject.create(name="Test Project", description="For MVP testing")
    print(f"Created project: {project.id} - {project.name}")

    file_path = "../../data/datasets/placenta_annotated_forAnalysis.txt"
    abs_path = os.path.abspath(file_path)
    print(f"Using file: {abs_path}")

    # Create a dataset
    dataset = Dataset.create(
        project=project,
        name="Placenta + Heart merged proteomics",
        type="placenta_heart_merged",
        original_filename="placenta_annotated_forAnalysis.txt",
        storage_path=abs_path,
        metadata={"rows": 1234, "columns": 32, "delimiter": "tab"}
    )
    print(f"Created dataset: {dataset.id} - {dataset.name}")

    # Create a raw version
    version = DatasetVersion.create(
        dataset=dataset,
        version_number="1",
        status="raw",
        storage_path=abs_path,
        preprocessing_config={}
    )
    print(f"Created version: {version.id} for dataset {dataset.id}")

    # Verify we can read it back
    fetched_dataset = Dataset.get_by_id(dataset.id)
    assert fetched_dataset.name == dataset.name
    print("Dataset retrieved successfully")

    # Clean up
    version.delete_instance()
    dataset.delete_instance()
    project.delete_instance()

    db.close()
    print("Test passed!")

if __name__ == "__main__":
    test_dataset_creation()