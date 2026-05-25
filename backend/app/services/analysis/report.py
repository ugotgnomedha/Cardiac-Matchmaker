"""Deterministic, cited Decision Report: ranking + grounded drivers + caveats, as markdown/JSON."""

import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.analysis import constants as C


def _snippet_around(text: str, gene: str, width: int = 160) -> str:
    """A readable excerpt centred on the gene mention so the citation shows context."""
    m = re.search(rf"\b{re.escape(gene)}\b", text, re.IGNORECASE)
    start = 0 if not m else max(0, m.start() - width // 3)
    excerpt = text[start : start + width]
    if start > 0 and " " in excerpt:
        excerpt = excerpt.split(" ", 1)[1]
    if start + width < len(text) and " " in excerpt:
        excerpt = excerpt.rsplit(" ", 1)[0]
    return ("…" if start > 0 else "") + excerpt.strip() + ("…" if start + width < len(text) else "")


@dataclass
class DriverEvidence:
    """One driver protein and where its function is grounded."""

    gene: str
    contribution: float
    matrisome_category: Optional[str]
    uniprot_class: str
    function: str
    source: str
    page: Optional[int] = None
    pmids: list[str] = field(default_factory=list)
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None

    @property
    def is_contaminant(self) -> bool:
        """Whether the UniProt class flags this driver as a likely contaminant."""
        return "contaminant" in self.uniprot_class


@dataclass
class StructureDecision:
    """The recommendation and supporting evidence for one heart structure."""

    structure: str
    use_case: str
    recommendation: str
    best_score: float
    runner_up: str
    runner_up_score: float
    margin: float
    ranking: list[tuple[str, float]]
    drivers: list[DriverEvidence]
    caveats: list[str]


@dataclass
class DecisionReport:
    """The full report across the requested structures, renderable to JSON/markdown."""

    method: str
    n_anchor_proteins: int
    alignment_quality: list[float]
    matrisome_only: bool
    structures: list[StructureDecision]

    def to_json(self) -> dict:
        """Serialise the report to a JSON-ready dict."""
        return {
            "method": self.method,
            "n_anchor_proteins": self.n_anchor_proteins,
            "alignment_quality": self.alignment_quality,
            "matrisome_only": self.matrisome_only,
            "structures": [
                {
                    "structure": s.structure,
                    "use_case": s.use_case,
                    "recommendation": s.recommendation,
                    "best_score": s.best_score,
                    "runner_up": s.runner_up,
                    "runner_up_score": s.runner_up_score,
                    "margin": s.margin,
                    "ranking": [{"prep": p, "score": v} for p, v in s.ranking],
                    "drivers": [
                        {
                            "gene": d.gene,
                            "contribution": d.contribution,
                            "matrisome_category": d.matrisome_category,
                            "uniprot_class": d.uniprot_class,
                            "function": d.function,
                            "source": d.source,
                            "page": d.page,
                            "pmids": d.pmids,
                        }
                        for d in s.drivers
                    ],
                    "caveats": s.caveats,
                }
                for s in self.structures
            ],
        }

    def to_markdown(self) -> str:
        """Render the report as a cited markdown document."""
        L: list[str] = ["# Cardiac Matchmaker — Decision Report"]
        L.append(
            f"\n*Alignment*: {self.method.upper()} domain adaptation on "
            f"{self.n_anchor_proteins} anchor proteins"
            f"{' (matrisome/ECM only)' if self.matrisome_only else ''}; "
            f"alignment quality {self.alignment_quality}. Scores are similarities in the "
            "aligned latent space — cross-dataset PATTERNS, not absolute abundances."
        )
        for s in self.structures:
            L.append(f"\n## {s.structure}  —  {s.use_case}")
            thin = "  ⚠ thin margin" if s.margin < 0.01 else ""
            L.append(
                f"\n**Recommendation: {s.recommendation}** "
                f"(aligned cosine {s.best_score:.3f}; runner-up {s.runner_up} "
                f"{s.runner_up_score:.3f}, margin {s.margin:.3f}{thin})."
            )
            L.append("\nRanking: " + ", ".join(f"{p} {v:.3f}" for p, v in s.ranking))
            L.append(f"\nDriver proteins ({s.recommendation} → {s.structure}):")
            L.append("\n| Protein | Matrisome cat. | UniProt class | Function (literature → UniProt) |")
            L.append("|---|---|---|---|")
            for d in s.drivers:
                cat = d.matrisome_category or "—"
                L.append(f"| {d.gene} | {cat} | {d.uniprot_class} | {d.function} |")
            if s.caveats:
                L.append("\nCaveats:")
                L.extend(f"- {c}" for c in s.caveats)
        return "\n".join(L)


def _annotate(gene: str, retriever, uniprot, cache: dict) -> dict:
    """Ground a driver gene: literature first, UniProt fallback, plus its class."""
    if gene in cache:
        return cache[gene]

    hit = uniprot.lookup(gene) if uniprot else None
    uclass = hit.category() if hit else "unknown"

    passages = retriever.protein_function(gene, k=1) if retriever else None
    if passages:
        p = passages[0]
        info = {
            "function": f"p.{p.page}: {_snippet_around(p.text, gene)}",
            "source": "literature",
            "page": p.page,
            "pmids": [],
            "document_id": p.document_id,
            "chunk_id": p.chunk_id,
        }
    elif hit:
        info = {
            "function": hit.cite(),
            "source": "uniprot",
            "page": None,
            "pmids": list(hit.pubmed),
            "document_id": None,
            "chunk_id": None,
        }
    else:
        info = {
            "function": "not named in the project literature or UniProt",
            "source": "none",
            "page": None,
            "pmids": [],
            "document_id": None,
            "chunk_id": None,
        }
    info["uniprot_class"] = uclass
    cache[gene] = info
    return info


def _structure_decision(
    alignment, structure: str, *, retriever, uniprot, n_drivers: int, cache: dict
) -> StructureDecision:
    """Build the ranking, drivers, and caveats for one structure."""
    ranking = alignment.score_matrix()[structure].sort_values(ascending=False)
    best, runner = ranking.index[0], ranking.index[1]
    best_score, runner_score = float(ranking.iloc[0]), float(ranking.iloc[1])
    margin = best_score - runner_score

    drivers: list[DriverEvidence] = []
    driver_rows = alignment.drivers(best, structure, top=n_drivers)
    for _, row in driver_rows.iterrows():
        gene = row["GeneName"]
        info = _annotate(gene, retriever, uniprot, cache)
        drivers.append(
            DriverEvidence(
                gene=gene,
                contribution=float(row["contribution"]),
                matrisome_category=(row["MatrisomeCategory"] or None),
                uniprot_class=info["uniprot_class"],
                function=info["function"],
                source=info["source"],
                page=info["page"],
                pmids=info["pmids"],
                document_id=info["document_id"],
                chunk_id=info["chunk_id"],
            )
        )

    caveats = ["Scores are cross-dataset patterns in the aligned space, not absolute abundances."]
    if margin < 0.01:
        caveats.append(
            f"Recommendation margin is thin (<0.01); runner-up {runner} is nearly tied."
        )
    contaminants = [d.gene for d in drivers if d.is_contaminant]
    if contaminants:
        caveats.append(
            "Top drivers flagged as likely blood/plasma or intracellular contaminants "
            f"rather than structural ECM: {', '.join(contaminants)}."
        )

    return StructureDecision(
        structure=structure,
        use_case=C.USE_CASE.get(structure, structure),
        recommendation=best,
        best_score=round(best_score, 3),
        runner_up=runner,
        runner_up_score=round(runner_score, 3),
        margin=round(margin, 3),
        ranking=[(p, round(float(v), 3)) for p, v in ranking.items()],
        drivers=drivers,
        caveats=caveats,
    )


def build_report(
    alignment,
    structures: list[str],
    *,
    retriever=None,
    uniprot=None,
    n_drivers: int = 5,
    matrisome_only: bool = False,
) -> DecisionReport:
    """Assemble the Decision Report for the requested heart structures."""
    cache: dict = {}
    decisions = [
        _structure_decision(
            alignment, s, retriever=retriever, uniprot=uniprot, n_drivers=n_drivers, cache=cache
        )
        for s in structures
    ]
    return DecisionReport(
        method=alignment.method,
        n_anchor_proteins=len(alignment.proteins),
        alignment_quality=list(alignment.quality),
        matrisome_only=matrisome_only,
        structures=decisions,
    )
