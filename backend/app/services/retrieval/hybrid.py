from __future__ import annotations

from app.domain.schemas import EvidencePackOut, SearchResultOut


def reciprocal_rank_fusion(ranks: list[list[tuple[str, float, str]]], k: int = 60) -> list[SearchResultOut]:
    scores: dict[str, float] = {}
    excerpts: dict[str, str] = {}
    source_types: dict[str, str] = {}
    for strategy in ranks:
        for idx, (source_ref, score, excerpt) in enumerate(strategy, start=1):
            scores[source_ref] = scores.get(source_ref, 0.0) + (1.0 / (k + idx)) + score * 0.01
            excerpts[source_ref] = excerpt
            source_types[source_ref] = source_ref.split(":", 1)[0]
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        SearchResultOut(
            source_type=source_types[source_ref],
            source_ref=source_ref,
            score=round(score, 4),
            excerpt=excerpts[source_ref],
        )
        for source_ref, score in ordered
    ]


def build_evidence_pack(query: str, candidates: list[SearchResultOut], top_k: int = 8) -> EvidencePackOut:
    clipped = candidates[:top_k]
    budget = 2000 + (len(clipped) * 200)
    return EvidencePackOut(query=query, results=clipped, context_budget_tokens=budget)
