from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import EvidencePackOut, SearchHybridIn, SearchResultOut
from app.services.retrieval.hybrid import build_evidence_pack, reciprocal_rank_fusion

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/hybrid", response_model=list[SearchResultOut])
def search_hybrid(payload: SearchHybridIn, user: dict[str, object] = Depends(get_current_user)) -> list[SearchResultOut]:
    require_workspace_member(payload.workspace_id, str(user["id"]))

    query = payload.query.lower()
    dense: list[tuple[str, float, str]] = []
    sparse: list[tuple[str, float, str]] = []
    graph: list[tuple[str, float, str]] = []

    for task in STORE.tasks.values():
        if task["workspace_id"] != payload.workspace_id:
            continue
        title = str(task["title"])
        score = 0.9 if query in title.lower() else 0.4
        dense.append((f"task:{task['id']}", score, title))

    for artifact in STORE.artifacts.values():
        if artifact["workspace_id"] != payload.workspace_id:
            continue
        title = str(artifact["title"])
        score = 0.95 if query in title.lower() else 0.35
        sparse.append((f"artifact:{artifact['id']}", score, title))

    for file_item in STORE.workspace_files.get(payload.workspace_id, []):
        name = str(file_item.get("name", "uploaded-file"))
        text = str(file_item.get("extracted_text", ""))
        haystack = f"{name}\n{text}".lower()
        score = 0.9 if query in haystack else 0.28
        sparse.append((f"file:{file_item['id']}", score, name))

    for decision in STORE.decisions.values():
        if decision["workspace_id"] != payload.workspace_id:
            continue
        question = str(decision["question"])
        score = 0.92 if query in question.lower() else 0.3
        graph.append((f"decision:{decision['id']}", score, question))

    ranked = reciprocal_rank_fusion([dense, sparse, graph])
    return ranked[: payload.top_k]


@router.post("/evidence-pack", response_model=EvidencePackOut)
def evidence_pack(payload: SearchHybridIn, user: dict[str, object] = Depends(get_current_user)) -> EvidencePackOut:
    ranked = search_hybrid(payload, user)
    return build_evidence_pack(payload.query, ranked, top_k=payload.top_k)
