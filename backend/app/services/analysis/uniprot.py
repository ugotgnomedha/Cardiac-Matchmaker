"""Fetch-once, disk-cached UniProt function lookup and ECM/contaminant classification."""

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

API = "https://rest.uniprot.org/uniprotkb/search"
CACHE_FILE = Path(os.getenv("MATCHMAKER_UNIPROT_CACHE", "/data/.uniprot_cache.json"))
_CACHE_VERSION = 2
_TIMEOUT = 10
_HEADERS = {"User-Agent": "CardiacMatchmaker/1.0 (academic; fetch-once cache)"}


@dataclass
class UniProtHit:
    """A UniProt entry: accession, name, function text, keywords, and PMIDs."""

    accession: str
    name: str
    function: str
    keywords: list
    pubmed: list = field(default_factory=list)

    def refs(self, n: int = 3) -> str:
        """Literature citation (PMIDs) for the function, or a no-primary-ref note."""
        if self.pubmed:
            return ", ".join(f"PMID:{p}" for p in self.pubmed[:n]) + (
                "…" if len(self.pubmed) > n else ""
            )
        return "curated entry, no primary ref"

    def cite(self, width: int = 200) -> str:
        """One-line citation: accession, refs, and a trimmed function description."""
        fn = self.function or self.name or "(no function annotation)"
        if len(fn) > width:
            fn = fn[:width].rsplit(" ", 1)[0] + "…"
        return f"UniProt {self.accession} [{self.refs()}]: {fn}"

    _ECM = {
        "Extracellular matrix",
        "Proteoglycan",
        "Collagen",
        "Cell adhesion",
        "Basement membrane",
    }
    _BLOOD = {
        "Blood coagulation",
        "Hemostasis",
        "Oxygen transport",
        "Acute phase",
        "Immunoglobulin",
        "Adaptive immunity",
        "Innate immunity",
        "Complement pathway",
    }
    _CELL = {"Cytoskeleton", "Cytoplasm", "Nucleus", "Mitochondrion"}

    def category(self) -> str:
        """Structural-vs-contaminant class from keywords (ECM checked first)."""
        kw = set(self.keywords)
        if kw & self._ECM:
            return "ECM/structural"
        if kw & self._BLOOD:
            return "blood/plasma (likely contaminant)"
        if kw & self._CELL:
            return "intracellular (likely contaminant)"
        return "other"


class UniProt:
    """Cached UniProt client: each gene is fetched at most once, then served offline."""

    def __init__(self, cache_file: Path = CACHE_FILE):
        """Load any existing on-disk cache for this client."""
        self.cache_file = Path(cache_file)
        self._cache = {}
        if self.cache_file.exists():
            try:
                blob = json.loads(self.cache_file.read_text())
                if isinstance(blob, dict) and blob.get("_version") == _CACHE_VERSION:
                    self._cache = blob.get("entries", {})
            except Exception:
                pass

    def _save(self) -> None:
        """Persist the versioned cache to disk, best effort."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps({"_version": _CACHE_VERSION, "entries": self._cache}, ensure_ascii=False)
            )
        except OSError:
            pass

    def _fetch(self, gene: str, organism_id: int) -> Optional[dict]:
        """Query UniProt for the reviewed human entry of a gene and parse its FUNCTION."""
        query = f"gene_exact:{gene} AND organism_id:{organism_id} AND reviewed:true"
        params = urllib.parse.urlencode(
            {
                "query": query,
                "fields": "accession,protein_name,cc_function,keyword",
                "format": "json",
                "size": 1,
            }
        )
        req = urllib.request.Request(f"{API}?{params}", headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            data = json.loads(r.read().decode())
        results = data.get("results") or []
        if not results:
            return None
        e = results[0]
        func, pubmed = "", []
        for c in e.get("comments", []):
            if c.get("commentType") == "FUNCTION" and c.get("texts"):
                t = c["texts"][0]
                func = t.get("value", "")
                pubmed = [
                    ev["id"]
                    for ev in t.get("evidences", [])
                    if ev.get("source") == "PubMed" and ev.get("id")
                ]
                pubmed += re.findall(r"PubMed:(\d+)", func)
                pubmed = list(dict.fromkeys(pubmed))
                break
        return {
            "accession": e.get("primaryAccession", ""),
            "name": (
                e.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value", "")
            ),
            "function": func,
            "keywords": [k.get("name", "") for k in e.get("keywords", [])],
            "pubmed": pubmed,
        }

    def lookup(self, gene: str, organism_id: int = 9606) -> Optional[UniProtHit]:
        """Cached UniProt entry for a gene symbol; fetches once, then served offline."""
        if gene not in self._cache:
            try:
                self._cache[gene] = self._fetch(gene, organism_id)
            except Exception:
                return None
            self._save()
        rec = self._cache[gene]
        return UniProtHit(**rec) if rec else None

    def prefetch(self, genes) -> dict:
        """Warm the cache for many genes (one network call per new gene)."""
        hit = miss = 0
        for g in dict.fromkeys(genes):
            if self.lookup(g):
                hit += 1
            else:
                miss += 1
        return {
            "requested": hit + miss,
            "found": hit,
            "not_in_uniprot": miss,
            "cache_size": len(self._cache),
        }
