"""Load a dataset version's proteomes into the matrices the alignment engine consumes."""

from dataclasses import dataclass
from typing import Iterable, Mapping
from uuid import UUID

import numpy as np
import pandas as pd

from app.services.analysis import constants as C


@dataclass
class ProteomicsData:
    """Prep matrix, heart matrix, and matrisome annotation for one dataset version."""

    prep_matrix: pd.DataFrame
    heart_matrix: pd.DataFrame
    annotation: pd.DataFrame

    @property
    def n_proteins(self) -> int:
        """Number of proteins in the prep matrix."""
        return int(self.prep_matrix.shape[0])


def build_matrices(
    measurements: Iterable[tuple[str, str, float]],
    *,
    present_in_heart: set[str],
    matrisome_division: Mapping[str, str | None],
    matrisome_category: Mapping[str, str | None],
) -> ProteomicsData:
    """Assemble prep/heart matrices + annotation from ``(sample, gene, value)`` rows."""
    frame = pd.DataFrame(measurements, columns=["sample", "feature", "value"])
    if frame.empty:
        empty = pd.DataFrame()
        return ProteomicsData(empty, empty, empty)

    profiles = frame.groupby(["feature", "sample"])["value"].mean().unstack("sample")

    prep_matrix = pd.DataFrame(
        {
            prep: profiles[present].mean(axis=1)
            for prep, replicates in C.PLACENTA_PREPS.items()
            if (present := [r for r in replicates if r in profiles.columns])
        }
    ).reindex(columns=list(C.PLACENTA_PREPS))

    heart_cols = [r for r in C.HEART_REGIONS if r in profiles.columns]
    heart_present = profiles.index[profiles.index.isin(present_in_heart)]
    heart_matrix = profiles.loc[heart_present, heart_cols].reindex(columns=C.HEART_REGIONS)

    proteins = prep_matrix.index
    annotation = pd.DataFrame(
        {
            "GeneName": proteins,
            "MatrisomeDivision": [matrisome_division.get(p) for p in proteins],
            "MatrisomeCategory": [matrisome_category.get(p) for p in proteins],
        },
        index=proteins,
    )

    return ProteomicsData(prep_matrix, heart_matrix, annotation)


class ProteomicsLoader:
    """Read a dataset version's samples/measurements/annotation from the database."""

    def load(self, dataset_version_id: UUID) -> ProteomicsData:
        """Query the dataset version's rows and build its ProteomicsData."""
        from app.models.feature.feature_model import FeatureAnnotation
        from app.models.sample.sample_model import Measurement, Sample

        rows: list[tuple[str, str, float]] = []
        query = (
            Measurement.select(Measurement, Sample)
            .join(Sample)
            .where(Sample.dataset_version == dataset_version_id)
        )
        for measurement in query:
            value = measurement.normalized_value
            if value is None:
                value = measurement.raw_value
            rows.append((measurement.sample.name, measurement.feature_name, float(value)))

        annotations = list(
            FeatureAnnotation.select().where(
                FeatureAnnotation.dataset_version == dataset_version_id
            )
        )
        present_in_heart = {a.feature_name for a in annotations if a.present_in_heart}
        matrisome_division = {a.feature_name: a.matrisome_division for a in annotations}
        matrisome_category = {a.feature_name: a.matrisome_category for a in annotations}

        return build_matrices(
            rows,
            present_in_heart=present_in_heart,
            matrisome_division=matrisome_division,
            matrisome_category=matrisome_category,
        )
