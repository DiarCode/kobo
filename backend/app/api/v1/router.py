from fastapi import APIRouter

from app.api.v1 import (
    actions,
    agents,
    approvals,
    artifacts,
    assistant,
    auth,
    council,
    evidence,
    health,
    integrations,
    metrics,
    projects,
    search,
    tasks,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(assistant.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(artifacts.router)
api_router.include_router(evidence.router)
api_router.include_router(agents.router)
api_router.include_router(council.router)
api_router.include_router(approvals.router)
api_router.include_router(actions.router)
api_router.include_router(search.router)
api_router.include_router(integrations.router)
api_router.include_router(metrics.router)
