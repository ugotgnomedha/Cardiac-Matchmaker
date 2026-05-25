"""Tools the reasoning agent uses: thin text views over the alignment, RAG, and UniProt."""


def match_scores_text(alignment) -> str:
    """Aligned best-match-per-structure table with alignment quality and anchor count."""
    return (
        f"alignment={alignment.method} quality={alignment.quality} "
        f"anchors={len(alignment.proteins)}\n"
        + alignment.best_match_per_region().to_string()
    )


def drivers_text(alignment, prep: str, region: str, top: int = 8) -> str:
    """Proteins driving the aligned match between a prep and a heart structure."""
    return alignment.drivers(prep, region, top=top).to_string(index=False)


def translate_text(alignment, prep: str) -> str:
    """Project a prep into cardiac space and rank all heart structures."""
    return alignment.translate(prep).to_string()


def protein_function_text(retriever, uniprot, name: str) -> str:
    """A protein's function: literature passages with page citations, else UniProt + class."""
    hits = retriever.protein_function(name, k=3) if retriever else []
    if hits:
        return "Literature:\n" + "\n\n".join(f"[p.{h.page}] {h.text[:300]}" for h in hits)
    hit = uniprot.lookup(name) if uniprot else None
    if hit:
        return (
            f"UniProt {hit.accession} [{hit.category()}; refs {hit.refs()}] — "
            f"{hit.name}: {hit.function[:280]}"
        )
    return f"no function for {name} (not in literature or UniProt)"


def findings_from_report(report) -> str:
    """Render the deterministic Decision Report as the agent's grounded findings text."""
    lines = [
        f"Alignment: {report.method}, {report.n_anchor_proteins} anchor proteins, "
        f"quality {report.alignment_quality}."
    ]
    for s in report.structures:
        lines.append(
            f"\n{s.structure} ({s.use_case}): recommend {s.recommendation} "
            f"(aligned cosine {s.best_score}; runner-up {s.runner_up} {s.runner_up_score}, "
            f"margin {s.margin})."
        )
        lines.append("Ranking: " + ", ".join(f"{prep} {score}" for prep, score in s.ranking))
        lines.append("Drivers:")
        for d in s.drivers:
            lines.append(f"- {d.gene} [{d.uniprot_class}; {d.source}] {d.function}")
        if s.caveats:
            lines.append("Caveats: " + " ".join(s.caveats))
    return "\n".join(lines)
