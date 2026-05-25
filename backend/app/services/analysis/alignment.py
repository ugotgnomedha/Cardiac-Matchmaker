"""Domain-adaptation alignment (CCA/Procrustes) and cosine match scoring of the proteomes."""

import warnings
from dataclasses import dataclass

import numpy as np

warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
import pandas as pd
from scipy.linalg import orthogonal_procrustes
from sklearn.cross_decomposition import CCA
from sklearn.decomposition import PCA

from app.services.analysis.proteomics import ProteomicsData


def _zscore(frame: pd.DataFrame) -> np.ndarray:
    """Column-wise z-score as a numpy array."""
    return ((frame - frame.mean(0)) / frame.std(0, ddof=0)).to_numpy()


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation between two vectors."""
    x, y = x - x.mean(), y - y.mean()
    return float(x @ y / np.sqrt((x @ x) * (y @ y)))


def _cosine_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity matrix between two sets of vectors."""
    An = A / np.linalg.norm(A, axis=1, keepdims=True)
    Bn = B / np.linalg.norm(B, axis=1, keepdims=True)
    return An @ Bn.T


@dataclass
class Alignment:
    """A fitted alignment with methods to score and explain prep-structure matches."""

    method: str
    quality: list[float]
    proteins: pd.Index
    Sp: np.ndarray
    Sc: np.ndarray
    Pabs: pd.DataFrame
    Habs: pd.DataFrame
    annotation: pd.DataFrame

    @property
    def preps(self) -> list[str]:
        """Placental preparation names."""
        return list(self.Pabs.columns)

    @property
    def regions(self) -> list[str]:
        """Heart structure names."""
        return list(self.Habs.columns)

    def _embed(self, weights: pd.Series, S: np.ndarray) -> np.ndarray:
        """Abundance-weighted centroid of proteins in the shared space."""
        w = np.clip(weights.to_numpy(), 0, None)
        w = w / w.sum()
        return w @ S

    def prep_embeddings(self) -> np.ndarray:
        """Each placental prep as a point in the shared space."""
        return np.vstack([self._embed(self.Pabs[p], self.Sp) for p in self.preps])

    def region_embeddings(self) -> np.ndarray:
        """Each heart structure as a point in the shared space."""
        return np.vstack([self._embed(self.Habs[r], self.Sc) for r in self.regions])

    def score_matrix(self) -> pd.DataFrame:
        """Prep x structure cosine similarity in the aligned latent space."""
        M = _cosine_matrix(self.prep_embeddings(), self.region_embeddings())
        return pd.DataFrame(M, index=self.preps, columns=self.regions)

    def best_match_per_region(self) -> pd.DataFrame:
        """Top-scoring prep per heart structure with its aligned cosine."""
        s = self.score_matrix()
        return pd.DataFrame({"best_prep": s.idxmax(), "aligned_cosine": s.max().round(3)})

    def drivers(self, prep: str, region: str, top: int = 10) -> pd.DataFrame:
        """Proteins pulling a prep toward a structure, ranked by contribution."""
        region_dir = self._embed(self.Habs[region], self.Sc)
        region_dir = region_dir / np.linalg.norm(region_dir)
        w = np.clip(self.Pabs[prep].to_numpy(), 0, None)
        w = w / w.sum()
        contrib = w * (self.Sp @ region_dir)
        out = pd.DataFrame(
            {
                "GeneName": self.annotation.loc[self.proteins, "GeneName"].to_numpy(),
                "MatrisomeCategory": self.annotation.loc[
                    self.proteins, "MatrisomeCategory"
                ].to_numpy(),
                "prep_abundance": self.Pabs[prep].round(2).to_numpy(),
                "contribution": np.round(contrib, 5),
            },
            index=self.proteins,
        )
        return out.sort_values("contribution", ascending=False).head(top)

    def translate(self, prep: str) -> pd.Series:
        """Project a placental prep into cardiac space and rank all structures."""
        pe = self._embed(self.Pabs[prep], self.Sp)
        re = self.region_embeddings()
        sims = _cosine_matrix(pe[None, :], re)[0]
        return pd.Series(sims, index=self.regions).sort_values(ascending=False).round(3)


def fit(data: ProteomicsData, method: str = "cca", n_components: int = 5) -> Alignment:
    """Fit the alignment on the proteins shared by both domains."""
    P, H = data.prep_matrix, data.heart_matrix

    common = H.index
    mask = P.loc[common].notna().all(axis=1) & H.notna().all(axis=1)
    idx = common[mask]
    if len(idx) < 3:
        raise ValueError(
            f"too few anchor proteins shared by both domains ({len(idx)}); "
            "cannot fit an alignment"
        )
    Pc, Hc = P.loc[idx], H.loc[idx]
    Xp, Xc = _zscore(Pc), _zscore(Hc)
    k = min(n_components, Xc.shape[1] - 1, Xp.shape[1] - 1)

    if method == "cca":
        model = CCA(n_components=k, max_iter=2000).fit(Xp, Xc)
        Sp, Sc = model.transform(Xp, Xc)
        quality = [round(_pearson(Sp[:, d], Sc[:, d]), 3) for d in range(k)]
    elif method == "procrustes":
        Ep = PCA(n_components=k, random_state=0).fit_transform(Xp)
        Ec = PCA(n_components=k, random_state=0).fit_transform(Xc)
        Ep /= np.linalg.norm(Ep)
        Ec /= np.linalg.norm(Ec)
        R, _ = orthogonal_procrustes(Ep, Ec)
        Sp, Sc = Ep @ R, Ec
        disparity = float(np.sum((Sp - Sc) ** 2) / np.sum(Sc**2))
        quality = [round(1.0 - disparity, 3)]
    else:
        raise ValueError(f"unknown method {method!r}")

    return Alignment(method, quality, idx, Sp, Sc, Pc, Hc, data.annotation)


def cross_domain_gain(alignment: Alignment) -> tuple[float, float]:
    """Cross-domain dim-1 correlation before vs after alignment."""
    before = abs(_pearson(_zscore(alignment.Pabs)[:, 0], _zscore(alignment.Habs)[:, 0]))
    after = abs(_pearson(alignment.Sp[:, 0], alignment.Sc[:, 0]))
    return round(before, 3), round(after, 3)
