"""End-to-end pipeline test (requires Postgres; runs offline with no UniProt network or Qdrant)."""

import os
import sys
from uuid import uuid4

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.evidence.evidence_model import ContradictionWarning, EvidenceItem
from app.models.feature.feature_model import FeatureAnnotation
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun, AnalysisStep, CandidateMatch
from app.models.sample.sample_model import Measurement, Sample
from app.services.analysis import constants as C
from app.services.analysis.pipeline import AnalysisService


class _NoUniProt:
    """UniProt stub that never resolves a gene (keeps the test offline)."""

    def lookup(self, gene):
        """Always return None."""
        return None


def _seed_proteome(project, n_proteins: int = 24, seed: int = 0) -> DatasetVersion:
    """Seed a dataset version with a synthetic proteome carrying a cross-domain signal."""
    rng = np.random.default_rng(seed)
    dataset = Dataset.create(
        project=project,
        name="Merged",
        type="placenta_heart_merged",
        original_filename="m.tsv",
        storage_path="/tmp/m.tsv",
        metadata={},
    )
    version = DatasetVersion.create(
        dataset=dataset,
        version_number="1",
        status="normalized",
        storage_path="/tmp/m.tsv",
        preprocessing_config={},
    )

    placenta_cols = [c for cols in C.PLACENTA_PREPS.values() for c in cols]
    samples = {}
    for name in placenta_cols:
        samples[name] = Sample.create(
            id=uuid4(), dataset_version=version, name=name, type="placenta_region", metadata={}
        )
    for name in C.HEART_REGIONS:
        samples[name] = Sample.create(
            id=uuid4(), dataset_version=version, name=name, type="heart_region", metadata={}
        )

    latent = rng.normal(size=(n_proteins, 3))
    prep_loadings = rng.normal(size=(3, len(placenta_cols)))
    region_loadings = rng.normal(size=(3, len(C.HEART_REGIONS)))
    prep_vals = 4.5 + 1.2 * (latent @ prep_loadings) + 0.1 * rng.normal(size=(n_proteins, len(placenta_cols)))
    region_vals = 25.0 + 3.0 * (latent @ region_loadings) + 0.2 * rng.normal(size=(n_proteins, len(C.HEART_REGIONS)))

    categories = ["Collagens", "ECM Glycoproteins", "Proteoglycans"]
    for i in range(n_proteins):
        gene = f"GENE{i}"
        FeatureAnnotation.create(
            id=uuid4(),
            dataset_version=version,
            feature_name=gene,
            matrisome_division="Core matrisome",
            matrisome_category=categories[i % len(categories)],
            present_in_heart=True,
        )
        for j, name in enumerate(placenta_cols):
            Measurement.create(
                id=uuid4(), sample=samples[name], feature_name=gene,
                raw_value=float(prep_vals[i, j]), unit="log2 intensity",
            )
        for j, name in enumerate(C.HEART_REGIONS):
            Measurement.create(
                id=uuid4(), sample=samples[name], feature_name=gene,
                raw_value=float(region_vals[i, j]), unit="log2 intensity",
            )
    return version


def test_pipeline_persists_steps_candidates_evidence_and_report(service_context):
    """Running the pipeline persists steps, candidates, evidence, warnings, and a report."""
    project = service_context.create_project_model()
    _seed_proteome(project)
    run = AnalysisRun.create(
        id=uuid4(),
        project=project,
        status="running",
        query="best match for semilunar valve replacement",
        target_application="valve replacement",
        target_tissue="semilunar valve",
        constraints={"structure": "SL-Valves"},
    )

    service = AnalysisService(uniprot=_NoUniProt(), retriever_factory=lambda pid: None, n_drivers=4)
    report_row = service.run(run)

    steps = list(
        AnalysisStep.select()
        .where(AnalysisStep.analysis_run == run)
        .order_by(AnalysisStep.sequence_number)
    )
    assert [s.step_name for s in steps] == ["load_proteomics", "align", "build_report"]
    assert all(s.status == "completed" for s in steps)

    candidates = list(CandidateMatch.select().where(CandidateMatch.analysis_run == run))
    assert len(candidates) == len(C.PLACENTA_PREPS)
    assert {c.rank for c in candidates} == set(range(1, len(C.PLACENTA_PREPS) + 1))
    assert all(c.target_name == "SL-Valves" for c in candidates)
    assert all(c.method == "cca" for c in candidates)

    evidence = list(EvidenceItem.select().where(EvidenceItem.analysis_run == run))
    assert 1 <= len(evidence) <= 4

    warnings = list(ContradictionWarning.select().where(ContradictionWarning.analysis_run == run))
    assert any(w.warning_type == "interpretation" for w in warnings)

    report = Report.get(Report.analysis_run == run)
    assert report.status == "ready"
    assert report.json_body["structures"][0]["structure"] == "SL-Valves"
    assert "Decision Report" in report.markdown_body
    assert report_row.id == report.id
