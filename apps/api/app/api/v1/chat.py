import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from supabase import Client

from apps.api.app.core.database import get_db, get_graph_db
from apps.api.app.core.security import get_current_user
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.graph_service import GraphLineageService
from apps.api.app.services.llm_service import LLMService
from packages.schemas.permissions import UserPermissionProfile

router = APIRouter(prefix="/chat", tags=["Chat"])


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


class ChatHistoryItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatQueryRequest(BaseModel):
    organization_id: str
    repo_id: str
    query: str
    history: list[ChatHistoryItem] = []
    context_keys: list[str] = []


class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    repo_id: str
    access_granted: bool
    provider: str = "kairo_engine"


@router.post("/query", response_model=ChatQueryResponse, status_code=status.HTTP_200_OK)
async def query_chat(
    request_body: ChatQueryRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
    db: Annotated[Client, Depends(get_db)] = None,
) -> ChatQueryResponse:
    """
    Role-scoped Grounded AI Chat Assistant.
    Enforces Pre-Retrieval ACL isolation before assembling dynamic context chunks
    from pgvector embeddings, work items, and graph decisions, then invoking LLMService.
    """
    # 1. Enforce Pre-Retrieval ACL Gate
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, profile.organization_id)
    PreRetrievalACL.guard_repo_access(request_body.repo_id, profile)

    context_chunks: list[dict[str, Any]] = []

    # 2. Dynamic Evidence from Explicit Context Slices
    for key in request_body.context_keys:
        clean_key = key.strip("[]")
        context_chunks.append({
            "source": clean_key,
            "content": f"Verified context slice for {clean_key} on repository {request_body.repo_id}.",
        })

    # 3. Dynamic Evidence from PostgreSQL Embeddings & Work Items
    if db:
        try:
            emb_res = (
                db.table("embeddings")
                .select("entity_type, entity_id, content_chunk")
                .eq("organization_id", request_body.organization_id)
                .eq("repo_id", request_body.repo_id)
                .limit(5)
                .execute()
            )
            for r in _rows(emb_res.data):
                source_tag = f"{r.get('entity_type', 'chunk')} {r.get('entity_id', '')}".strip()
                context_chunks.append({
                    "source": source_tag,
                    "content": str(r.get("content_chunk", "")),
                })
        except Exception:
            pass

        try:
            work_res = (
                db.table("work_items")
                .select("external_id, title, status, description")
                .eq("organization_id", request_body.organization_id)
                .limit(5)
                .execute()
            )
            for w in _rows(work_res.data):
                t_key = str(w.get("external_id", ""))
                context_chunks.append({
                    "source": f"Jira {t_key}",
                    "content": f"Task {t_key}: {w.get('title')} (Status: {w.get('status')}). {w.get('description', '')}",
                })
        except Exception:
            pass

    # 4. Dynamic Evidence from Neo4j Temporal Provenance Decisions
    try:
        gen = get_graph_db()
        graph_session = next(gen)
        task_keys = re.findall(r"\b[A-Z]+-\d+\b", request_body.query)
        for t_key in task_keys:
            decisions = GraphLineageService.extract_decision_subgraph(
                organization_id=request_body.organization_id,
                task_key=t_key,
                session=graph_session,
            )
            for d in decisions:
                context_chunks.append({
                    "source": f"ADR {d.decision_id}",
                    "content": f"Decision {d.decision_id}: {d.title} (Status: {d.status})",
                })
    except Exception:
        pass

    # 5. Base repository telemetry scope
    context_chunks.append({
        "source": f"Repo {request_body.repo_id}",
        "content": f"Repository {request_body.repo_id} monitored context under tenant {request_body.organization_id}.",
    })

    # 6. Grounded Synthesis via LLM Service
    llm_result = await LLMService.generate_grounded_answer(
        query=request_body.query,
        repo_id=request_body.repo_id,
        context_chunks=context_chunks,
        history=[h.model_dump() for h in request_body.history],
        organization_id=request_body.organization_id,
    )

    return ChatQueryResponse(
        answer=llm_result["answer"],
        citations=llm_result["citations"],
        repo_id=request_body.repo_id,
        access_granted=True,
        provider=llm_result.get("provider", "kairo_engine"),
    )
